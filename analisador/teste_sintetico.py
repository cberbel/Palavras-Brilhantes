#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste do analisar.py com dados sintéticos de comportamento conhecido.

Cada trial é construído para exercitar uma regra do protocolo. O teste falha se
o analisador não recuperar exatamente o que foi plantado.
"""
import csv, json, os, subprocess, sys, tempfile

FPS = 30.0
DT = 1000.0 / FPS          # 33,33 ms por quadro
PASSO_TRIAL = 10_000.0     # trials bem separados no tempo do vídeo

# (lado_alvo, estado_inicial, ms_do_shift ou None, sustentado?, tudo_fora?, esperado)
CASOS = [
    ("left",  "dist", 600.0, True,  False, {"tr": 600, "excl": ""}),
    ("right", "dist", 150.0, True,  False, {"tr": None, "excl": "shift_antecipatorio"}),
    ("left",  "alvo", None,  True,  False, {"tr": None, "excl": ""}),
    ("right", "dist", 700.0, True,  True,  {"tr": None, "excl": "olhar_fora"}),
    ("left",  "dist", 900.0, False, False, {"tr": None, "excl": "sem_shift_na_janela"}),
]


def constroi(tmp):
    trials, amostras = [], []
    for i, (lado, inicio, shift, sustenta, fora, _) in enumerate(CASOS):
        onset = (i + 1) * PASSO_TRIAL
        dist = "right" if lado == "left" else "left"
        trials.append({"trial": i + 1, "alvo": f"item{i+1}", "ladoAlvo": lado,
                       "t_bipe_ms": onset - 3000, "t_alvo_onset_ms": onset,
                       "rt_valido": "sim"})
        # de -2000 ms (baseline) a +2000 ms após o onset.
        # O tempo é calculado a partir do índice, não acumulado, senão o erro de
        # ponto flutuante desloca um quadro perto das fronteiras.
        n_no_alvo = 0
        for k in range(int(4000.0 / DT)):
            t = onset - 2000.0 + k * DT
            if fora:
                g = "away"
            elif t < onset:
                g = dist if inicio == "dist" else lado
            elif shift is not None and t >= onset + shift:
                if sustenta:
                    g = lado
                else:
                    # um único quadro no alvo, depois volta — não pode virar TR
                    g = lado if n_no_alvo < 1 else dist
                    if g == lado:
                        n_no_alvo += 1
            else:
                g = dist if inicio == "dist" else lado
            amostras.append((round(t, 1), g))

    sinc = os.path.join(tmp, "sincronizacao.json")
    with open(sinc, "w", encoding="utf-8") as f:
        json.dump({"video": "sintetico.webm", "n_trials": len(trials),
                   "n_bipes": len(trials), "alerta": None, "trials": trials},
                  f, ensure_ascii=False)

    olhar = os.path.join(tmp, "olhar.csv")
    with open(olhar, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_ms", "olhar"])
        w.writerows(amostras)
    return sinc, olhar


def main():
    aqui = os.path.dirname(os.path.abspath(__file__))
    tmp = tempfile.mkdtemp(prefix="lwl_teste_")
    sinc, olhar = constroi(tmp)
    saida = os.path.join(tmp, "resultados")

    r = subprocess.run([sys.executable, os.path.join(aqui, "analisar.py"),
                        sinc, olhar, "--saida", saida],
                       capture_output=True, text=True, encoding="utf-8")
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        return 1

    with open(os.path.join(saida, "por_trial.csv"), encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    falhas = []
    for (lado, inicio, shift, sustenta, fora, esp), got in zip(CASOS, linhas):
        tr = int(got["tr_ms"]) if got["tr_ms"] else None
        excl = got["excluido"]
        if esp["tr"] is None:
            ok_tr = tr is None
        else:
            ok_tr = tr is not None and abs(tr - esp["tr"]) <= DT + 1   # 1 quadro de tolerância
        ok_ex = excl.startswith(esp["excl"]) if esp["excl"] else excl == ""
        marca = "ok " if (ok_tr and ok_ex) else "FALHA"
        print(f"[{marca}] trial {got['trial']}: tr={tr} (esperado {esp['tr']}) "
              f"excluido='{excl}' (esperado '{esp['excl']}')")
        if not (ok_tr and ok_ex):
            falhas.append(got["trial"])

    print()
    if falhas:
        print(f"FALHOU nos trials {falhas}")
        return 1
    print("Todos os casos passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
