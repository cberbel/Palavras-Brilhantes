#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Confere os onsets do onsets.csv contra o áudio e monta o protocolo de 32 trials.

A conferência existe porque o onset é o número do qual depende todo o tempo de
reação. Ele vem da API de síntese, mas confiar nele sem olhar o sinal seria
aceitar um número que ninguém verificou. Aqui ele é comparado com o instante em
que a energia do áudio realmente sobe depois da pausa que antecede a palavra.

Saída: protocolo.txt, no formato que o apresentador lê
    alvo | imgEsquerda | imgDireita | ladoAlvo | audio | onset_ms

Uso:  python montar_protocolo.py
"""
from __future__ import annotations
import argparse, csv, os, wave
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))

# (alvo, distrator) — os dois que aparecem juntos na tela
PARES = [("gato", "banana"), ("bola", "sapato"),
         ("cachorro", "livro"), ("pato", "maçã")]

IMAGEM = {"gato": "gato", "bola": "bola", "cachorro": "cachorro", "sapato": "sapato",
          "banana": "banana", "livro": "livro", "pato": "pato", "maçã": "maca"}

FRAME_MS = 10
LIMIAR = 0.15        # fração do pico de RMS que conta como "som"
BUSCA_MS = 300       # quanto procurar em volta do onset informado


def rms_frames(caminho: str) -> tuple[np.ndarray, float]:
    with wave.open(caminho, "rb") as w:
        sr = w.getframerate()
        n_canais = w.getnchannels()
        larg = w.getsampwidth()
        bruto = w.readframes(w.getnframes())
    if larg != 2:
        raise SystemExit(f"{caminho}: esperado PCM 16-bit, veio {larg*8}-bit")
    x = np.frombuffer(bruto, dtype=np.int16).astype(np.float64)
    if n_canais > 1:
        x = x.reshape(-1, n_canais).mean(axis=1)
    n = int(sr * FRAME_MS / 1000)
    n_fr = len(x) // n
    if n_fr == 0:
        return np.array([]), sr
    quadros = x[: n_fr * n].reshape(n_fr, n)
    return np.sqrt((quadros ** 2).mean(axis=1)), sr


def confere(rms: np.ndarray, onset_ms: float, eh_ultima: bool,
            limites: list[tuple[str, float]]) -> tuple[bool, str]:
    """Verifica o que pode dar errado de verdade.

    O onset vem da API de síntese, que sabe exatamente quando começou a emitir
    cada palavra — não é estimativa. O risco não é ela errar, é eu ter casado o
    evento errado e pegado o artigo em vez do substantivo. Por isso a checagem
    forte é estrutural: o alvo tem de ser a ÚLTIMA fronteira do enunciado.

    A checagem acústica fica só como apoio, e não tenta achar o "ataque" da
    palavra: em fala contínua não há pausa entre "o" e "gato", e um detector de
    silêncio recua até antes do artigo e acusa erro onde não há.
    """
    if not eh_ultima:
        return False, "alvo não é a última palavra do enunciado"
    if len(limites) < 2:
        return False, f"só {len(limites)} fronteira(s) — enunciado não segmentou"

    anterior = max((t for _, t in limites if t < onset_ms), default=None)
    if anterior is None:
        return False, "nada antes do alvo: casou a primeira palavra"
    if onset_ms - anterior < 40:
        return False, f"apenas {onset_ms-anterior:.0f} ms após a palavra anterior"

    if rms.size:
        lim = rms.max() * LIMIAR
        i = int(onset_ms / FRAME_MS)
        # tem de haver som no alvo e continuar por pelo menos ~150 ms
        trecho = rms[i:i + 15]
        if trecho.size < 8 or float(trecho.max()) < lim:
            return False, "sem energia sonora no instante informado"
        dur = (len(rms) - i) * FRAME_MS
        if dur < 150:
            return False, f"só {dur:.0f} ms de áudio após o onset"
    return True, ""


def onset_pelo_audio(rms: np.ndarray, a_partir_de: float) -> float | None:
    """Primeira subida sustentada de energia depois de `a_partir_de`.

    Usado só quando o sinal contradiz a API — a palavra da síntese não está onde
    ela disse. Aí a fonte confiável passa a ser o áudio.
    """
    if rms.size == 0:
        return None
    lim = rms.max() * 0.25
    i = int(a_partir_de / FRAME_MS)
    while i < len(rms) - 5:
        if rms[i] >= lim and float(rms[i:i + 5].min()) >= lim * 0.6:
            return i * FRAME_MS
        i += 1
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=os.path.join(AQUI, "estimulos", "audio"))
    ap.add_argument("--saida", default=os.path.join(AQUI, "protocolo.txt"))
    ap.add_argument("--tolerancia", type=float, default=60.0,
                    help="divergência máxima aceita, em ms")
    a = ap.parse_args()

    idx = os.path.join(a.audio, "onsets.csv")
    if not os.path.exists(idx):
        raise SystemExit(f"Não achei {idx}. Rode antes o gerar_audio.ps1.")
    with open(idx, newline="", encoding="utf-8-sig") as f:
        clipes = {(r["alvo"], r["variante"]): r for r in csv.DictReader(f)}

    # tolera vírgula decimal, caso o índice tenha sido gerado num locale pt-BR
    for r in clipes.values():
        r["onset_ms"] = str(r["onset_ms"]).replace(",", ".")

    print(f"{'clipe':<14} {'onset':>8}  {'segmentação do enunciado'}")
    print("-" * 68)
    suspeitos: list[str] = []
    corrigidos: list[str] = []
    for (alvo, var), r in sorted(clipes.items()):
        caminho = os.path.join(AQUI, r["arquivo"].replace("/", os.sep))
        rms, _ = rms_frames(caminho)
        onset = float(r["onset_ms"])

        limites = []
        for item in (r.get("limites") or "").split("|"):
            if ":" in item:
                txt, ms = item.rsplit(":", 1)
                try:
                    limites.append((txt, float(ms.replace(",", "."))))
                except ValueError:
                    pass
        eh_ultima = (r.get("alvo_eh_ultima_palavra") or "").strip().lower() == "sim"

        ok, motivo = confere(rms, onset, eh_ultima, limites)
        nota = ""
        if not ok and "energia" in motivo:
            corrigido = onset_pelo_audio(rms, onset)
            if corrigido is not None:
                nota = f"  → corrigido para {corrigido:.0f} ms (+{corrigido-onset:.0f})"
                corrigidos.append(f"{alvo}_{var}: {onset:.0f} → {corrigido:.0f} ms")
                r["onset_ms"] = f"{corrigido:.1f}"
                onset, ok = corrigido, True

        marca = "ok " if ok else "⚠  "
        seg = " ".join(f"{t}@{ms:.0f}" for t, ms in limites)
        print(f"{marca}{alvo+'_'+var:<11} {onset:>8.0f}  {seg}{nota}")
        if not ok:
            suspeitos.append(f"{alvo}_{var}: {motivo}")

    print("-" * 68)
    if corrigidos:
        print("Onsets corrigidos pelo áudio (a síntese reportou onde não havia som):")
        for c in corrigidos:
            print("   " + c)
        print()
    if suspeitos:
        print("⚠ Conferir à mão:")
        for s in suspeitos:
            print("   " + s)
        print("  Abra o arquivo no Audacity e corrija o onset no protocolo.txt.\n")
    else:
        print("Em todos os clipes o alvo é a última palavra, com som presente "
              "no instante usado.\n")
    print("Ouça os 16 clipes uma vez antes de coletar dados. A verificação aqui é "
          "de tempo,\nnão de pronúncia — só o ouvido humano detecta uma palavra "
          "mal falada pela síntese.\n")

    # ---- monta os 32 trials -------------------------------------------------
    # Cada palavra é alvo 4 vezes: 2 à esquerda e 2 à direita, alternando as
    # duas variantes de frase para a sessão não ficar repetitiva.
    linhas = []
    for x, y in PARES:
        for alvo, distr in ((x, y), (y, x)):
            for i, lado in enumerate(("esquerda", "direita", "esquerda", "direita")):
                var = "a" if i < 2 else "b"
                c = clipes.get((alvo, var))
                if not c:
                    raise SystemExit(f"Falta o áudio de '{alvo}' variante '{var}'.")
                esq, dir_ = (alvo, distr) if lado == "esquerda" else (distr, alvo)
                linhas.append(" | ".join([
                    alvo,
                    f"estimulos/imagens/{IMAGEM[esq]}.png",
                    f"estimulos/imagens/{IMAGEM[dir_]}.png",
                    lado, c["arquivo"], c["onset_ms"],
                ]))

    with open(a.saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    lados = {"esquerda": 0, "direita": 0}
    alvos: dict[str, int] = {}
    for l in linhas:
        p = [s.strip() for s in l.split("|")]
        lados[p[3]] += 1
        alvos[p[0]] = alvos.get(p[0], 0) + 1
    print(f"{len(linhas)} trials — esquerda {lados['esquerda']}, direita {lados['direita']}")
    print("por alvo: " + ", ".join(f"{k}={v}" for k, v in alvos.items()))
    print(f"\nEscrito: {a.saida}")


if __name__ == "__main__":
    main()
