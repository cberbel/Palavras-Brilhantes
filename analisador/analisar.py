#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise Looking-While-Listening (paradigma Fernald).

Entradas
  sincronizacao.json : saída do sincronizar.py — dá t_alvo_onset_ms de cada trial
  olhar.csv          : codificação do olhar quadro a quadro, colunas t_ms e olhar
                       (olhar ∈ left/right/away). Vem do OWLET, do iCatcher+ ou
                       de codificação manual, na mesma base de tempo do vídeo.

Saídas
  por_trial.csv : uma linha por trial, com TR, acurácia, baseline e o motivo de
                  exclusão quando houver
  resumo.json   : medidas da sessão

Regras implementadas (Fernald, Zangl, Portillo & Marchman, 2008)
  · Janela de análise: 300–1800 ms após o onset da palavra-alvo.
  · TR só em trials que começam no DISTRATOR (nos que já começam no alvo não há
    para onde reagir).
  · Piso de 300 ms como EXCLUSÃO, não como recorte: se a criança já mudou para o
    alvo antes de 300 ms, o trial inteiro sai. Uma sacada nesse prazo não pode
    ter sido causada pela palavra, e recortá-la em vez de excluí-la produz um TR
    artificial de exatamente 300 ms.
  · O deslocamento precisa se sustentar (padrão: 3 quadros) para contar. Sem
    isso, um único quadro mal classificado vira um TR.
  · Acurácia: proporção de tempo no alvo sobre (alvo + distrator) na janela.
  · Baseline: proporção no alvo na janela anterior ao onset, para detectar viés.
  · TR da sessão é reportado pela MEDIANA — a distribuição é assimétrica à direita.
"""
from __future__ import annotations
import argparse, csv, json, os, statistics
from typing import Optional

JANELA = (300.0, 1800.0)
BASELINE_MS = 2000.0
N_QUADROS_SUSTENTA = 3
MAX_AWAY = 0.50          # exclui o trial se mais da metade da janela for "away"
MIN_TRIALS_SESSAO = 12


def ler_olhar(caminho: str) -> list[tuple[float, str]]:
    """Lê a codificação do olhar, aceitando os nomes de coluna mais comuns."""
    amostras: list[tuple[float, str]] = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r.get("t_ms") or r.get("time_ms") or r.get("timestamp_ms") or r.get("t")
            g = (r.get("olhar") or r.get("gaze") or r.get("look") or
                 r.get("annotation") or r.get("direcao") or "").strip().lower()
            if t is None or not g:
                continue
            if g in ("l", "left", "esquerda", "e"):
                g = "left"
            elif g in ("r", "right", "direita", "d"):
                g = "right"
            else:
                g = "away"
            try:
                amostras.append((float(t), g))
            except ValueError:
                continue
    amostras.sort(key=lambda p: p[0])
    return amostras


def fatia(amostras, ini: float, fim: float):
    return [(t, g) for t, g in amostras if ini <= t < fim]


def estado_no_onset(amostras, onset: float) -> Optional[str]:
    """Último estado observado até o onset. None se não há dado antes dele."""
    antes = [g for t, g in amostras if t <= onset]
    return antes[-1] if antes else None


def primeiro_shift_sustentado(janela, alvo: str, n: int) -> Optional[float]:
    """Instante do primeiro bloco de `n` quadros consecutivos no alvo."""
    seq = 0
    for i, (t, g) in enumerate(janela):
        if g == alvo:
            seq += 1
            if seq >= n:
                return janela[i - n + 1][0]
        else:
            seq = 0
    return None


def analisa_trial(onset: float, lado: str, amostras) -> dict:
    dist = "right" if lado == "left" else "left"
    jini, jfim = onset + JANELA[0], onset + JANELA[1]

    base = fatia(amostras, onset - BASELINE_MS, onset)
    n_ba, n_bd = sum(g == lado for _, g in base), sum(g == dist for _, g in base)
    baseline = n_ba / (n_ba + n_bd) if (n_ba + n_bd) else None

    janela = fatia(amostras, jini, jfim)
    if not janela:
        return {"n": 0, "acuracia": None, "tr_ms": None, "inicio": None,
                "baseline": baseline, "excluido": "sem_dados_na_janela"}

    n_away = sum(g == "away" for _, g in janela)
    prop_away = n_away / len(janela)
    n_alvo = sum(g == lado for _, g in janela)
    n_dist = sum(g == dist for _, g in janela)
    acuracia = n_alvo / (n_alvo + n_dist) if (n_alvo + n_dist) else None

    base_out = {"n": len(janela), "acuracia": acuracia, "tr_ms": None,
                "prop_away": round(prop_away, 3), "baseline": baseline}

    if prop_away > MAX_AWAY:
        return {**base_out, "inicio": None, "acuracia": None,
                "excluido": f"olhar_fora_{prop_away:.0%}"}

    inicio = estado_no_onset(amostras, onset)
    if inicio is None:
        return {**base_out, "inicio": None, "excluido": "sem_fixacao_no_onset"}
    if inicio == "away":
        return {**base_out, "inicio": "away", "excluido": "olhando_fora_no_onset"}

    # Procura o primeiro deslocamento sustentado a partir do onset, olhando ALÉM
    # da janela — a sustentação pode atravessar a fronteira dos 300 ms. Só depois
    # aplica-se o piso à latência encontrada. Procurar apenas dentro de [0,300)
    # deixaria passar um shift que começa em 250 ms e se sustenta até 350 ms.
    if inicio == dist:
        busca = fatia(amostras, onset, jfim)
        t_shift = primeiro_shift_sustentado(busca, lado, N_QUADROS_SUSTENTA)
        if t_shift is None:
            return {**base_out, "inicio": inicio, "excluido": "sem_shift_na_janela"}
        tr = t_shift - onset
        if tr < JANELA[0]:
            return {**base_out, "inicio": inicio,
                    "excluido": f"shift_antecipatorio_{tr:.0f}ms"}
        return {**base_out, "inicio": inicio, "tr_ms": tr, "excluido": ""}

    # começou no alvo: acurácia vale, TR não se aplica
    return {**base_out, "inicio": inicio, "excluido": ""}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sincronizacao", help="sincronizacao.json do sincronizar.py")
    ap.add_argument("olhar", help="codificação do olhar (csv)")
    ap.add_argument("--saida", default="./resultados")
    ap.add_argument("--permitir-tts", action="store_true",
                    help="calcula TR mesmo com áudio de TTS (não recomendado)")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)

    with open(a.sincronizacao, encoding="utf-8") as f:
        sinc = json.load(f)
    if sinc.get("alerta"):
        print("⚠ " + sinc["alerta"] + "\n")

    amostras = ler_olhar(a.olhar)
    if not amostras:
        raise SystemExit("Nenhum dado de olhar carregado. Confira as colunas de "
                         f"{a.olhar} (esperado t_ms e olhar).")

    linhas, trs, accs, bases = [], [], [], []
    for t in sinc["trials"]:
        onset = t.get("t_alvo_onset_ms")
        if onset is None:
            linhas.append({"trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
                           "excluido": "sem_onset_no_log"})
            continue

        r = analisa_trial(float(onset), t["ladoAlvo"], amostras)

        # TR de sessão com TTS não é confiável: o instante da palavra dentro da
        # frase sintetizada não é conhecido com precisão.
        if t.get("rt_valido") == "nao" and not a.permitir_tts:
            r["tr_ms"] = None
            if not r["excluido"]:
                r["excluido"] = "audio_tts_tr_invalido"

        linhas.append({
            "trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
            "onset_ms": round(float(onset)), "inicio": r.get("inicio") or "",
            "n_amostras": r.get("n", 0), "prop_away": r.get("prop_away", ""),
            "baseline": "" if r.get("baseline") is None else round(r["baseline"], 3),
            "acuracia": "" if r.get("acuracia") is None else round(r["acuracia"], 3),
            "tr_ms": "" if r.get("tr_ms") is None else round(r["tr_ms"]),
            "excluido": r.get("excluido", ""),
        })
        if r.get("acuracia") is not None and not r["excluido"]:
            accs.append(r["acuracia"])
        if r.get("tr_ms") is not None:
            trs.append(r["tr_ms"])
        if r.get("baseline") is not None:
            bases.append(r["baseline"])

    cols = ["trial", "alvo", "ladoAlvo", "onset_ms", "inicio", "n_amostras",
            "prop_away", "baseline", "acuracia", "tr_ms", "excluido"]
    caminho = os.path.join(a.saida, "por_trial.csv")
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)

    validos = [l for l in linhas if not l["excluido"]]
    motivos: dict[str, int] = {}
    for l in linhas:
        if l["excluido"]:
            motivos[l["excluido"]] = motivos.get(l["excluido"], 0) + 1

    resumo = {
        "trials_no_log": len(linhas),
        "trials_validos": len(validos),
        "exclusoes": motivos,
        "acuracia_media": round(statistics.mean(accs), 3) if accs else None,
        "tr_mediano_ms": round(statistics.median(trs)) if trs else None,
        "tr_n": len(trs),
        "baseline_medio": round(statistics.mean(bases), 3) if bases else None,
        "sessao_utilizavel": len(validos) >= MIN_TRIALS_SESSAO,
    }
    with open(os.path.join(a.saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)

    print(f"Trials no log      : {resumo['trials_no_log']}")
    print(f"Trials válidos     : {resumo['trials_validos']}")
    print(f"Acurácia média     : {resumo['acuracia_media']}")
    print(f"TR mediano         : {resumo['tr_mediano_ms']} ms (n={resumo['tr_n']})")
    print(f"Baseline médio     : {resumo['baseline_medio']}"
          "   (~0,5 = sem viés de lado)")
    if motivos:
        print("Exclusões          : " + ", ".join(f"{k}={v}" for k, v in sorted(motivos.items())))
    if not resumo["sessao_utilizavel"]:
        print(f"\n⚠ Menos de {MIN_TRIALS_SESSAO} trials válidos — não interprete esta sessão.")
    print(f"\nArquivos em {a.saida}")


if __name__ == "__main__":
    main()
