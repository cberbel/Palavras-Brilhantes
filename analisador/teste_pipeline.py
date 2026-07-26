#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de integração: vídeo de verdade → ffmpeg → bipes → TR.

Os outros dois testes cobrem as peças isoladas. Este monta um .webm com bipes em
posições conhecidas, roda o sincronizar.py e o analisar.py em sequência e
verifica se o tempo de reação plantado volta no fim. É o único teste que prova
que as peças encaixam — inclusive a extração de áudio pelo ffmpeg e o formato
do eventos.csv que o apresentador realmente escreve.
"""
from __future__ import annotations
import csv, json, os, subprocess, sys, tempfile, wave
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from sincronizar import acha_ffmpeg, BEEP_HZ, BEEP_MS

SR = 16000
FPS = 30.0
N_TRIALS = 6
BIPE_0 = 2000.0
PASSO = 8000.0
GAP = 3000.0            # fixação 1000 + pré-exposição 2000
ONSET_CLIPE = 900.0
TR_PLANTADO = 600.0
TOL_MS = 60.0


def faz_wav(caminho: str, dur_ms: float, bipes_ms: list[float]) -> None:
    n = int(SR * dur_ms / 1000)
    rng = np.random.default_rng(3)
    x = 0.04 * rng.standard_normal(n)                     # ruído de sala
    t = np.arange(n) / SR
    for f0, amp in [(200, .16), (500, .11), (900, .07)]:  # "fala" de fundo
        env = np.clip(np.sin(2 * np.pi * 0.9 * t) + 0.3, 0, None)
        x += amp * env * np.sin(2 * np.pi * f0 * t)
    m = int(SR * BEEP_MS / 1000)
    env = np.ones(m); r = int(0.004 * SR)
    env[:r] = np.linspace(0, 1, r); env[-r:] = np.linspace(1, 0, r)
    tom = 0.22 * env * np.sin(2 * np.pi * BEEP_HZ * np.arange(m) / SR)
    for b in bipes_ms:
        i = int(b * SR / 1000)
        x[i:i + m] += tom
    pcm = np.clip(x, -1, 1) * 32767
    with wave.open(caminho, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.astype(np.int16).tobytes())


def faz_webm(wav: str, webm: str, dur_ms: float) -> None:
    cmd = [acha_ffmpeg(), "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c=gray:s=160x120:r=10:d={dur_ms/1000:.2f}",
           "-i", wav, "-c:v", "libvpx", "-b:v", "80k", "-c:a", "libopus",
           "-shortest", webm]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg falhou ao montar o webm:\n" + r.stderr[:800])


def faz_eventos(caminho: str, bipes: list[float]) -> None:
    cols = ["pid", "idade_meses", "ordem", "modo_audio", "trial", "alvo", "ladoAlvo",
            "fase", "gap_bipe_frase_ms", "onset_no_clipe_ms", "alvo_apos_bipe_ms",
            "rt_valido", "t_video_aprox_ms", "obs"]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, b in enumerate(bipes, 1):
            w.writerow({"pid": "PIPE", "ordem": "A", "modo_audio": "arquivo",
                        "trial": i, "alvo": f"item{i}",
                        "ladoAlvo": "left" if i % 2 else "right", "fase": "bipe",
                        "gap_bipe_frase_ms": GAP, "onset_no_clipe_ms": ONSET_CLIPE,
                        "alvo_apos_bipe_ms": GAP + ONSET_CLIPE, "rt_valido": "sim",
                        "t_video_aprox_ms": round(b), "obs": ""})


def faz_olhar(caminho: str, bipes: list[float], dur_ms: float) -> None:
    """Olhar preso no distrator, mudando para o alvo TR_PLANTADO ms após o onset."""
    dt = 1000.0 / FPS
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["t_ms", "olhar"])
        for k in range(int(dur_ms / dt)):
            t = k * dt
            g = "away"
            for i, b in enumerate(bipes, 1):
                onset = b + GAP + ONSET_CLIPE
                if onset - 2500 <= t <= onset + 2500:
                    lado = "left" if i % 2 else "right"
                    dist = "right" if lado == "left" else "left"
                    g = lado if t >= onset + TR_PLANTADO else dist
                    break
            w.writerow([round(t, 1), g])


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="lwl_pipe_")
    bipes = [BIPE_0 + i * PASSO for i in range(N_TRIALS)]
    dur = bipes[-1] + GAP + ONSET_CLIPE + 3000

    wav = os.path.join(tmp, "a.wav"); webm = os.path.join(tmp, "sessao.webm")
    ev = os.path.join(tmp, "eventos.csv"); olhar = os.path.join(tmp, "olhar.csv")
    sinc = os.path.join(tmp, "sincronizacao.json"); res = os.path.join(tmp, "res")

    print("montando mídia de teste...")
    faz_wav(wav, dur, bipes)
    faz_webm(wav, webm, dur)
    faz_eventos(ev, bipes)
    faz_olhar(olhar, bipes, dur)
    print(f"  {os.path.getsize(webm)/1024:.0f} KB de webm, {N_TRIALS} trials\n")

    for etapa, cmd in [
        ("sincronizar", [sys.executable, os.path.join(AQUI, "sincronizar.py"),
                         webm, ev, "--saida", sinc]),
        ("analisar", [sys.executable, os.path.join(AQUI, "analisar.py"),
                      sinc, olhar, "--saida", res]),
    ]:
        print(f"--- {etapa} ---")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip())
        if r.returncode != 0:
            print(r.stderr); return 1
        print()

    with open(sinc, encoding="utf-8") as f:
        s = json.load(f)
    erros_bipe = [abs(m["t_bipe_ms"] - b) for m, b in zip(s["trials"], bipes)]

    with open(os.path.join(res, "por_trial.csv"), encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    falhas = []
    if s["n_bipes"] != N_TRIALS:
        falhas.append(f"bipes: {s['n_bipes']} != {N_TRIALS}")
    if erros_bipe and max(erros_bipe) > TOL_MS:
        falhas.append(f"pior erro de bipe {max(erros_bipe):.0f} ms")

    print("--- conferência ---")
    print(f"erro de localização dos bipes: máx {max(erros_bipe):.0f} ms")
    for l in linhas:
        tr = int(l["tr_ms"]) if l["tr_ms"] else None
        ok = tr is not None and abs(tr - TR_PLANTADO) <= TOL_MS
        print(f"  [{'ok ' if ok else 'FALHA'}] trial {l['trial']}: TR={tr} ms "
              f"(plantado {TR_PLANTADO:.0f}), acurácia={l['acuracia']}, "
              f"excluido='{l['excluido']}'")
        if not ok:
            falhas.append(f"trial {l['trial']} TR={tr}")

    print()
    if falhas:
        print("FALHOU: " + "; ".join(falhas)); return 1
    print(f"Pipeline completo: TR plantado recuperado nos {len(linhas)} trials, "
          f"dentro de {TOL_MS:.0f} ms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
