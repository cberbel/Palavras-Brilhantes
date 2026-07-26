#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera as 8 imagens de estímulo do protocolo.

Por que desenhar em vez de usar fotos: o paradigma exige que alvo e distrator
tenham saliência visual parecida. Fotos de banco variam em fundo, enquadramento,
contraste e riqueza de detalhe, e a criança pode olhar para a mais chamativa em
vez da nomeada — o que vira acurácia sem compreensão. Ilustrações planas geradas
pelo mesmo código compartilham fundo, área ocupada, espessura de traço e
saturação, então a diferença entre as duas figuras de um par é só a identidade
do objeto.

No fim o script imprime a cobertura de tinta e a saturação média de cada imagem.
Elas devem ficar próximas entre si; se uma destoar muito, ajuste antes de usar.

Uso:
    python gerar_estimulos.py [--saida estimulos/imagens] [--tamanho 512]
"""
from __future__ import annotations
import argparse, math, os
import numpy as np
from PIL import Image, ImageDraw

SS = 4                      # supersampling: o PIL não suaviza bordas de polígono
TRACO = 7                   # espessura do contorno, em px da imagem final
PRETO = (40, 40, 45)
BRANCO = (255, 255, 255)


def nova(tam: int):
    img = Image.new("RGB", (tam * SS, tam * SS), BRANCO)
    return img, ImageDraw.Draw(img)


def E(*vals):
    """Escala coordenadas para o espaço supersampleado."""
    return [v * SS for v in vals]


def elipse(d, cx, cy, rx, ry, cor, contorno=True):
    d.ellipse(E(cx - rx, cy - ry, cx + rx, cy + ry), fill=cor,
              outline=PRETO if contorno else None, width=TRACO * SS if contorno else 0)


def poli(d, pts, cor, contorno=True):
    d.polygon([c * SS for p in pts for c in p], fill=cor,
              outline=PRETO if contorno else None, width=TRACO * SS if contorno else 0)


def linha(d, pts, cor=PRETO, w=TRACO):
    d.line([c * SS for p in pts for c in p], fill=cor, width=w * SS, joint="curve")


# --------------------------------------------------------------------------
# Cada função desenha num sistema de coordenadas de 512×512 e recebe o Draw.
# Paleta com saturação parecida, matizes bem separados.
# --------------------------------------------------------------------------
VERMELHO = (222, 74, 62)
AMARELO  = (240, 190, 60)
AZUL     = (52, 118, 205)
PNEU     = (38, 62, 104)
LARANJA  = (232, 138, 58)
MARROM   = (176, 122, 78)
VERDE    = (104, 168, 92)
CINZA    = (150, 156, 165)
CREME    = (232, 190, 132)   # focinho/pelo do cachorro — bege saturado, não creme
VIDRO    = (150, 196, 232)   # janelas do carro


def bola(d):
    elipse(d, 256, 262, 150, 150, VERMELHO)
    # duas faixas curvas, para não ser só um círculo liso
    for dy in (-52, 52):
        pts = [(256 + 145 * math.cos(t), 262 + dy * 1.0 + 120 * math.sin(t) * 0.28)
               for t in [math.pi * i / 40 for i in range(41)]]
        linha(d, pts, BRANCO, 9)
    elipse(d, 256, 262, 150, 150, None, contorno=True)


def maca(d):
    elipse(d, 256, 290, 132, 138, VERMELHO)
    # entalhe do topo
    d.pieslice(E(180, 140, 332, 250), 200, 340, fill=BRANCO)
    elipse(d, 210, 208, 62, 52, VERMELHO, contorno=False)
    elipse(d, 302, 208, 62, 52, VERMELHO, contorno=False)
    linha(d, [(256, 190), (268, 130)], MARROM, 12)          # cabinho
    poli(d, [(268, 148), (330, 118), (300, 168)], VERDE)     # folha


def banana(d):
    # Crescente de verdade: área entre dois arcos concêntricos. A primeira versão
    # era uma linha quebrada e não lia como banana nenhuma.
    cx, cy, R, r, giro = 256, 110, 198, 124, -18
    def arco(raio, a0, a1, n=48):
        pts = []
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            x, y = raio * math.cos(a), raio * math.sin(a)
            g = math.radians(giro)
            pts.append((cx + x * math.cos(g) - y * math.sin(g),
                        cy + x * math.sin(g) + y * math.cos(g)))
        return pts
    # arco interno com sweep menor: as pontas afinam em vez de terminarem em
    # corte reto, que fazia a figura ler como tigela e não como banana
    poli(d, arco(R, 16, 164) + arco(r, 152, 28), AMARELO)
    p = arco(R, 164, 164, 1)[0]
    linha(d, [p, (p[0] - 10, p[1] - 32)], MARROM, 13)


def carro(d):
    poli(d, [(96, 300), (140, 300), (170, 222), (330, 222), (372, 300), (416, 300),
             (416, 344), (96, 344)], AZUL)
    poli(d, [(182, 296), (204, 240), (248, 240), (248, 296)], VIDRO)   # janelas
    poli(d, [(262, 296), (262, 240), (306, 240), (330, 296)], VIDRO)
    # Rodas menores e em azul-escuro em vez de preto puro: duas áreas grandes de
    # preto derrubavam a saturação média do carro bem abaixo da do par (banana).
    for cx in (168, 348):
        elipse(d, cx, 346, 36, 36, PNEU)
        elipse(d, cx, 346, 14, 14, VIDRO, contorno=False)


def sapato(d):
    poli(d, [(110, 340), (118, 262), (168, 236), (232, 240), (300, 288),
             (386, 306), (406, 330), (400, 356), (114, 356)], AZUL)
    linha(d, [(150, 250), (176, 300)], BRANCO, 8)
    linha(d, [(196, 244), (222, 296)], BRANCO, 8)
    d.rectangle(E(110, 336, 406, 358), fill=BRANCO, outline=PRETO, width=TRACO * SS)


def gato(d):
    poli(d, [(150, 196), (166, 104), (238, 156)], LARANJA)     # orelhas
    poli(d, [(362, 196), (346, 104), (274, 156)], LARANJA)
    elipse(d, 256, 262, 138, 124, LARANJA)
    elipse(d, 212, 244, 17, 22, PRETO, contorno=False)         # olhos
    elipse(d, 300, 244, 17, 22, PRETO, contorno=False)
    poli(d, [(240, 288), (272, 288), (256, 306)], VERMELHO)    # focinho
    linha(d, [(256, 306), (256, 318)])
    linha(d, [(256, 318), (228, 330)]); linha(d, [(256, 318), (284, 330)])
    for y, dy in ((286, -14), (300, 0), (314, 14)):            # bigodes
        linha(d, [(214, y), (128, y + dy)], PRETO, 5)
        linha(d, [(298, y), (384, y + dy)], PRETO, 5)


def cachorro(d):
    elipse(d, 148, 250, 46, 92, MARROM)                        # orelhas caídas
    elipse(d, 364, 250, 46, 92, MARROM)
    elipse(d, 256, 250, 130, 118, CREME)
    elipse(d, 214, 234, 16, 20, PRETO, contorno=False)
    elipse(d, 298, 234, 16, 20, PRETO, contorno=False)
    elipse(d, 256, 306, 62, 48, MARROM)                        # focinho
    elipse(d, 256, 292, 22, 16, PRETO, contorno=False)         # nariz
    linha(d, [(256, 306), (256, 326)])
    linha(d, [(256, 326), (230, 338)]); linha(d, [(256, 326), (282, 338)])


def pato(d):
    elipse(d, 268, 306, 128, 92, AMARELO)                      # corpo
    poli(d, [(330, 250), (392, 196), (386, 268)], AMARELO)     # cauda
    elipse(d, 178, 214, 68, 68, AMARELO)                       # cabeça
    poli(d, [(126, 208), (58, 224), (126, 244)], LARANJA)      # bico
    elipse(d, 168, 198, 11, 13, PRETO, contorno=False)
    linha(d, [(228, 296), (300, 296)], PRETO, 5)               # asa
    linha(d, [(232, 316), (296, 316)], PRETO, 5)


OBJETOS = {
    "bola": bola, "maca": maca, "banana": banana, "carro": carro,
    "sapato": sapato, "gato": gato, "cachorro": cachorro, "pato": pato,
}

# Pares que aparecem juntos na tela. Precisam bater em área e saturação.
PARES = [("gato", "bola"), ("cachorro", "sapato"),
         ("banana", "carro"), ("pato", "maca")]


def mascara_tinta(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    return ~np.all(a > 246, axis=2)


def metricas(img: Image.Image) -> tuple[float, float]:
    """(fração de pixels não-brancos, saturação média desses pixels)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    m = mascara_tinta(img)
    n = int(m.sum())
    if n == 0:
        return 0.0, 0.0
    mx = a.max(axis=2)[m]
    mn = a.min(axis=2)[m]
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0.0)
    return n / m.size, float(sat.mean())


def normaliza(img: Image.Image, alvo_tinta: float, extensao_max: float) -> Image.Image:
    """Reescala o objeto para ocupar a mesma área de tinta que os demais.

    Equalizar a área na mão, mexendo em coordenadas, é lento e sempre fica
    aproximado. Como as figuras são planas sobre branco, dá para medir a tinta
    depois de desenhar e reescalar: multiplicar o objeto por `s` multiplica a
    área por `s²`. O limite de extensão evita que uma figura fina — a banana —
    seja esticada até encostar nas bordas só para bater a área.
    """
    m = mascara_tinta(img)
    if not m.any():
        return img
    ys, xs = np.where(m)
    caixa = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    larg, alt = caixa[2] - caixa[0], caixa[3] - caixa[1]

    s = math.sqrt(alvo_tinta / (m.sum() / m.size))
    s = min(s, extensao_max / max(larg, alt))

    recorte = img.crop(caixa).resize((max(1, int(larg * s)), max(1, int(alt * s))),
                                     Image.LANCZOS)
    fundo = Image.new("RGB", img.size, BRANCO)
    fundo.paste(recorte, ((img.width - recorte.width) // 2,
                          (img.height - recorte.height) // 2))
    return fundo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "estimulos", "imagens"))
    ap.add_argument("--tamanho", type=int, default=512)
    ap.add_argument("--tinta", type=float, default=0.20,
                    help="fração da tela ocupada por tinta, alvo para todas")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    extensao_max = a.tamanho * 0.92

    print(f"{'objeto':<10} {'tinta':>8} {'saturação':>10}")
    print("-" * 30)
    cobs, sats = {}, {}
    for nome, fn in OBJETOS.items():
        img, d = nova(a.tamanho)
        fn(d)
        img = normaliza(img, a.tinta, extensao_max * SS)
        img = img.resize((a.tamanho, a.tamanho), Image.LANCZOS)
        img.save(os.path.join(a.saida, f"{nome}.png"))
        cob, sat = metricas(img)
        cobs[nome], sats[nome] = cob, sat
        print(f"{nome:<10} {cob:>7.1%} {sat:>10.2f}")

    # O que enviesa o olhar é a diferença DENTRO do par que aparece junto na
    # tela, não a variação no conjunto todo.
    print("-" * 30)
    print("por par (é o que importa):")
    pior = 0.0
    for x, y in PARES:
        rz = max(cobs[x], cobs[y]) / min(cobs[x], cobs[y])
        ds = abs(sats[x] - sats[y])
        pior = max(pior, rz)
        marca = "ok " if (rz <= 1.25 and ds <= 0.20) else "⚠  "
        print(f"  {marca} {x} × {y}: área {rz:.2f}x, saturação Δ{ds:.2f}")

    if pior > 1.25:
        print("\n⚠ Algum par está desigual em área. Pares desiguais enviesam o "
              "olhar para a figura mais chamativa — ajuste antes de coletar.")
    print(f"\n{len(OBJETOS)} imagens em {a.saida}")


if __name__ == "__main__":
    main()
