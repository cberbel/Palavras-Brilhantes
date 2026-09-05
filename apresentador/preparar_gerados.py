#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recorta a grade de 20 fotos geradas e transforma cada uma em estímulo.

Em 05/09/2026 as 20 palavras novas (listas B, C e reserva do
montar_protocolo.py) foram geradas de uma vez só, numa única imagem 4096×4096
com grade de 5 colunas × 4 linhas (modelo Nano Banana 2, via Higgsfield).
Gerar 20 imagens separadas custaria 20× mais créditos; a grade custou 3.

Este script faz o mesmo tratamento do finalizar_fotos.py, só que a partir das
células da grade: limpa o fundo para branco, recorta no objeto e reescala até
todos ocuparem a mesma área de tinta. Saída em 1024×1024 (as fotos antigas são
512×512; em tela de alta densidade a diferença aparece, mas dentro de um par as
duas fotos vêm sempre da mesma geração, então o par continua equilibrado).

Uso:
    python preparar_gerados.py CAMINHO/lwl_grid_20objetos.png
"""
from __future__ import annotations
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "estimulos", "imagens")

# ordem das células na grade (linha a linha, da esquerda para a direita)
NOMES = ["carro", "peixe", "cavalo", "pao", "copo",
         "bebe", "menino", "aviao", "ursinho", "trem",
         "boneca", "colher", "flor", "meia", "vaca",
         "chave", "galinha", "mesa", "bolacha", "cadeira"]
COLS, LINHAS = 5, 4

# Segunda grade (2048×2048, 3×3), gerada depois para substituir o avião: o avião
# é fino demais (8% de tinta) e obrigava o bebê a encolher junto. O modelo
# devolveu 3×3 em vez de 3×2, com repetições; só as 6 primeiras células valem.
GRADE2 = {"cols": 3, "linhas": 3,
          "nomes": ["ovo", "leao", "chapeu", "relogio", "sapo", "bolo", None, None, None]}

# Pares como no montar_protocolo.py (mesmo gênero, categorias diferentes,
# consoante inicial diferente), já com a saturação medida para o pareamento.
PARES = [("copo", "peixe"), ("cavalo", "pao"), ("boneca", "cadeira"), ("vaca", "mesa"),
         ("carro", "menino"), ("bebe", "sapo"), ("flor", "galinha"), ("meia", "bolacha"),
         # reserva
         ("trem", "ursinho"), ("colher", "chave"), ("aviao", "bolo"),
         ("ovo", "relogio"), ("leao", "chapeu")]

# Ajuste de saturação por objeto. A flor vermelha saiu com saturação 0,92 —
# nada na grade chega perto; a galinha (par dela) tem 0,62. Reduzir a cor da
# flor em 25% deixa o par dentro do limite de 0,20 sem parecer artificial.
SATURACAO = {"flor": 0.75}

TAM = 1024
ALVO_TINTA = 0.20
BRANCO = (255, 255, 255)
TOL_FUNDO = 60


def limpa_fundo(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    for canto in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        try:
            ImageDraw.floodfill(img, canto, BRANCO, thresh=TOL_FUNDO)
        except Exception:
            pass
    a = np.asarray(img).copy()
    a[np.all(a >= 238, axis=2)] = 255
    return Image.fromarray(a)


def tira_linhas(img: Image.Image) -> Image.Image:
    """Apaga as linhas finas horizontais que o modelo desenha entre as células.

    Uma linha ocupa uma faixa de 1–4 linhas de pixels, atravessa quase toda a
    largura do recorte e é cinza. A faixa é reconstruída por interpolação das
    linhas vizinhas, então um objeto que ela cruza (haste da flor, ovo) não
    fica com um risco.
    """
    a = np.asarray(img.convert("RGB")).copy()
    h, w = a.shape[:2]
    tinta = ~np.all(a > 240, axis=2)
    cinza = (a.max(axis=2) - a.min(axis=2)) < 28
    # fração da largura coberta por pixel cinza-com-tinta: uma linha dá ~1,0;
    # um objeto cinza largo (colher) também, mas por muitas linhas seguidas
    frac = (tinta & cinza).sum(axis=1) / w
    y = 0
    while y < h:
        if frac[y] > 0.45:
            y0 = y
            while y < h and frac[y] > 0.45:
                y += 1
            if y - y0 <= 5:
                # reconstrói a faixa interpolando as linhas vizinhas (em vez de
                # pintar de branco, que deixaria um risco claro num objeto claro)
                ya, yb = max(0, y0 - 2), min(h - 1, y + 1)
                if ya < y0 and yb >= y:
                    for yy in range(ya + 1, yb):
                        t = (yy - ya) / (yb - ya)
                        a[yy] = ((1 - t) * a[ya].astype(np.float32) + t * a[yb].astype(np.float32)).astype(np.uint8)
        else:
            y += 1
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


def normaliza(img: Image.Image, alvo: float = ALVO_TINTA) -> Image.Image:
    m = mascara_tinta(img)
    if not m.any():
        return Image.new("RGB", (TAM, TAM), BRANCO)
    ys, xs = np.where(m)
    obj = img.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    frac = mascara_tinta(obj).sum() / (TAM * TAM)
    s = (alvo / frac) ** 0.5 if frac > 0 else 1.0
    larg, alt = obj.size
    s = min(s, TAM * 0.92 / max(larg, alt))
    obj = obj.resize((max(1, int(larg * s)), max(1, int(alt * s))), Image.LANCZOS)
    fundo = Image.new("RGB", (TAM, TAM), BRANCO)
    fundo.paste(obj, ((TAM - obj.width) // 2, (TAM - obj.height) // 2))
    return fundo


def acha_objetos(g: Image.Image, cw: int, ch: int, cols: int = COLS) -> dict[int, tuple[int, int, int, int]]:
    """Localiza cada objeto por componente conexo, não pelo retângulo da célula.

    O modelo não respeita a grade à risca: desenha linhas finas separando as
    células e deixa um objeto invadir a célula vizinha (a cabeça do menino
    entra na célula do peixe; a haste da flor desce até a da mesa). Recortar
    pelo retângulo fixo traz esses pedaços junto. Aqui a máscara de tinta é
    erodida 3 px (some com as linhas, que têm 1–2 px), os componentes que
    sobram são atribuídos à célula onde cai o seu centro, e a caixa do objeto
    é a união dos componentes relevantes daquela célula.
    """
    from scipy import ndimage
    a = np.asarray(g).astype(np.int16)
    tinta = ~np.all(a > 240, axis=2)
    ero = ndimage.binary_erosion(tinta, structure=np.ones((7, 7)))
    rot, n = ndimage.label(ero)
    objs = ndimage.find_objects(rot)
    areas = ndimage.sum(ero, rot, index=range(1, n + 1))
    por_celula: dict[int, list[tuple[float, tuple[int, int, int, int]]]] = {}
    for k, (sl, ar) in enumerate(zip(objs, areas), start=1):
        if sl is None or ar < 400:
            continue
        ys, xs = sl
        cy, cx = (ys.start + ys.stop) / 2, (xs.start + xs.stop) / 2
        cel = int(cy // ch) * cols + int(cx // cw)
        # caixa do componente na máscara original (sem erosão), com folga de 4 px
        por_celula.setdefault(cel, []).append((float(ar), (xs.start - 4, ys.start - 4, xs.stop + 4, ys.stop + 4)))
    caixas = {}
    for cel, lst in por_celula.items():
        maior = max(ar for ar, _ in lst)
        rel = [cx for ar, cx in lst if ar >= maior * 0.02]
        caixas[cel] = (min(c[0] for c in rel), min(c[1] for c in rel),
                       max(c[2] for c in rel), max(c[3] for c in rel))
    return caixas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("grade", help="PNG 4096×4096 com a grade 5×4 de objetos")
    ap.add_argument("--saida", default=SAIDA)
    ap.add_argument("--extra", default=None, help="segunda grade (substitutos), 3×3")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)

    limpos: dict[str, Image.Image] = {}
    grades = [(a.grade, COLS, LINHAS, NOMES)]
    if a.extra:
        grades.append((a.extra, GRADE2["cols"], GRADE2["linhas"], GRADE2["nomes"]))
    for caminho, cols, linhas, nomes in grades:
        g = Image.open(caminho).convert("RGB")
        W, H = g.size
        cw, ch = W // cols, H // linhas
        print(f"grade {os.path.basename(caminho)}: {W}×{H}, célula {cw}×{ch}")
        caixas = acha_objetos(g, cw, ch, cols)
        for i, nome in enumerate(nomes):
            if nome is None:
                continue
            if i not in caixas:
                raise SystemExit(f"não achei objeto na célula {i} ({nome})")
            x0, y0, x1, y1 = caixas[i]
            m = 12
            cel = g.crop((max(0, x0 - m), max(0, y0 - m), min(W, x1 + m), min(H, y1 + m)))
            img = limpa_fundo(tira_linhas(cel))
            if nome in SATURACAO:
                img = ImageEnhance.Color(img).enhance(SATURACAO[nome])
            limpos[nome] = img
    todos = list(limpos)
    print(f"\n{'objeto':<10} {'tinta':>8} {'saturação':>10}")
    print("-" * 32)

    # Objeto fino (colher, avião) não chega aos 20% de tinta sem estourar o
    # teto de extensão. Nesse caso o PAR inteiro desce para a área que o
    # objeto fino alcança: o que importa é alvo e distrator iguais entre si,
    # não iguais aos outros pares.
    alvo_de = {n: ALVO_TINTA for n in todos}
    for x, y in PARES:
        if x not in limpos or y not in limpos:
            continue
        ax = metricas(normaliza(limpos[x]))[0]
        ay = metricas(normaliza(limpos[y]))[0]
        alvo_de[x] = alvo_de[y] = min(ax, ay, ALVO_TINTA)

    cobs, sats = {}, {}
    for nome in todos:
        img = normaliza(limpos[nome], alvo_de[nome])
        img.save(os.path.join(a.saida, f"{nome}.png"), optimize=True)
        cobs[nome], sats[nome] = metricas(img)
        print(f"{nome:<10} {cobs[nome]:>7.1%} {sats[nome]:>10.2f}")

    print("-" * 32)
    print("por par (é o que importa):")
    for x, y in PARES:
        if x not in cobs or y not in cobs:
            continue
        rz = max(cobs[x], cobs[y]) / max(min(cobs[x], cobs[y]), 1e-6)
        ds = abs(sats[x] - sats[y])
        marca = "ok " if (rz <= 1.25 and ds <= 0.20) else "⚠  "
        print(f"  {marca} {x} × {y}: área {rz:.2f}x, saturação Δ{ds:.2f}")

    with open(os.path.join(a.saida, "metricas_gerados.json"), "w", encoding="utf-8") as f:
        json.dump({n: {"tinta": cobs[n], "saturacao": sats[n]} for n in todos}, f, indent=1)
    print(f"\n{len(todos)} imagens em {a.saida}")


if __name__ == "__main__":
    main()
