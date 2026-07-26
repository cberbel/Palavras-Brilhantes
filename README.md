# Teste de Eficiência de Processamento Linguístico (Looking-While-Listening)

Ferramenta baseada no paradigma da Anne Fernald (Stanford). Duas figuras lado a lado,
uma frase que nomeia uma delas, e a medida de quão rápido e quão consistentemente os
olhos da criança vão para a figura certa.

**No ar:** https://palavras-brilhantes.vercel.app — apresentador, câmera para celular e
codificador. Nenhum dado sai do aparelho; a análise continua sendo local.

**Para gravar e testar agora:** [COMO-TESTAR.md](COMO-TESTAR.md) — passo a passo de
20 minutos, com os três atalhos `.cmd` da raiz do projeto. Pelo site, pule direto para
o passo 1 abrindo o endereço acima em vez de rodar o servidor local.

**Antes de usar com crianças, leia o [PLANO.md](PLANO.md).** Ele explica o que o teste
mede, o que ele não é, e o que fazer para que a medida seja válida.

---

## Estado atual

| Peça | Situação |
|---|---|
| `apresentador/index.html` | pronto — 32 trials, áudio agendado, bipe por trial |
| `apresentador/estimulos/imagens/` | pronto — 8 **fotos reais**, pares equilibrados em área e cor |
| `apresentador/estimulos/audio/` | pronto — 16 clipes com onset verificado |
| `analisador/sincronizar.py` | pronto — bipes localizados com 5–10 ms de erro |
| `analisador/analisar.py` | pronto — TR, acurácia, baseline, exclusões |
| `codificador/index.html` | pronto — codificação manual e concordância (kappa) |
| Codificador automático | **falta instalar** o OWLET ou o iCatcher+ |
| Teste de espelhamento | **falta fazer** — precisa de uma gravação sua (5 min) |
| Voz humana nos áudios | recomendado — a voz sintética tem tempo exato, prosódia não |

Três suítes de teste passando: análise, detecção de bipe e pipeline completo.

---

## Instalação

Python 3.11+.

```bash
pip install numpy pillow imageio-ffmpeg
```

O `imageio-ffmpeg` traz o ffmpeg embutido, então não é preciso instalá-lo no sistema.
Se você já tiver ffmpeg no PATH, ele é usado preferencialmente.

---

## Preparar os estímulos (só uma vez)

As imagens e os áudios **já estão gerados**. Refaça só se quiser mudar as palavras.

### Imagens

Os estímulos são **fotos reais** de objetos, sob licença livre (CC0 e CC BY), obtidas
via Openverse. A procedência de cada uma está em
[estimulos/imagens/CREDITOS.md](apresentador/estimulos/imagens/CREDITOS.md) — as CC BY
exigem que o crédito acompanhe o material se ele for divulgado.

```bash
python apresentador/baixar_fotos.py
```

Busca candidatas e pontua cada uma por uniformidade de fundo. **A pontuação mede fundo
liso, não o que está na foto** — ela chegou a eleger uma molécula 3D como "bola" e
moscas-do-cavalo como "pato". Olhe o painel de candidatas antes de escolher.

```bash
python apresentador/finalizar_fotos.py
```

Limpa o fundo para branco, recorta no objeto e reescala tudo para a mesma área ocupada.
Imprime a comparação por par: área dentro de 1,25x e saturação dentro de 0,20.

As oito palavras são **gato, banana, bola, sapato, cachorro, livro, pato, maçã**.
"Carro" foi descartado por falta de foto livre de um carro único em fundo limpo — só
existem grupos, modelos de LEGO e ilustrações. "Livro" ocupa o lugar dele.

A versão em ilustração continua disponível, caso você prefira desenho a foto:

```bash
python apresentador/gerar_estimulos.py
```

```bash
powershell -ExecutionPolicy Bypass -File apresentador/gerar_audio.ps1
```

Sintetiza as 16 frases com a voz pt-BR do Windows e registra o instante exato de cada
palavra dentro do arquivo.

```bash
python apresentador/montar_protocolo.py
```

Confere os onsets contra o áudio, corrige o que não bater e escreve o `protocolo.txt`
com os 32 trials.

**Ouça os 16 clipes uma vez.** A verificação automática é de tempo, não de pronúncia.

---

## Rodar uma sessão

### 1. Apresentar e gravar

A webcam não funciona com o arquivo aberto direto (`file://`). Sirva por HTTP:

```bash
python -m http.server 8000 --directory apresentador
```

Abra `http://localhost:8000` no Chrome. O `protocolo.txt` é carregado sozinho e o modo
TTS é desmarcado. Confira a prévia da câmera, preencha o ID e inicie. Ao final, baixe o
`.webm` e o `_eventos.csv`.

### 2. Sincronizar

```bash
python analisador/sincronizar.py SESSAO.webm SESSAO_eventos.csv --saida sincronizacao.json
```

O número de bipes tem que bater com o de trials e a margem ficar acima de 1,5x. Se não
bater, nada adiante vale.

### 3. Codificar o olhar

Rode o [OWLET](https://github.com/denisemw/OWLET) (casa, webcam ou celular) ou o
[iCatcher+](https://github.com/icatcherplus/icatcher_plus) (escola, volume) sobre o
vídeo. Padronize a saída num CSV com colunas `t_ms` e `olhar`
(`left` / `right` / `away`), na mesma base de tempo do vídeo.

### 4. Calcular

```bash
python analisador/analisar.py sincronizacao.json olhar.csv --saida resultados
```

Saem `resultados/por_trial.csv` e `resultados/resumo.json`.

---

## O teste de espelhamento — faça antes de gravar qualquer criança

É o erro mais provável de todo o projeto, e ele produz acurácia perto de zero em vez de
perto de cem. Se acontecer sem você perceber, você joga fora dados de crianças reais.

1. Sirva o apresentador e rode uma sessão curta com você mesmo na frente da câmera.
2. Olhe **deliberadamente** para a figura da esquerda em alguns trials e para a da
   direita em outros. Anote no papel o que fez.
3. Abra `codificador/index.html`, carregue o vídeo e codifique esses trials à mão.
4. Rode o codificador automático sobre o mesmo vídeo.
5. Na seção 3 do codificador, compare os dois CSVs.

Concordância alta e na direção certa: pode seguir. Concordância perto de zero com a
matriz de confusão trocando esquerda por direita: o espelhamento está invertido, e é só
inverter o mapeamento na conversão da saída do codificador automático.

---

## Codificação manual e validação

`codificador/index.html` roda em qualquer navegador, sem servidor. Carregue o vídeo,
informe o fps e marque com <kbd>A</kbd> esquerda, <kbd>D</kbd> direita, <kbd>X</kbd>
fora, <kbd>?</kbd> incerto. Cada marca vale do quadro atual até a próxima — você só
marca quando o olhar muda.

Codifique 20–25% dos trials à mão e compare com o automático. O padrão da literatura
para dois codificadores humanos é concordância acima de 95%.

---

## Testes

```bash
python analisador/teste_pipeline.py
```

Monta um `.webm` com bipes em posições conhecidas, roda sincronização e análise em
sequência e verifica se o tempo de reação plantado volta no fim. É o teste que prova que
as peças encaixam. Os outros dois — `teste_sintetico.py` e `teste_sync.py` — cobrem as
regras de protocolo e a detecção de bipe isoladamente.

Rode os três depois de qualquer mudança nos parâmetros.

---

## O ponto que mais importa: o áudio

O tempo de reação é medido a partir do **início exato da palavra-alvo**, não do início da
frase. Por isso:

- **Não use o modo TTS do navegador para medir.** A fala sintetizada ao vivo não informa
  com precisão quando a palavra começa. O apresentador marca essas sessões como
  `rt_valido=nao` e o analisador se recusa a calcular TR a partir delas.
- Os clipes em `estimulos/audio/` **não** têm esse problema: são arquivos, e a API de
  síntese informou a posição exata de cada palavra, conferida depois contra o sinal.
  O tempo é válido. O que fica devendo é a prosódia — voz sintética não tem o contorno
  melódico da fala dirigida à criança.
- **Para coleta de dados de verdade, grave uma voz humana.** Uma frase por arquivo, voz
  feminina falante nativa, registro de fala dirigida à criança. Marque o início do
  primeiro fonema da palavra-alvo no Audacity e ponha o número na coluna `onset_ms`
  do `protocolo.txt`.

Como o bipe e a frase são agendados no mesmo relógio do `AudioContext`, o intervalo
entre eles é exato. Achando o bipe no vídeo, o instante da palavra é:

```
t_palavra = t_bipe_no_video + gap_bipe_frase_ms + onset_ms
```

Nada disso depende de quando o gravador começou nem de deriva de relógio — e funciona
igual se quem grava for a webcam ou um celular ao lado.

---

## Pastas

```
teste-lwl/
├── PLANO.md                  protocolo, setups, riscos, referências
├── PLANO-cowork-original.md  o plano da primeira versão, guardado como referência
├── apresentador/
│   ├── index.html            apresentação + gravação + bipe de sincronização
│   ├── protocolo.txt         32 trials gerados (imagens, áudios, onsets)
│   ├── baixar_fotos.py       busca fotos sob licença livre e pontua candidatas
│   ├── finalizar_fotos.py    limpa fundo, recorta e equaliza a saliência
│   ├── gerar_estimulos.py    versão alternativa em ilustração
│   ├── gerar_audio.ps1       sintetiza as frases e mede o onset de cada palavra
│   ├── montar_protocolo.py   confere os onsets e monta o protocolo
│   └── estimulos/
│       ├── imagens/          8 PNGs + CREDITOS.md
│       ├── candidatas/       fotos baixadas, para revisão
│       └── audio/            16 WAVs + onsets.csv
├── analisador/
│   ├── sincronizar.py        acha os bipes na trilha de áudio do vídeo
│   ├── analisar.py           TR, acurácia, baseline, exclusões
│   ├── teste_sintetico.py    regras de protocolo
│   ├── teste_sync.py         detecção de bipe
│   └── teste_pipeline.py     integração ponta a ponta
├── codificador/
│   └── index.html            codificação manual e concordância
├── cowork/                   primeira versão, como veio do zip
└── dados/                    sessões (nunca versionar)
```

---

## Antes de usar com crianças

Termo de consentimento assinado pelos responsáveis. Vídeo de rosto de criança é dado
pessoal de menor: tudo roda e fica local, sem nuvem e sem API externa, com IDs anônimos
e direito de exclusão a qualquer momento. Os detalhes estão na seção de ética do
[PLANO.md](PLANO.md).

Este é um instrumento de pesquisa, não uma avaliação diagnóstica. Uma medida isolada de
uma criança tem variabilidade alta e não deve ser interpretada sozinha.
