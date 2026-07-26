#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transforma as fotos escolhidas em estímulos comparáveis.

Foto crua não serve como estímulo: cada uma vem com enquadramento, tamanho de
objeto e fundo diferentes, e o paradigma exige que alvo e distrator tenham
saliência parecida — senão a criança olha para a mais chamativa em vez da
nomeada, e isso vira acurácia sem compreensão.

O tratamento é o mesmo aplicado às ilustrações: limpar o fundo para branco,
recortar no objeto e reescalar até que todas ocupem a mesma área de tinta.

Uso:
    python finalizar_fotos.py
    python finalizar_fotos.py --escolhas gato=3 bola=4 ...
"""
from __future__ import annotations
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(AQUI, "estimulos", "candidatas")
SAIDA = os.path.join(AQUI, "estimulos", "imagens")

# Escolhas feitas por inspeção visual do painel de candidatas. A pontuação
# automática mede fundo liso, não o que está na foto — ela chegou a eleger uma
# molécula 3D como "bola" e moscas-do-cavalo como "pato". A conferência humana
# não é opcional.
ESCOLHAS = {
    "gato": 3, "bola": 4, "cachorro": 5, "sapato": 1,
    "banana": 3, "livro": 1, "pato": 5, "maca": 2,
}

# Pareamento refeito depois de medir as fotos. O anterior juntava banana (muito
# saturada) com livro (sépia, apagado) — diferença de 0,41 em saturação, e a
# figura mais chamativa puxa o olhar independentemente da palavra. Este
# pareamento mantém todos os pares abaixo de 0,15 e preserva os contrastes que
# o protocolo exige: categorias semânticas diferentes e consoantes iniciais
# distintas em ponto e modo de articulação (g/b, b/s, k/l, p/m).
PARES = [("gato", "banana"), ("bola", "sapato"),
         ("cachorro", "livro"), ("pato", "maca")]

TAM = 512
ALVO_TINTA = 0.20
BRANCO = (255, 255, 255)
TOL_FUNDO = 60          # tolerância do preenchimento a partir das bordas


def limpa_fundo(img: Image.Image) -> Image.Image:
    """Preenche o fundo com branco a partir dos quatro cantos.

    Funciona porque foto de estúdio tem fundo conectado e quase uniforme. O
    preenchimento respeita a fronteira do objeto, então sombra suave some e o
    objeto fica intacto — ao contrário de um corte por limiar global, que come
    partes claras do próprio objeto.
    """
    img = img.convert("RGB")
    w, h = img.size
    for canto in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        try:
            ImageDraw.floodfill(img, canto, BRANCO, thresh=TOL_FUNDO)
        except Exception:
            pass

    # O preenchimento vem das bordas e não alcança o fundo que ficou preso
    # entre o objeto e a caixa de recorte. Sobra um retângulo cinza-claro
    # visível ao redor da figura. Encostar em branco puro tudo que já é
    # quase-branco resolve, e não toca o objeto: acima de 238 nos três canais
    # não há informação de forma, só fundo de estúdio.
    a = np.asarray(img).copy()
    a[np.all(a >= 238, axis=2)] = 255
    return Image.fromarray(a)


def mascara_tinta(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    return ~np.all(a > 244, axis=2)


def metricas(img: Image.Image) -> tuple[float, float]:
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    m = mascara_tinta(img)
    n = int(m.sum())
    if n == 0:
        return 0.0, 0.0
    mx, mn = a.max(axis=2)[m], a.min(axis=2)[m]
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0.0)
    return n / m.size, float(sat.mean())


def normaliza(img: Image.Image) -> Image.Image:
    m = mascara_tinta(img)
    if not m.any():
        return Image.new("RGB", (TAM, TAM), BRANCO)
    ys, xs = np.where(m)
    caixa = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    obj = img.crop(caixa)

    # escala para atingir a área de tinta alvo, com teto de extensão para que
    # um objeto alongado não seja esticado até as bordas só para bater a área
    frac = mascara_tinta(obj).sum() / (TAM * TAM)
    s = (ALVO_TINTA / frac) ** 0.5 if frac > 0 else 1.0
    larg, alt = obj.size
    s = min(s, TAM * 0.92 / max(larg, alt))
    obj = obj.resize((max(1, int(larg * s)), max(1, int(alt * s))), Image.LANCZOS)

    fundo = Image.new("RGB", (TAM, TAM), BRANCO)
    fundo.paste(obj, ((TAM - obj.width) // 2, (TAM - obj.height) // 2))
    return fundo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--escolhas", nargs="*", default=None, help="ex.: gato=3 bola=4")
    a = ap.parse_args()
    escolhas = dict(ESCOLHAS)
    for e in (a.escolhas or []):
        k, v = e.split("=")
        escolhas[k] = int(v)
    os.makedirs(SAIDA, exist_ok=True)

    creditos_cand = {}
    arq = os.path.join(CAND, "creditos.json")
    if os.path.exists(arq):
        with open(arq, encoding="utf-8") as f:
            creditos_cand = json.load(f)

    print(f"{'objeto':<10} {'tinta':>8} {'saturação':>10}")
    print("-" * 32)
    cobs, sats, usados = {}, {}, {}
    for nome, n in escolhas.items():
        origem = os.path.join(CAND, f"{nome}_{n}.jpg")
        if not os.path.exists(origem):
            print(f"{nome:<10} FALTA {origem}")
            continue
        img = normaliza(limpa_fundo(Image.open(origem)))
        img.save(os.path.join(SAIDA, f"{nome}.png"))
        cob, sat = metricas(img)
        cobs[nome], sats[nome] = cob, sat
        print(f"{nome:<10} {cob:>7.1%} {sat:>10.2f}")

        for c in creditos_cand.get(nome, []):
            if c.get("n") == n:
                usados[nome] = c
                break

    print("-" * 32)
    print("por par (é o que importa):")
    for x, y in PARES:
        if x not in cobs or y not in cobs:
            continue
        rz = max(cobs[x], cobs[y]) / min(cobs[x], cobs[y])
        ds = abs(sats[x] - sats[y])
        marca = "ok " if (rz <= 1.25 and ds <= 0.20) else "⚠  "
        print(f"  {marca} {x} × {y}: área {rz:.2f}x, saturação Δ{ds:.2f}")

    # créditos: obrigatório para CC BY, e boa prática mesmo para CC0
    linhas = ["# Créditos das imagens de estímulo", "",
              "Fotos obtidas via Openverse (api.openverse.org), sob licença livre.",
              "Cada foto foi recortada, teve o fundo padronizado para branco e foi",
              "reescalada para equalizar a área ocupada entre os pares.", ""]
    for nome in escolhas:
        c = usados.get(nome)
        if not c:
            linhas.append(f"- **{nome}** — crédito não registrado")
            continue
        linhas.append(
            f"- **{nome}** — \"{c.get('titulo') or 'sem título'}\", "
            f"por {c.get('autor') or 'autor não informado'}. "
            f"Licença {c.get('licenca')}. Fonte: {c.get('fonte')}")
    with open(os.path.join(SAIDA, "CREDITOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print(f"\n{len(cobs)} imagens em {SAIDA}")
    print(f"Créditos em {os.path.join(SAIDA, 'CREDITOS.md')}")


if __name__ == "__main__":
    main()
