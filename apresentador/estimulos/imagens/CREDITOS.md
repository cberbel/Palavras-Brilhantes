# Créditos das imagens de estímulo

Fotos obtidas via Openverse (api.openverse.org), sob licença livre.
Cada foto foi recortada, teve o fundo padronizado para branco e foi
reescalada para equalizar a área ocupada entre os pares.

- **gato** — "Project 366 #263: 190920 It Starts With A B", por comedy_nose. Licença cc0 1.0. Fonte: https://www.flickr.com/photos/23408922@N07/50361206711
- **bola** — "Closeup yoga ball white background", por autor não informado. Licença cc0 1.0. Fonte: https://www.rawpixel.com/image/6025360/photo-image-background-public-domain-yoga
- **cachorro** — "Mixed-Breed Dog", por autor não informado. Licença cc0 1.0. Fonte: https://www.rawpixel.com/image/5965473/mixed-breed-dog
- **sapato** — "Still Items", por Freestocks.org. Licença cc0 1.0. Fonte: https://stocksnap.io/photo/still-items-EC1PNPT1N1
- **banana** — "Banana - Isolated", por robin_24. Licença by 2.0. Fonte: https://www.flickr.com/photos/53507547@N06/5129712590
- **livro** — "Free old open book isolated", por autor não informado. Licença cc0 1.0. Fonte: https://www.rawpixel.com/image/5913492/image-background-book-public-domain
- **pato** — "Rubber Ducky", por visual.dichotomy. Licença by 2.0. Fonte: https://www.flickr.com/photos/12549623@N00/3624435520
- **maca** — "Free red apple white background", por autor não informado. Licença cc0 1.0. Fonte: https://www.rawpixel.com/image/5913734/image-background-public-domain-fruit

## Imagens geradas (05/09/2026)

As 26 fotos abaixo não são fotografias: foram **geradas por IA** (modelo Nano Banana 2,
da Google, via Higgsfield), em duas grades — uma 4096×4096 com 20 objetos e uma
2048×2048 com 6 — e tratadas pelo `preparar_gerados.py` (fundo branco, recorte por
componente conexo, área de tinta igualada dentro de cada par, 1024×1024). Não há
licença de terceiros a creditar; as grades originais ficam fora do repositório
(`Downloads\lwl_grid_20objetos.png` e `lwl_grid_6substitutos.png` no PC do Cláudio;
também na biblioteca Higgsfield, jobs `d93b421e…` e `017f885e…`).

carro, peixe, cavalo, pão, copo, bebê, menino, avião, ursinho, trem, boneca, colher,
flor, meia, vaca, chave, galinha, mesa, bolacha, cadeira, ovo, leão, chapéu, relógio,
sapo, bolo.

A flor teve a saturação reduzida a 75% para parear com a galinha. avião e colher são
objetos finos: o par inteiro (avião/bolo, colher/chave) foi igualado na área que o
objeto fino alcança, e não nos 20% dos outros pares.
