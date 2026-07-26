# Plano da sessão Cowork "Fernald language processing efficiency tool"

Texto recuperado em 25/07/2026 da sessão Cowork do claude.ai
(`claude.ai/cowork/cse_0167zpf1Gm9BGTaztQcF9GaA`), onde já foi produzida uma primeira
versão funcional da ferramenta (`lwl-fernald.zip`).

Guardado aqui como referência. O plano de trabalho vigente é o [PLANO.md](PLANO.md);
este arquivo existe para não perder o que já tinha sido decidido lá.

---

## O que já existe no `lwl-fernald.zip`

```
lwl-fernald/
├── PLANO.md
├── experimento/
│   ├── index.html      ← app: apresentação + gravação + timing (roda sem instalar nada)
│   └── estimulos/
│       ├── imagens/    ← PNGs dos objetos
│       └── audio/      ← (opcional) áudios se não usar TTS
└── analise/
    └── analisar.py     ← calcula RT e acurácia (janela 300–1800 ms, piso 300 ms)
```

O `index.html` mostra fixação central → duas imagens → frase (TTS pt-BR ou áudios
próprios), grava a webcam, registra o tempo da palavra-alvo dentro do vídeo, coloca um
marcador de sincronismo (flash branco + beep) no início e, ao fim, baixa o `.webm` e o
`eventos.csv`. Vem com 8 trials de exemplo usando emojis.

O `analisar.py` cruza o `eventos.csv` com a codificação do olhar (OWLET, iCatcher+ ou
manual) e calcula RT e acurácia com a janela 300–1800 ms e o piso de 300 ms. Foi
validado com dados sintéticos (RT de 617 ms no trial iniciado no distrator).

Para rodar:

```bash
cd experimento && python3 -m http.server 8000
```

Depois abrir `http://localhost:8000` no Chrome — a webcam não funciona via `file://`.

---

## Parâmetros do paradigma registrados lá

Fonte canônica: Fernald, Zangl, Portillo & Marchman (2008), *Looking while listening*.

- Janela de análise: **300 a 1800 ms** após o início da palavra-alvo.
- Piso de 300 ms: shifts mais rápidos são descartados — não dá tempo de planejar e
  executar uma sacada em resposta à palavra.
- Codificação a **30 fps** = 1 frame a cada ~33 ms, rotulado esquerda / direita / fora.
- Pré-exposição: imagens aparecem ~1–2 s antes do áudio, em silêncio.
- Frases-portadoras curtas de fala dirigida à criança, com a palavra no fim:
  *"Cadê o ___?"*, *"Olha o ___!"*, *"Acha o ___"*.
- **24–32 trials**, com o lado do alvo contrabalançado.
- **Confiabilidade:** um segundo codificador recodifica ~20–25% dos vídeos;
  concordância esperada **> 95%**.

Nota registrada lá: os tempos exatos (duração do trial ~5–6 s, pré-exposição 1–2 s,
nº de trials) variam entre estudos. A janela 300–1800 ms e a codificação a 33 ms são o
que não se deve mexer se você quer comparabilidade com a literatura.

---

## Decisão de arquitetura (idêntica à do PLANO.md)

Dois caminhos para medir o olhar:

1. **Rastrear ao vivo no navegador (WebGazer.js)** — exige calibração por cliques do
   usuário; bebê não faz isso. Pouco confiável para crianças pequenas.
2. **Gravar o rosto e codificar depois (offline)** — o que os laboratórios fazem.
   Funciona com webcam e com celular, e não depende de calibrar um bebê.

A ferramenta usa o caminho 2.

---

## Os quatro níveis de setup propostos

- **Nível 0** — protótipo rodando em 5 minutos, com emojis e voz do navegador.
- **Nível 1** — casa simples: webcam acima da tela, criança a 50–60 cm no colo do
  cuidador, boa luz sem contraluz → OWLET → `analisar.py`.
- **Nível 2** — celular: estímulos no tablet/computador com gravação de webcam
  desligada; celular acima/atrás da tela filmando o rosto a 30 fps; sincronização pelo
  flash branco + beep do início.
- **Nível 3** — escola/avançado: Lookit / Children Helping Science para coleta
  padronizada em escala; iCatcher+ no lugar do OWLET para volume; eye-tracker dedicado
  (Tobii + PsychoPy) se houver orçamento.

---

## Verificação de qualidade proposta

- Conferir que existe uma linha `alvo_onset` por trial no `eventos.csv`.
- Conferir que a base de tempo da codificação do olhar bate com a do vídeo
  (usar o marcador de sync).
- Acurácia deve ficar acima de 0,5 se a criança reconhece as palavras;
  RTs típicos vão de algumas centenas até ~1000 ms.
- Descartar trials com poucas amostras de olhar na janela (`n_amostras`).

---

## Referências que estavam lá e não estavam no meu levantamento

- **Peekbank** (Stanford) — banco de dados aberto de estudos looking-while-listening.
  Serve para calibrar desenho e métricas contra a literatura e para alinhar o esquema de
  dados. https://peekbank.github.io/peekbank-website/
- **Children Helping Science** — o nome atual/público da plataforma Lookit.
  https://childrenhelpingscience.com · https://lookit.mit.edu
- Fernald, Perfors & Marchman (2006), *Picking up speed in understanding*,
  Developmental Psychology 42(1).
- Marchman & Fernald (2008), Developmental Science 11(3), F9–F16.
