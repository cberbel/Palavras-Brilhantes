#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste da detecção de bipes com áudio sintético em posições conhecidas.

Simula o pior caso realista: bipe baixo, fala e ruído de sala por cima.
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sincronizar import energia_no_tom, acha_bipes, BEEP_HZ, BEEP_MS

SR = 16000
DUR = 60.0
POSICOES = [2.0, 9.5, 17.0, 24.5, 32.0, 39.5, 47.0, 54.5]   # segundos
BEEP_S = BEEP_MS / 1000.0
TOL_MS = 15.0   # menos de meio quadro a 30 fps


def sinal():
    n = int(SR * DUR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(7)

    # ruído de sala
    x = 0.05 * rng.standard_normal(n)

    # "fala": tons variados na banda da voz, com envelope irregular — inclusive
    # passando perto de 1000 Hz, para o teste não ser fácil demais
    for f0, amp in [(180, .18), (420, .12), (760, .10), (950, .08), (1300, .07)]:
        env = np.clip(np.sin(2 * np.pi * (0.7 + f0 / 1000) * t) + 0.4, 0, None)
        x += amp * env * np.sin(2 * np.pi * f0 * t + rng.random())

    # bipes, em volume modesto (como chegariam pelo microfone da câmera)
    for p in POSICOES:
        i0 = int(p * SR)
        m = int(BEEP_S * SR)
        env = np.ones(m)
        r = int(0.004 * SR)
        env[:r] = np.linspace(0, 1, r)
        env[-r:] = np.linspace(1, 0, r)
        x[i0:i0 + m] += 0.20 * env * np.sin(2 * np.pi * BEEP_HZ * np.arange(m) / SR)

    return x


def confere(rotulo, achados, margem, esperados, falhas):
    print(f"--- {rotulo}")
    print(f"Esperados : {len(esperados)}")
    n_ok = sum(1 for a in achados if a is not None)
    print(f"Detectados: {n_ok}  (margem {margem:.2f}x)")
    if len(achados) != len(esperados):
        falhas.append(f"{rotulo}: contagem {len(achados)} != {len(esperados)}")
    for esp, got in zip(esperados, achados):
        if esp is None:
            marca = "ok " if got is None else "FALHA"
            print(f"[{marca}] trial sem bipe → achado {got}")
            if got is not None:
                falhas.append(f"{rotulo}: inventou bipe em {got:.3f}s")
            continue
        if got is None:
            print(f"[FALHA] esperado {esp:6.3f}s  achado nenhum")
            falhas.append(f"{rotulo}: {esp}s não achado")
            continue
        erro = abs(got - esp) * 1000
        marca = "ok " if erro <= TOL_MS else "FALHA"
        print(f"[{marca}] esperado {esp:6.3f}s  achado {got:6.3f}s  erro {erro:5.1f} ms")
        if erro > TOL_MS:
            falhas.append(f"{rotulo}: {esp}s erro {erro:.0f} ms")


def main():
    x = sinal()
    tempos, razao = energia_no_tom(x, SR, BEEP_HZ)
    falhas = []

    # 1) sem log: pega os N picos mais fortes
    achados, margem, _ = acha_bipes(tempos, razao, len(POSICOES))
    confere("sem log (top-N)", achados, margem, POSICOES, falhas)

    # 2) guiado pelo log: tempos aproximados com deslocamento constante de
    #    +1,3 s (o vídeo começou antes do apresentador) e erro de ±60 ms
    rng = np.random.default_rng(3)
    aprox = [(p + 1.3 + rng.uniform(-0.06, 0.06)) * 1000 for p in POSICOES]
    achados, margem, _ = acha_bipes(tempos, razao, len(POSICOES), esperados_ms=aprox)
    confere("guiado pelo log", achados, margem, POSICOES, falhas)

    # 3) guiado, mas o log tem um trial a mais cujo bipe não está no áudio
    #    (a gravação parou antes): tem de devolver None nesse trial e acertar
    #    os outros, sem deslocar o pareamento
    aprox2 = aprox[:5] + [(43.25 + 1.3) * 1000] + aprox[5:]
    esp2 = POSICOES[:5] + [None] + POSICOES[5:]
    achados, margem, _ = acha_bipes(tempos, razao, len(esp2), esperados_ms=aprox2)
    confere("guiado, 1 bipe faltando", achados, margem, esp2, falhas)

    print()
    if falhas:
        print("FALHOU: " + "; ".join(falhas))
        return 1
    print(f"Todos os bipes localizados dentro de {TOL_MS:.0f} ms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
