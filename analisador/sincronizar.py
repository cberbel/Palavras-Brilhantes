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
TOL_PAREAMENTO_MS = 250  # quanto o bipe pode desviar do intervalo previsto pelo log


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
    fd, tmp = tempfile.mkstemp(prefix="lwl_sync_", suffix=".wav")
    os.close(fd)
    # aresample=async=1:first_pts=0 preserva a linha do tempo da trilha: se o
    # Opus do MediaRecorder começar com PTS ≠ 0 ou tiver lacunas (aba perdeu
    # foco), o ffmpeg preenche com silêncio em vez de concatenar — senão o bipe
    # cai num instante que não corresponde ao video.currentTime do codificador.
    cmd = [acha_ffmpeg(), "-y", "-loglevel", "error", "-i", video,
           "-vn", "-af", "aresample=async=1:first_pts=0",
           "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp]
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
    try:
        os.remove(tmp)
    except OSError:
        pass
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


def acha_bipes(tempos: np.ndarray, razao: np.ndarray, n_esperado: int,
               esperados_ms: list[float] | None = None) -> tuple[list[float], float, list[int]]:
    """Localiza os bipes. Retorna (tempos_s, margem, indices_dos_trials).

    Duas decisões que tornam isto robusto:

    1. Contraste local em vez de limiar absoluto. A pontuação de cada instante é
       a razão tom/total dividida pela mediana da vizinhança de ±1 s. Um bipe se
       destaca do que veio logo antes e logo depois, mesmo que a sala esteja
       barulhenta ou o volume tenha mudado no meio da sessão.

    2. Usa o que o log sabe. Sabemos quantos bipes existem (um por trial) e, pelo
       `t_video_aprox_ms` do eventos.csv, com que INTERVALOS eles vieram (erro
       < 100 ms). Então: pega-se um excesso de candidatos (3× n_esperado) e
       escolhe-se, entre eles, o conjunto cujos intervalos batem com os do log.
       Sem isso, um bipe mascarado por choro + um pico espúrio de fala em outro
       lugar mantinham a contagem certa e deslocavam todos os trials seguintes
       em silêncio. Um trial cujo bipe não foi achado fica sem bipe (None) — e o
       analisador recusa só ele, não a sessão inteira.

    A "margem" é a razão entre o pico mais fraco aceito e o mais forte rejeitado,
    medida NO PICO (não na borda refinada): perto de 1 significa escolha apertada.
    """
    if razao.size == 0 or n_esperado <= 0:
        return [], 0.0, []

    # mediana móvel como piso local
    meia = max(1, int(1000 / HOP_MS))
    pad = np.pad(razao, meia, mode="edge")
    jan = np.lib.stride_tricks.sliding_window_view(pad, 2 * meia + 1)
    piso = np.median(jan, axis=1) + 1e-6
    score = razao / piso

    sep = max(1, int(SEP_MIN_MS / HOP_MS))
    ordem = np.argsort(score)[::-1]
    cands: list[int] = []
    for i in ordem:
        if any(abs(int(i) - p) < sep for p in cands):
            continue
        cands.append(int(i))
        if len(cands) >= 3 * n_esperado:
            break
    cands.sort()
    t_cand = np.array([tempos[i] * 1000.0 for i in cands])      # ms, no pico

    if esperados_ms and len(esperados_ms) == n_esperado and n_esperado >= 2:
        # Pareamento guiado: para cada deslocamento possível (candidato j como
        # bipe do trial 0), conta quantos trials têm candidato a ±TOL do
        # instante previsto; fica com o deslocamento que casa mais trials e,
        # entre empates, o de maior pontuação somada.
        esp = np.array(esperados_ms, dtype=float)
        rel = esp - esp[0]
        melhor = None
        for j in range(len(cands)):
            t0 = t_cand[j]
            pares = []
            for k in range(n_esperado):
                alvo = t0 + rel[k]
                d = np.abs(t_cand - alvo)
                m = int(np.argmin(d))
                pares.append(m if d[m] <= TOL_PAREAMENTO_MS else None)
            n_ok = sum(p is not None for p in pares)
            soma = sum(score[cands[p]] for p in pares if p is not None)
            chave = (n_ok, soma)
            if melhor is None or chave > melhor[0]:
                melhor = (chave, pares)
        pares = melhor[1]
        usados = [cands[p] for p in pares if p is not None]
        idx_trials = pares
    else:
        # sem log utilizável: os n mais fortes, em ordem de tempo
        top = sorted(cands, key=lambda i: -score[i])[:n_esperado]
        usados = sorted(top)
        idx_trials = list(range(len(usados)))

    aceitos = set(usados)
    rejeitados = [score[i] for i in cands if i not in aceitos]
    if usados:
        mais_fraco = float(min(score[i] for i in usados))
        forte_rej = float(max(rejeitados)) if rejeitados else 0.0
        margem = mais_fraco / forte_rej if forte_rej > 0 else float("inf")
    else:
        margem = 0.0

    inicio = {i: refina_onset(razao, i) for i in usados}
    if esperados_ms and len(esperados_ms) == n_esperado and n_esperado >= 2:
        tempos_por_trial = [None if p is None else float(tempos[inicio[cands[p]]]) for p in idx_trials]
        return tempos_por_trial, margem, idx_trials
    return [float(tempos[inicio[i]]) for i in usados], margem, idx_trials


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
                "t_video_aprox_ms": (float(r["t_video_aprox_ms"])
                                     if r.get("t_video_aprox_ms") else None),
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
    esperados = [t["t_video_aprox_ms"] for t in trials]
    guiado = all(e is not None for e in esperados) and len(trials) >= 2
    bipes, margem, _ = acha_bipes(tempos, razao, len(trials), esperados if guiado else None)
    if not guiado:
        bipes = list(bipes) + [None] * (len(trials) - len(bipes))
    achados = sum(b is not None for b in bipes)

    print(f"Trials esperados : {len(trials)}")
    print(f"Bipes localizados: {achados}" + ("  (pareados pelos intervalos do log)" if guiado else ""))
    print(f"Margem           : {margem:.2f}x  (quanto maior, mais claro o bipe)")

    alerta = None
    faltando = [t["trial"] for t, b in zip(trials, bipes) if b is None]
    if faltando:
        alerta = (f"Sem bipe para {len(faltando)} de {len(trials)} trials "
                  f"({', '.join(map(str, faltando[:10]))}{'…' if len(faltando) > 10 else ''}). "
                  "Esses trials ficam sem onset e o analisador os descarta; os outros valem.")
        print("⚠ " + alerta)
    elif margem < 1.5:
        alerta = (f"Margem de detecção baixa ({margem:.2f}x): o bipe mais fraco aceito "
                  "está perto do ruído mais forte rejeitado. Confira os intervalos "
                  "entre bipes abaixo antes de confiar na sincronização.")
        print("⚠ " + alerta)

    mapa = []
    for t, b in zip(trials, bipes):
        t_bipe_ms = None if b is None else b * 1000.0
        alvo_ms = (t_bipe_ms + t["alvo_apos_bipe_ms"]) if (t_bipe_ms is not None and t["alvo_apos_bipe_ms"] is not None) else None
        mapa.append({
            "trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
            "t_bipe_ms": None if t_bipe_ms is None else round(t_bipe_ms, 1),
            "t_alvo_onset_ms": None if alvo_ms is None else round(alvo_ms, 1),
            "rt_valido": t["rt_valido"],
        })

    # deriva: os intervalos entre bipes devem bater com os do log
    deriva = None
    com_bipe = [(m, t) for m, t in zip(mapa, trials) if m["t_bipe_ms"] is not None]
    if len(com_bipe) >= 2:
        obs = np.diff([m["t_bipe_ms"] for m, _ in com_bipe])
        print(f"Intervalo entre bipes: mediana {np.median(obs):.0f} ms, "
              f"desvio {obs.std():.0f} ms")
        deriva = {"intervalo_mediano_ms": float(np.median(obs)),
                  "desvio_ms": float(obs.std())}
        if guiado:
            esp = np.diff([t["t_video_aprox_ms"] for _, t in com_bipe])
            dif = np.abs(obs - esp)
            print(f"Desvio em relação ao log: máx {dif.max():.0f} ms "
                  f"(o log tem erro de até ~100 ms; acima disso, desconfie)")
            deriva["desvio_max_vs_log_ms"] = float(dif.max())

    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump({"video": os.path.basename(a.video), "n_trials": len(trials),
                   "n_bipes": achados, "margem": margem, "alerta": alerta,
                   "deriva": deriva, "trials": mapa}, f, ensure_ascii=False, indent=1)
    print(f"\nEscrito: {a.saida}")


if __name__ == "__main__":
    main()
