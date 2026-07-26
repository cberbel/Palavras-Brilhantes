#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca fotos reais dos objetos do protocolo, sob licença livre, e escolhe as que
servem como estímulo.

Fonte: Openverse (api.openverse.org), restrito a CC0 e domínio público. Fotos
com licença mais restritiva ficam de fora de propósito: o material vai ser usado
com crianças e possivelmente mostrado a famílias, e "achei na internet" não é
base legal.

O trabalho real aqui não é baixar, é filtrar. Foto de estímulo precisa de fundo
liso e objeto centralizado; uma foto de gato no sofá, com padrões e outros
objetos, faz a criança olhar pela razão errada. Por isso cada candidata recebe
uma nota automática de uniformidade de borda e de contraste do objeto, e só as
melhores vão para o painel de revisão humana.

Uso:
    python baixar_fotos.py            # busca e monta o painel de candidatas
    python baixar_fotos.py --escolher gato=3 bola=1 ...   # fixa as escolhidas
"""
from __future__ import annotations
import argparse, io, json, os, time, urllib.parse, urllib.request
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(AQUI, "estimulos", "candidatas")
UA = "LWL-estimulos/1.0 (projeto de pesquisa escolar)"

# nome do arquivo -> termos de busca, em inglês porque o acervo é majoritariamente
# anglófono e a busca é por metadado textual
# A busca casa metadado textual, não conteúdo. Termos genéricos trouxeram uma
# molécula 3D como "bola" e moscas-do-cavalo como "duck" — os nomes científicos
# tinham as palavras certas na legenda. Termos específicos e concretos filtram
# melhor; a conferência visual continua obrigatória.
BUSCAS = {
    "gato":     ["cat white background", "kitten isolated white background",
                 "cat portrait plain background", "tabby cat studio"],
    "bola":     ["ball white background", "soccer ball isolated", "toy ball white background"],
    "cachorro": ["dog white background", "puppy isolated white", "dog studio white",
                 "golden retriever white background", "beagle isolated white background",
                 "dog sitting white background studio"],
    "sapato":   ["shoe white background", "sneaker isolated white", "shoes studio white"],
    "banana":   ["banana white background", "banana isolated white"],
    # "carro" foi descartado: o acervo livre não tem foto de um carro único em
    # fundo limpo — só grupos, modelos de LEGO e ilustrações. "livro" é
    # igualmente familiar nessa idade e fotografa bem.
    "livro":    ["book white background", "open book isolated white",
                 "closed book studio white background", "hardcover book isolated"],
    "pato":     ["rubber duck bath toy", "yellow rubber duck white background",
                 "duckling isolated white background", "mallard duck plain background"],
    "maca":     ["apple white background", "red apple isolated white"],
}


# Nenhuma configuração isolada serve para os 8 objetos. Exigir category=photograph
# limpa o clipart de "pato de borracha" mas zera "bola", porque muita foto boa não
# está classificada nessa categoria. Restringir a CC0 dá um acervo pequeno; abrir
# para CC BY amplia mas entra mais foto de cena. A saída é rodar as combinações e
# juntar tudo num único conjunto de candidatas, deixando a escolha para o olho.
CONFIGS = [
    {"license": "cc0,pdm", "category": ""},
    {"license": "cc0,pdm,by,by-sa", "category": "&category=photograph"},
    {"license": "cc0,pdm,by,by-sa", "category": ""},
]


def busca(q: str, cfg: dict, n: int = 12) -> list[dict]:
    url = ("https://api.openverse.org/v1/images/?format=json" + cfg["category"] +
           f"&page_size={n}&license={cfg['license']}&q=" + urllib.parse.quote(q))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r).get("results", [])
    except Exception as e:
        print(f"    busca falhou ({q}): {type(e).__name__}")
        return []


def baixa(url: str) -> Image.Image | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            img = Image.open(io.BytesIO(r.read()))
            return img.convert("RGB")
    except Exception:
        return None


def nota_fundo(img: Image.Image) -> tuple[float, float]:
    """(uniformidade da borda 0-1, contraste do objeto 0-1).

    Uma foto de estúdio tem borda quase constante. Uma foto de cena tem borda
    variada. A segunda nota evita premiar imagens que são lisas por serem quase
    vazias: exige que exista algo bem diferente do fundo no meio do quadro.
    """
    a = np.asarray(img.resize((160, 160), Image.LANCZOS)).astype(np.float32)
    borda = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3),
                            a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    cor = borda.mean(axis=0)
    desvio = float(np.linalg.norm(borda - cor, axis=1).mean())
    uniformidade = max(0.0, 1.0 - desvio / 60.0)

    centro = a[40:120, 40:120].reshape(-1, 3)
    dif = float(np.linalg.norm(centro - cor, axis=1).mean())
    contraste = min(1.0, dif / 90.0)
    return uniformidade, contraste


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-objeto", type=int, default=4, help="candidatas mantidas")
    ap.add_argument("--somente", nargs="*", default=None,
                    help="refaz a busca só destes objetos")
    a = ap.parse_args()
    os.makedirs(CAND, exist_ok=True)

    arq_cred = os.path.join(CAND, "creditos.json")
    creditos = {}
    if os.path.exists(arq_cred):
        with open(arq_cred, encoding="utf-8") as f:
            creditos = json.load(f)

    alvos = {k: v for k, v in BUSCAS.items() if not a.somente or k in a.somente}
    for nome, termos in alvos.items():
        print(f"{nome}:")
        vistos, pontuadas = set(), []
        for cfg in CONFIGS:
            for q in termos:
                for r in busca(q, cfg):
                    u = r.get("url")
                    if not u or u in vistos:
                        continue
                    vistos.add(u)
                    img = baixa(u)
                    if img is None or min(img.size) < 300:
                        continue
                    uni, con = nota_fundo(img)
                    pontuadas.append((uni * 0.7 + con * 0.3, uni, con, img, r))
                    time.sleep(0.15)
        pontuadas.sort(key=lambda t: -t[0])
        melhores = pontuadas[: a.por_objeto]
        print(f"  {len(vistos)} baixadas, {len(melhores)} mantidas")

        creditos[nome] = []
        for i, (nota, uni, con, img, r) in enumerate(melhores, 1):
            img.save(os.path.join(CAND, f"{nome}_{i}.jpg"), quality=92)
            creditos[nome].append({
                "n": i, "nota": round(nota, 3), "uniformidade": round(uni, 3),
                "contraste": round(con, 3), "titulo": r.get("title"),
                "autor": r.get("creator"), "licenca": f"{r.get('license')} {r.get('license_version')}",
                "fonte": r.get("foreign_landing_url"), "arquivo_original": r.get("url"),
            })
            print(f"    {i}. nota {nota:.2f} (fundo {uni:.2f}, objeto {con:.2f}) "
                  f"— {(r.get('title') or '')[:44]}")

    with open(arq_cred, "w", encoding="utf-8") as f:
        json.dump(creditos, f, ensure_ascii=False, indent=1)
    print(f"\nCandidatas e créditos em {CAND}")


if __name__ == "__main__":
    main()
