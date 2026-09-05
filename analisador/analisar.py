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

Regras implementadas (Fernald, Zangl, Portillo & Marchman, 2008; Peekbank)
  · Janela de análise: 300–1800 ms após o onset da palavra-alvo.
  · Acurácia: proporção de tempo no alvo sobre (alvo + distrator) na janela.
    Conta em TODO trial que tenha dado — inclusive quando a criança nunca sai
    do distrator (é o caso de não-compreensão, acurácia ≈ 0) e quando o shift
    veio cedo demais. Só sai da acurácia o trial sem dado utilizável: sem
    amostras na janela, olhar fora em mais da metade dela, ou sem fixação
    conhecida no instante do onset.
  · TR só em trials que começam no DISTRATOR (nos que já começam no alvo não há
    para onde reagir). O TR é a latência do INÍCIO do deslocamento — o primeiro
    quadro em que o olhar deixa o distrator —, não a chegada ao alvo. É assim
    em Fernald e no `rt` do Peekbank; medir a chegada somaria a duração da
    sacada e dos quadros de transição ao TR.
  · Tipo do shift (`shift_tipo`): D→T quando a primeira fixação sustentada
    depois de sair do distrator é no alvo; D→fora quando é fora da tela (sem
    TR); T→D / T→fora para trials que começam no alvo (só acurácia); nenhum
    quando o olhar nunca sai do distrator.
  · Piso de 300 ms: shift D→T antes de 300 ms não vira TR (sacada iniciada
    antes de a palavra poder ter sido processada) — mas a acurácia conta.
  · Fixação "sustentada" = mesma direção por pelo menos SUSTENTA_MS (100 ms),
    medida em tempo e não em quadros, para não depender da taxa do vídeo.
  · A fixação no onset tem de ser observada a menos de TOL_ONSET_MS do onset;
    uma amostra antiga (lacuna na codificação) não vale como estado inicial.
  · Baseline: proporção no alvo na janela anterior ao onset, para detectar viés;
    o resumo traz também a acurácia corrigida pelo baseline (acurácia − baseline).
  · TR da sessão é reportado pela MEDIANA — a distribuição é assimétrica à direita.

Colunas de por_trial.csv
  excluido   : motivo pelo qual o trial NÃO conta nem para acurácia (vazio = conta)
  sem_tr     : motivo pelo qual não há TR neste trial (vazio = há TR)
  shift_tipo : D>T, D>fora, T>D, T>fora, nenhum, ou vazio quando excluído
  t_saida_ms : latência (ms após o onset) em que o olhar deixou a fixação inicial
"""
from __future__ import annotations
import argparse, csv, json, os, statistics
from typing import Optional

JANELA = (300.0, 1800.0)
BASELINE_MS = 2000.0
SUSTENTA_MS = 100.0      # fixação precisa durar isto para contar (≈3 quadros a 30 fps)
TOL_ONSET_MS = 40.0      # a fixação "no onset" tem de ter sido vista a menos disto do onset
MAX_AWAY = 0.50          # exclui o trial se mais da metade da janela for "away"
MIN_TRIALS_SESSAO = 12


def ler_olhar(caminho: str) -> list[tuple[float, str]]:
    """Lê a codificação do olhar, aceitando os nomes de coluna mais comuns."""
    amostras: list[tuple[float, str]] = []
    with open(caminho, newline="", encoding="utf-8") as f:
        # o codificador manual grava a convenção esquerda/direita como comentário
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
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


def intervalo_amostral(amostras) -> float:
    """Intervalo típico entre amostras (mediana), em ms. 33,3 a 30 fps."""
    if len(amostras) < 2:
        return 1000.0 / 30
    ts = [t for t, _ in amostras]
    d = sorted(b - a for a, b in zip(ts, ts[1:]) if b > a)
    return d[len(d) // 2] if d else 1000.0 / 30


def estado_no_onset(amostras, onset: float, dt: float) -> Optional[str]:
    """Estado do olhar no instante do onset.

    Vale a última amostra até o onset, desde que esteja a menos de
    TOL_ONSET_MS (ou de um intervalo amostral) dele. Sem isso, uma lacuna na
    codificação faz um olhar de 1,5 s antes virar "estado inicial" e gerar um
    TR que nunca existiu.
    """
    tol = max(TOL_ONSET_MS, dt * 1.5)
    antes = [(t, g) for t, g in amostras if t <= onset]
    if antes and onset - antes[-1][0] <= tol:
        return antes[-1][1]
    depois = [(t, g) for t, g in amostras if t > onset]
    if depois and depois[0][0] - onset <= tol:
        return depois[0][1]
    return None


def fixacoes(seq, dt: float):
    """Agrupa amostras consecutivas iguais em fixações (inicio, fim, direcao).

    `fim` é o instante da última amostra mais um intervalo amostral, para que
    uma fixação de 3 quadros a 30 fps meça 100 ms e não 67.
    """
    out = []
    for t, g in seq:
        if out and out[-1][2] == g:
            out[-1][1] = t + dt
        else:
            out.append([t, t + dt, g])
    return [(a, b, g) for a, b, g in out]


def classifica_shift(amostras, onset: float, inicio: str, lado: str, dist: str,
                     fim_busca: float, dt: float) -> tuple[str, Optional[float]]:
    """Primeiro deslocamento sustentado a partir da fixação inicial.

    Devolve (tipo, t_saida_ms). t_saida é a latência, contada do onset, do
    primeiro quadro em que o olhar deixa a fixação inicial — a definição de
    Fernald. O tipo vem da primeira fixação SUSTENTADA (≥ SUSTENTA_MS) que
    não é a inicial: alvo, distrator ou fora. Quadros soltos de transição
    (a sacada em si, um quadro mal classificado) não decidem o destino nem
    devolvem a criança ao estado inicial.
    """
    seq = [(t, g) for t, g in amostras if onset <= t < fim_busca]
    fx = fixacoes(seq, dt)
    origem = "D" if inicio == dist else "T"
    saiu_em = None
    for a, b, g in fx:
        if g == inicio and saiu_em is None:
            continue
        if saiu_em is None:
            saiu_em = a - onset
        if (b - a) >= SUSTENTA_MS - 1e-6:
            if g == inicio:
                # voltou e ficou: o que houve antes foi só transição
                saiu_em = None
                continue
            destino = "T" if g == lado else ("D" if g == dist else "fora")
            return f"{origem}>{destino}", saiu_em
    return "nenhum", None


def analisa_trial(onset: float, lado: str, amostras) -> dict:
    dist = "right" if lado == "left" else "left"
    jini, jfim = onset + JANELA[0], onset + JANELA[1]
    dt = intervalo_amostral(amostras)

    base = fatia(amostras, onset - BASELINE_MS, onset)
    n_ba, n_bd = sum(g == lado for _, g in base), sum(g == dist for _, g in base)
    baseline = n_ba / (n_ba + n_bd) if (n_ba + n_bd) else None

    vazio = {"n": 0, "acuracia": None, "tr_ms": None, "inicio": None, "shift_tipo": "",
             "t_saida_ms": None, "prop_away": "", "baseline": baseline, "sem_tr": ""}
    janela = fatia(amostras, jini, jfim)
    if not janela:
        return {**vazio, "excluido": "sem_dados_na_janela"}

    n_away = sum(g == "away" for _, g in janela)
    prop_away = n_away / len(janela)
    n_alvo = sum(g == lado for _, g in janela)
    n_dist = sum(g == dist for _, g in janela)
    acuracia = n_alvo / (n_alvo + n_dist) if (n_alvo + n_dist) else None

    base_out = {**vazio, "n": len(janela), "acuracia": acuracia,
                "prop_away": round(prop_away, 3)}

    # --- exclusões de verdade: sem dado utilizável, nem para acurácia ---
    if prop_away > MAX_AWAY or acuracia is None:
        return {**base_out, "acuracia": None, "excluido": f"olhar_fora_{prop_away:.0%}"}

    inicio = estado_no_onset(amostras, onset, dt)
    if inicio is None:
        return {**base_out, "excluido": "sem_fixacao_no_onset"}
    if inicio == "away":
        return {**base_out, "inicio": "away", "excluido": "olhando_fora_no_onset"}

    # --- daqui em diante o trial conta para a acurácia ---
    tipo, saida = classifica_shift(amostras, onset, inicio, lado, dist, jfim, dt)
    out = {**base_out, "inicio": inicio, "shift_tipo": tipo, "excluido": "",
           "t_saida_ms": None if saida is None else round(saida)}

    if inicio == lado:
        return {**out, "sem_tr": "comecou_no_alvo"}
    if tipo == "nenhum":
        return {**out, "sem_tr": "sem_shift_na_janela"}
    if tipo == "D>fora":
        return {**out, "sem_tr": "shift_para_fora"}
    if saida < JANELA[0]:
        return {**out, "sem_tr": f"shift_antecipatorio_{saida:.0f}ms"}
    return {**out, "tr_ms": saida}


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

    linhas, trs, accs, accs_corr, bases = [], [], [], [], []
    for t in sinc["trials"]:
        onset = t.get("t_alvo_onset_ms")
        if onset is None:
            linhas.append({"trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
                           "excluido": "sem_bipe_no_video"})
            continue

        r = analisa_trial(float(onset), t["ladoAlvo"], amostras)

        # TR de sessão com TTS não é confiável: o instante da palavra dentro da
        # frase sintetizada não é conhecido com precisão. A acurácia continua
        # valendo — ela não depende do instante exato.
        if t.get("rt_valido") == "nao" and not a.permitir_tts and r.get("tr_ms") is not None:
            r["tr_ms"] = None
            r["sem_tr"] = "audio_tts_tr_invalido"

        linhas.append({
            "trial": t["trial"], "alvo": t["alvo"], "ladoAlvo": t["ladoAlvo"],
            "onset_ms": round(float(onset)), "inicio": r.get("inicio") or "",
            "n_amostras": r.get("n", 0), "prop_away": r.get("prop_away", ""),
            "baseline": "" if r.get("baseline") is None else round(r["baseline"], 3),
            "acuracia": "" if r.get("acuracia") is None else round(r["acuracia"], 3),
            "shift_tipo": r.get("shift_tipo", ""),
            "t_saida_ms": "" if r.get("t_saida_ms") is None else r["t_saida_ms"],
            "tr_ms": "" if r.get("tr_ms") is None else round(r["tr_ms"]),
            "sem_tr": r.get("sem_tr", ""),
            "excluido": r.get("excluido", ""),
        })
        if r.get("acuracia") is not None and not r["excluido"]:
            accs.append(r["acuracia"])
            if r.get("baseline") is not None:
                accs_corr.append(r["acuracia"] - r["baseline"])
        if r.get("tr_ms") is not None:
            trs.append(r["tr_ms"])
        if r.get("baseline") is not None:
            bases.append(r["baseline"])

    cols = ["trial", "alvo", "ladoAlvo", "onset_ms", "inicio", "n_amostras",
            "prop_away", "baseline", "acuracia", "shift_tipo", "t_saida_ms",
            "tr_ms", "sem_tr", "excluido"]
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
    sem_tr: dict[str, int] = {}
    tipos: dict[str, int] = {}
    for l in validos:
        if l["sem_tr"]:
            k = l["sem_tr"].split("_")[0] if l["sem_tr"].startswith("shift_antecipatorio") else l["sem_tr"]
            sem_tr[k] = sem_tr.get(k, 0) + 1
        if l["shift_tipo"]:
            tipos[l["shift_tipo"]] = tipos.get(l["shift_tipo"], 0) + 1

    q = statistics.quantiles(trs, n=4) if len(trs) >= 2 else None
    resumo = {
        "trials_no_log": len(linhas),
        "trials_validos": len(validos),
        "exclusoes": motivos,
        "acuracia_media": round(statistics.mean(accs), 3) if accs else None,
        "acuracia_corrigida_baseline": round(statistics.mean(accs_corr), 3) if accs_corr else None,
        "tr_mediano_ms": round(statistics.median(trs)) if trs else None,
        "tr_iqr_ms": [round(q[0]), round(q[2])] if q else None,
        "tr_n": len(trs),
        "sem_tr": sem_tr,
        "shift_tipos": tipos,
        "baseline_medio": round(statistics.mean(bases), 3) if bases else None,
        "sessao_utilizavel": len(validos) >= MIN_TRIALS_SESSAO,
    }
    with open(os.path.join(a.saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)

    print(f"Trials no log      : {resumo['trials_no_log']}")
    print(f"Trials válidos     : {resumo['trials_validos']}")
    print(f"Acurácia média     : {resumo['acuracia_media']}"
          f"   (corrigida pelo baseline: {resumo['acuracia_corrigida_baseline']})")
    print(f"TR mediano         : {resumo['tr_mediano_ms']} ms (n={resumo['tr_n']}, "
          f"IQR {resumo['tr_iqr_ms']})")
    if tipos:
        print("Shifts             : " + ", ".join(f"{k}={v}" for k, v in sorted(tipos.items())))
    if sem_tr:
        print("Sem TR             : " + ", ".join(f"{k}={v}" for k, v in sorted(sem_tr.items())))
    print(f"Baseline médio     : {resumo['baseline_medio']}"
          "   (~0,5 = sem viés de lado)")
    if motivos:
        print("Exclusões          : " + ", ".join(f"{k}={v}" for k, v in sorted(motivos.items())))
    if not resumo["sessao_utilizavel"]:
        print(f"\n⚠ Menos de {MIN_TRIALS_SESSAO} trials válidos — não interprete esta sessão.")
    print(f"\nArquivos em {a.saida}")


if __name__ == "__main__":
    main()
