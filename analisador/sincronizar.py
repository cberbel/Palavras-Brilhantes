#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sincronização: encontra os bipes de 1000 Hz na trilha de áudio do vídeo.

Cada trial do apresentador começa com um bipe curto agendado no mesmo relógio
do AudioContext em que a frase é tocada. Achando o bipe no vídeo, o instante da
palavra-alvo dentro do vídeo é, exatamente:

    t_alvo_no_video = t_bipe_no_video + gap_bipe_frase_ms + onset_no_clipe_ms

que é o campo `alvo_apos_bipe_ms` do eventos.csv. Isso dispensa qualquer
suposição sobre quando o MediaRecorder começou, e funciona igual se quem gravou
foi a webcam ou um celular ao lado.

Uso:
    python sincronizar.py VIDEO.webm EVENTOS.csv [--saida sincronizacao.json]

Requer ffmpeg no PATH e numpy.
"""
from __future__ import annotations
import argparse, csv, json, os, shutil, subprocess, sys, tempfile, wave
import numpy as np

BEEP_HZ = 1000.0
BEEP_MS = 80        # precisa bater com o BEEP_MS do apresentador
JANELA_MS = 40      # resolução de ~25 Hz — separa o bipe de formantes vizinhos
HOP_MS = 5          # passo entre janelas
SEP_MIN_MS = 1500   # separação mínima entre dois bipes (trials duram ~7 s)


def acha_ffmpeg() -> str:
    """ffmpeg do sistema, ou o binário embutido no pacote imageio-ffmpeg.

    O fallback existe porque instalar ffmpeg no Windows costuma virar uma tarefa
    à parte (baixar, descompactar, mexer no PATH), enquanto `pip install
    imageio-ffmpeg` traz o binário pronto e resolve o problema numa linha.
    """
    do_sistema = shutil.which("ffmpeg")
    if do_sistema:
        return do_sistema
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit(
            "ffmpeg não encontrado. Instale de uma destas formas:\n"
            "  pip install imageio-ffmpeg      (mais simples, binário embutido)\n"
            "  winget install Gyan.FFmpeg      (instala no sistema)"
        )


def extrai_audio(video: str) -> tuple[np.ndarray, int]:
    """Extrai a trilha de áudio como mono 16 kHz PCM 16-bit via ffmpeg."""
    tmp = os.path.join(tempfile.gettempdir(), "lwl_sync_audio.wav")
    cmd = [acha_ffmpeg(), "-y", "-loglevel", "error", "-i", video,
           "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        raise SystemExit(
            "Falha ao extrair áudio do vídeo.\n"
            f"ffmpeg disse: {r.stderr.strip()[:500]}\n\n"
            "Causa mais comum: o vídeo foi gravado SEM trilha de áudio. "
            "Sem áudio não há bipe, e a sincronização tem de ser manual."
        )
    with wave.open(tmp, "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    if x.size == 0:
        raise SystemExit("A trilha de áudio do vídeo está vazia.")
    return x / 32768.0, sr


def energia_no_tom(x: np.ndarray, sr: int, freq: float) -> tuple[np.ndarray, np.ndarray]:
    """Fração da energia da janela concentrada em `freq`.

    Normalizar pela energia total é o que torna a detecção robusta a volume: o
    bipe é um tom puro, então a fração sobe perto de 1, enquanto fala e ruído de
    sala ficam baixos por espalharem energia por todo o espectro.

    Vetorizado: um bin de DFT calculado de uma vez sobre todas as janelas. Um
    laço Goertzel em Python levaria dezenas de segundos num vídeo de 5 minutos.
    """
    n = int(sr * JANELA_MS / 1000)
    hop = int(sr * HOP_MS / 1000)
    if len(x) < n:
        return np.array([]), np.array([])

    janelas = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    w = np.hanning(n)
    seg = janelas * w

    # projeção no bin de `freq` (frequência exata, não arredondada para um bin)
    fase = np.exp(-2j * np.pi * freq * np.arange(n) / sr)
    proj = seg @ fase
    energia_tom = 2.0 * np.abs(proj) ** 2 / n          # 2x: bins positivo e negativo
    energia_total = np.einsum("ij,ij->i", seg, seg) + 1e-12

    tempos = np.arange(len(seg)) * hop / sr + (n / 2) / sr   # centro da janela
    return tempos, np.clip(energia_tom / energia_total, 0, None)


def refina_onset(razao: np.ndarray, pico: int) -> int:
    """Recua do pico até o INÍCIO do tom.

    `tempos` marca o centro de cada janela, então o pico da razão cai no meio do
    bipe, não onde ele começa — um viés de algumas dezenas de ms que entraria
    inteiro no tempo de reação. A janela fica meio preenchida pelo tom quando seu
    centro coincide com o início dele, ou seja, na meia-altura da subida.
    """
    meia_altura = razao[pico] * 0.5
    limite = max(0, pico - int((BEEP_MS + JANELA_MS) / HOP_MS))
    i = pico
    while i > limite and razao[i - 1] >= meia_altura:
        i -= 1
    return i


def acha_bipes(tempos: np.ndarray, razao: np.ndarray,
               n_esperado: int) -> tuple[list[float], float]:
    """Localiza os bipes. Retorna (tempos_s, margem_de_confianca).

    Duas decisões que tornam isto robusto:

    1. Contraste local em vez de limiar absoluto. A pontuação de cada instante é
       a razão tom/total dividida pela mediana da vizinhança de ±1 s. Um bipe se
       destaca do que veio logo antes e logo depois, mesmo que a sala esteja
       barulhenta ou o volume tenha mudado no meio da sessão.

    2. Usa `n_esperado`. Sabemos quantos bipes existem — um por trial. Então em
       vez de adivinhar um limiar, pegamos os `n_esperado` picos mais fortes com
       separação mínima. A "margem" devolvida é a razão entre o pico mais fraco
       aceito e o mais forte rejeitado: perto de 1 significa que a escolha foi
       apertada e merece conferência manual.
    """
    if razao.size == 0 or n_esperado <= 0:
        return [], 0.0

    # mediana móvel como piso local
    meia = max(1, int(1000 / HOP_MS))
    pad = np.pad(razao, meia, mode="edge")
    jan = np.lib.stride_tricks.sliding_window_view(pad, 2 * meia + 1)
    piso = np.median(jan, axis=1) + 1e-6
    score = razao / piso

    sep = max(1, int(SEP_MIN_MS / HOP_MS))
    ordem = np.argsort(score)[::-1]
    picos: list[int] = []
    rejeitado_forte = 0.0
    for i in ordem:
        if any(abs(int(i) - p) < sep for p in picos):
            continue
        if len(picos) < n_esperado:
            picos.append(int(i))
        else:
            rejeitado_forte = float(score[i])
            break

    picos = [refina_onset(razao, p) for p in sorted(picos)]
    if picos:
        mais_fraco = float(min(score[p] for p in picos))
        margem = mais_fraco / rejeitado_forte if rejeitado_forte > 0 else float("inf")
    else:
        margem = 0.0
    return [float(tempos[i]) for i in picos], margem


def le_trials(eventos_csv: str) -> list[dict]:
    """Uma entrada por trial, a partir das linhas fase='bipe'."""
    out = []
    with open(eventos_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("fase") != "bipe":
                continue
            out.append({
                "trial": int(r["trial"]),
                "alvo": r.get("alvo", ""),
                "ladoAlvo": r.get("ladoAlvo", ""),
                "alvo_apos_bipe_ms": (float(r["alvo_apos_bipe_ms"])
                                      if r.get("alvo_apos_bipe_ms") else None),
                "rt_valido": r.get("rt_valido", "sim"),
            })
    out.sort(key=lambda d: d["trial"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("eventos")
    ap.add_argument("--saida", default="sincronizacao.json")
    a = ap.parse_args()

    trials = le_trials(a.eventos)
    if not trials:
        raise SystemExit("Nenhuma linha fase='bipe' no eventos.csv. "
                         "Este arquivo veio de uma versão antiga do apresentador?")

    x, sr = extrai_audio(a.video)
    tempos, razao = energia_no_tom(x, sr, BEEP_HZ)
    bipes, margem = acha_bipes(tempos, razao, len(trials))

    print(f"Trials esperados : {len(trials)}")
    print(f"Bipes localizados: {len(bipes)}")
    print(f"Margem           : {margem:.2f}x  (quanto maior, mais claro o bipe)")

    alerta = None
    if len(bipes) != len(trials):
        alerta = (f"Foram localizados {len(bipes)} bipes para {len(trials)} trials. "
                  "Os trials foram pareados na ordem, até acabar o que houver.")
        print("⚠ " + alerta)
    elif margem < 1.5:
        alerta = (f"Margem de detecção baixa ({margem:.2f}x): o bipe mais fraco aceito "
                  "está perto do ruído mais forte rejeitado. Confira os intervalos "
                  "entre bipes abaixo antes de confiar na sincronização.")
        print("⚠ " + alerta)

    mapa = []
    for i, t in enumerate(trials):
        if i >= len(bipes):
            break
        t_bipe_ms = bipes[i] * 1000.0
        alvo_ms = (t_bipe_ms + t["alvo_apos_bipe_ms"]) if t["alvo_apos_bipe_ms"] is not None else None
        mapa.append({
            "trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
            "t_bipe_ms": round(t_bipe_ms, 1),
            "t_alvo_onset_ms": None if alvo_ms is None else round(alvo_ms, 1),
            "rt_valido": t["rt_valido"],
        })

    # deriva: os intervalos entre bipes devem bater com os do log
    deriva = None
    if len(mapa) >= 2:
        obs = np.diff([m["t_bipe_ms"] for m in mapa])
        print(f"Intervalo entre bipes: mediana {np.median(obs):.0f} ms, "
              f"desvio {obs.std():.0f} ms")
        deriva = {"intervalo_mediano_ms": float(np.median(obs)),
                  "desvio_ms": float(obs.std())}

    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump({"video": os.path.basename(a.video), "n_trials": len(trials),
                   "n_bipes": len(bipes), "margem": margem, "alerta": alerta,
                   "deriva": deriva, "trials": mapa}, f, ensure_ascii=False, indent=1)
    print(f"\nEscrito: {a.saida}")


if __name__ == "__main__":
    main()
