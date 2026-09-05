#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste do analisar.py com dados sintéticos de comportamento conhecido.

Cada trial é construído para exercitar uma regra do protocolo. O teste falha se
o analisador não recuperar exatamente o que foi plantado.

Além do TR, confere o que foi corrigido em 05/09/2026:
  · trial sem shift conta para a acurácia (≈0), não é excluído;
  · shift antecipatório fica sem TR mas conta para a acurácia;
  · TR é a SAÍDA do distrator, mesmo que haja quadros "fora" antes de chegar
    ao alvo (D>T), e um shift que se sustenta fora da tela é D>fora, sem TR;
  · lacuna na codificação antes do onset exclui o trial (sem fixação no onset).
"""
import csv, json, os, subprocess, sys, tempfile

FPS = 30.0
DT = 1000.0 / FPS          # 33,33 ms por quadro
PASSO_TRIAL = 10_000.0     # trials bem separados no tempo do vídeo

# Cada caso: dict com o comportamento plantado e o esperado.
#   lado      : lado do alvo
#   inicio    : "dist" | "alvo" — onde o olhar está no onset
#   shift     : ms após o onset em que o olhar sai da fixação inicial (None = nunca)
#   via_fora  : ms de "away" entre sair do distrator e chegar ao alvo (0 = direto)
#   destino   : "alvo" | "fora" — onde o olhar se sustenta depois do shift
#   sustenta  : False = um único quadro no destino e volta (não pode virar TR)
#   tudo_fora : trial inteiro "away"
#   lacuna    : ms sem amostra imediatamente antes do onset
CASOS = [
    dict(lado="left",  inicio="dist", shift=600.0,
         esp=dict(tr=600, excl="", sem_tr="", tipo="D>T", acc_min=0.6)),
    dict(lado="right", inicio="dist", shift=150.0,
         esp=dict(tr=None, excl="", sem_tr="shift_antecipatorio", tipo="D>T", acc_min=0.9)),
    dict(lado="left",  inicio="alvo", shift=None,
         esp=dict(tr=None, excl="", sem_tr="comecou_no_alvo", tipo="nenhum", acc_min=0.9)),
    dict(lado="right", inicio="dist", shift=700.0, tudo_fora=True,
         esp=dict(tr=None, excl="olhar_fora", sem_tr="", tipo="")),
    dict(lado="left",  inicio="dist", shift=900.0, sustenta=False,
         esp=dict(tr=None, excl="", sem_tr="sem_shift_na_janela", tipo="nenhum", acc_max=0.1)),
    # sai do distrator em 500 ms, passa 67 ms "fora" (sacada) e chega ao alvo:
    # TR = 500 (saída), não 567 (chegada)
    dict(lado="right", inicio="dist", shift=500.0, via_fora=2 * DT,
         esp=dict(tr=500, excl="", sem_tr="", tipo="D>T")),
    # sai do distrator em 500 ms, fica 500 ms fora da tela e volta ao distrator:
    # D>fora, sem TR, mas conta (fora = 1/3 da janela, abaixo do limite de 50%)
    dict(lado="left",  inicio="dist", shift=500.0, destino="fora", volta=500.0,
         esp=dict(tr=None, excl="", sem_tr="shift_para_fora", tipo="D>fora", acc_max=0.05)),
    # nunca sai do distrator: acurácia 0, sem TR, NÃO excluído
    dict(lado="right", inicio="dist", shift=None,
         esp=dict(tr=None, excl="", sem_tr="sem_shift_na_janela", tipo="nenhum", acc_max=0.05)),
    # codificação começa só 300 ms depois do onset: sem fixação no onset → excluído
    dict(lado="left",  inicio="dist", shift=600.0, lacuna=1500.0,
         esp=dict(tr=None, excl="sem_fixacao_no_onset", sem_tr="", tipo="")),
]


def constroi(tmp):
    trials, amostras = [], []
    for i, c in enumerate(CASOS):
        onset = (i + 1) * PASSO_TRIAL
        lado = c["lado"]; inicio = c["inicio"]; shift = c.get("shift")
        via_fora = c.get("via_fora", 0.0); destino = c.get("destino", "alvo")
        sustenta = c.get("sustenta", True); fora = c.get("tudo_fora", False)
        lacuna = c.get("lacuna", 0.0); volta = c.get("volta")
        dist = "right" if lado == "left" else "left"
        trials.append({"trial": i + 1, "alvo": f"item{i+1}", "ladoAlvo": lado,
                       "t_bipe_ms": onset - 3000, "t_alvo_onset_ms": onset,
                       "rt_valido": "sim"})
        # de -2000 ms (baseline) a +2000 ms após o onset.
        # O tempo é calculado a partir do índice, não acumulado, senão o erro de
        # ponto flutuante desloca um quadro perto das fronteiras.
        n_no_destino = 0
        for k in range(int(4000.0 / DT)):
            t = onset - 2000.0 + k * DT
            if lacuna and onset - lacuna <= t < onset + 300.0:
                continue                      # buraco na codificação
            estado_inicial = dist if inicio == "dist" else lado
            if fora:
                g = "away"
            elif t < onset or shift is None or t < onset + shift:
                g = estado_inicial
            elif t < onset + shift + via_fora:
                g = "away"                    # sacada / transição
            elif volta is not None and t >= onset + shift + via_fora + volta:
                g = estado_inicial            # voltou para onde estava
            else:
                alvo_g = lado if destino == "alvo" else "away"
                if sustenta:
                    g = alvo_g
                else:
                    # um único quadro no destino, depois volta — não pode virar TR
                    g = alvo_g if n_no_destino < 1 else estado_inicial
                    if g == alvo_g:
                        n_no_destino += 1
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
    for c, got in zip(CASOS, linhas):
        esp = c["esp"]
        tr = int(got["tr_ms"]) if got["tr_ms"] else None
        excl, sem_tr, tipo = got["excluido"], got["sem_tr"], got["shift_tipo"]
        acc = float(got["acuracia"]) if got["acuracia"] else None
        problemas = []
        if esp["tr"] is None:
            if tr is not None:
                problemas.append(f"tr={tr} (esperado nenhum)")
        elif tr is None or abs(tr - esp["tr"]) > DT + 1:   # 1 quadro de tolerância
            problemas.append(f"tr={tr} (esperado {esp['tr']})")
        if not (excl.startswith(esp["excl"]) if esp["excl"] else excl == ""):
            problemas.append(f"excluido='{excl}' (esperado '{esp['excl']}')")
        if not (sem_tr.startswith(esp["sem_tr"]) if esp["sem_tr"] else sem_tr == ""):
            problemas.append(f"sem_tr='{sem_tr}' (esperado '{esp['sem_tr']}')")
        if tipo != esp["tipo"]:
            problemas.append(f"shift_tipo='{tipo}' (esperado '{esp['tipo']}')")
        if "acc_min" in esp and (acc is None or acc < esp["acc_min"]):
            problemas.append(f"acurácia={acc} (esperado ≥ {esp['acc_min']})")
        if "acc_max" in esp and (acc is None or acc > esp["acc_max"]):
            problemas.append(f"acurácia={acc} (esperado ≤ {esp['acc_max']})")
        if esp["excl"] == "" and acc is None:
            problemas.append("acurácia vazia num trial que deveria contar")
        marca = "ok " if not problemas else "FALHA"
        print(f"[{marca}] trial {got['trial']}: tr={tr} tipo={tipo or '-'} "
              f"acc={acc} sem_tr='{sem_tr}' excluido='{excl}'"
              + ("" if not problemas else "  ← " + "; ".join(problemas)))
        if problemas:
            falhas.append(got["trial"])

    # a acurácia da sessão tem de incluir o trial de não-compreensão (≈0)
    with open(os.path.join(saida, "resumo.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    validos_esperados = sum(1 for c in CASOS if c["esp"]["excl"] == "")
    if resumo["trials_validos"] != validos_esperados:
        print(f"[FALHA] trials_validos={resumo['trials_validos']} (esperado {validos_esperados})")
        falhas.append("resumo")
    else:
        print(f"[ok ] trials_validos={resumo['trials_validos']}, "
              f"acurácia média={resumo['acuracia_media']}, "
              f"corrigida={resumo['acuracia_corrigida_baseline']}, tipos={resumo['shift_tipos']}")

    print()
    if falhas:
        print(f"FALHOU nos trials {falhas}")
        return 1
    print("Todos os casos passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
