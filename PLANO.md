# Teste de Eficiência de Processamento Linguístico (Looking-While-Listening)

Plano de construção de uma ferramenta baseada no paradigma da Anne Fernald (Stanford),
para uso em casa (setup simples) e na escola (setup avançado).

Documento em duas partes: **(1) resumo com comentários** sobre o que importa, e
**(2) passo a passo** para executar com o Claude Code.

---

# PARTE 1 — Resumo e comentários sobre os pontos principais

## 1.1 O que o teste faz

Duas figuras aparecem lado a lado (ex.: uma bola e um gato). Depois de ~2 segundos em
silêncio, toca um áudio: *"Onde está o gato?"*. A criança move os olhos. Uma câmera filma
o rosto dela. Depois, quadro a quadro, mede-se:

- **Tempo de reação (TR)** — quantos milissegundos a criança levou, a partir do início da
  palavra-alvo, para mover o olhar do distrator para o alvo.
- **Acurácia** — que proporção do tempo ela ficou olhando para a figura certa numa janela
  fixa depois da palavra.

Essas duas medidas juntas são o que Fernald chama de *eficiência de processamento
linguístico*: não é "a criança sabe a palavra?", é "quão rápido e automático é o acesso
a essa palavra?".

## 1.2 Por que isso importa (e por que os números são o que são)

Os achados que dão sentido ao teste:

- Aos **15 meses**, a criança tipicamente só olha para a figura certa *depois* que a
  palavra terminou. Aos **24-25 meses**, ela já desloca o olhar *antes* do fim da palavra —
  reconhecimento a partir dos primeiros fonemas.
- A **velocidade** de processamento aos 18-25 meses prediz crescimento de vocabulário e
  desempenho linguístico e cognitivo anos depois (Marchman & Fernald, 2008).
- A quantidade de **fala dirigida à criança** (não fala ambiente/TV/conversa entre adultos)
  prevê essa eficiência; diferenças por nível socioeconômico já são mensuráveis aos
  18 meses (Fernald, Marchman & Weisleder, 2013; Weisleder & Fernald, 2013).

**Comentário:** esse é o argumento pedagógico forte para uma escola — o teste torna
visível, em milissegundos, algo que o discurso sobre "conversar com a criança" costuma
deixar abstrato.

## 1.3 Os pontos técnicos que realmente decidem se o teste funciona

Estes são os que aparecem repetidamente nos artigos e que, se você errar, invalidam tudo:

1. **Resolução temporal.** A codificação clássica é quadro a quadro a 30 fps = **33 ms**
   por quadro. É o suficiente: as diferenças de interesse são de 100-400 ms. Se der
   60 fps (celular), melhor ainda.

2. **A janela de 300–1800 ms.** Deslocamentos de olhar que ocorrem **antes de 300 ms**
   após o início da palavra-alvo são rápidos demais para terem sido causados pela palavra —
   são antecipações ou movimentos espontâneos, e devem ser **descartados**. A janela de
   análise vai tipicamente de 300 a 1800 ms (alguns estudos usam até 3000 ms para acurácia).

3. **Só valem os trials "distrator-inicial" para TR.** O tempo de reação só é calculável
   quando, no exato instante do início da palavra, a criança estava olhando para a figura
   **errada**. Se já estava no alvo, não há para onde reagir. Isso significa que você vai
   descartar 40-60% dos trials para TR — por isso são necessários **muitos trials**
   (~32 é o padrão) e por isso a acurácia é medida em paralelo, aproveitando todos.

4. **O início exato da palavra-alvo.** Tudo é ancorado nesse instante. Não é o início da
   frase — é o início do fonema /g/ de "gato". Isso precisa ser marcado à mão no arquivo
   de áudio (Audacity, por exemplo) e guardado no arquivo de configuração.

5. **Sincronização áudio-vídeo.** O calcanhar de Aquiles. O vídeo da criança e a linha do
   tempo do estímulo são gravados por dispositivos diferentes, com latências diferentes e
   desconhecidas. A solução robusta: **um bipe curto no início de cada trial**, captado
   pelo microfone da câmera. O bipe na trilha de áudio do vídeo é a verdade sobre quando o
   som saiu de fato do alto-falante. Alinha-se por correlação cruzada. Funciona igual para
   webcam e para celular.

6. **Linha de base (baseline).** Mede-se a proporção de olhar para o alvo nos ~2000 ms
   *antes* da palavra. Serve para detectar viés (criança que só olha para a direita, ou
   figura muito mais chamativa). Sem baseline, você não sabe se um acerto foi
   compreensão ou preferência.

7. **Contrabalanceamento.** Cada palavra aparece como alvo à esquerda e à direita; cada
   par de figuras aparece nas duas direções; a ordem dos trials tem pelo menos duas
   versões. Sem isso, o efeito de lado contamina a medida.

8. **Posição da câmera.** No centro horizontal da tela (logo acima ou abaixo), na altura
   dos olhos da criança. Se a câmera estiver deslocada lateralmente, esquerda e direita
   ficam assimétricas e o classificador erra.

9. **Codificador cego.** Quem codifica (humano ou algoritmo) não deve ver a tela — só o
   rosto. É por isso que o setup padrão filma **apenas a criança**. Isso é automático no
   nosso caso e é uma vantagem.

10. **Atenção entre trials.** Um estímulo central animado + som ("Olha aqui!") traz o olhar
    de volta ao centro antes do próximo trial. Sem isso, a criança fica presa numa figura
    e a sequência inteira degrada.

## 1.4 Sobre a medição do olhar — a decisão de arquitetura mais importante

Existem duas famílias de solução, e a escolha muda tudo:

| Abordagem | Como funciona | Prós | Contras |
|---|---|---|---|
| **Classificação discreta** (esquerda / direita / desviado) | Rede neural olha o rosto e diz para que lado está olhando, quadro a quadro | É exatamente o que o paradigma precisa; treinada em bebês reais; funciona com vídeo caseiro ruim | Precisa de processamento offline |
| **Eye-tracking contínuo** (coordenada x,y do olhar) | Estima ponto de fixação na tela; exige calibração | Dá mapa de calor, permite mais de 2 regiões | Calibração com criança de 18 meses é impraticável; precisão baixa em webcam |

**Recomendação: classificação discreta, offline.** O paradigma de Fernald só precisa de
"esquerda ou direita" — pedir coordenadas contínuas é resolver um problema muito mais
difícil sem ganho. As duas ferramentas abertas maduras:

- **iCatcher+** ([icatcherplus.github.io](https://icatcherplus.github.io/)) — CNN treinada
  em 479 vídeos de bebês de 4 meses a 3,5 anos, gravados em laboratório *e* em casa por
  webcam. Classifica Left / Right / Away por quadro. `pip install icatcher`. É a escolha
  principal.
- **OWLET** ([github.com/denisemw/OWLET](https://github.com/denisemw/OWLET)) — pensado
  especificamente para vídeos de webcam e **celular** gravados em casa. Alternativa /
  segunda opinião.

**Comentário importante:** nenhuma dessas é 100%. O protocolo de pesquisa correto é
codificar **manualmente ~20% dos trials** e comparar com o automático. Se a concordância
for alta (>90% dos quadros), você confia no resto. Por isso a ferramenta precisa incluir
um **codificador manual** — não é acessório, é o padrão-ouro de validação.

## 1.5 O que este teste NÃO é

Ponto que precisa estar escrito em qualquer material que saia da escola:

- **Não é diagnóstico.** É um paradigma de pesquisa. Um TR alto num dia pode ser sono,
  fralda, timidez, ou a criança simplesmente não conhecer aquela palavra.
- **Só faz sentido em grupo ou longitudinalmente.** Uma medida isolada de uma criança tem
  ruído enorme. O valor está em (a) acompanhar a mesma criança ao longo de meses, ou
  (b) comparar médias de grupo antes/depois de uma intervenção.
- **Vocabulário é pré-requisito.** Se a criança não conhece "colher", o trial não mede
  velocidade — mede desconhecimento. Por isso se aplica **antes** um checklist de
  vocabulário com os pais e só se usam palavras que a criança já conhece.

## 1.6 Ética e dados (LGPD)

Vídeo do rosto de criança é dado pessoal sensível de menor. Regras que vão embutidas
na ferramenta:

- Termo de consentimento assinado pelos responsáveis, específico, dizendo o que é gravado,
  onde fica guardado, por quanto tempo, e quem vê.
- **Tudo roda e fica local.** Nada de nuvem, nada de API externa. O processamento
  (iCatcher+) é offline na própria máquina.
- IDs anônimos nos arquivos (`P07_2026-08-12`), com a chave nome↔ID em arquivo separado
  e protegido.
- Direito de apagar a qualquer momento — a ferramenta tem comando para isso.
- Resultado individual não vira rótulo nem vai para ficha da criança.

---

# PARTE 2 — Arquitetura da ferramenta

Três módulos independentes. A separação é deliberada: apresentar estímulo e medir olhar
são problemas diferentes, com requisitos de tempo real diferentes.

```
teste-lwl/
├── apresentador/          # (A) Roda no navegador, offline. Mostra figuras, toca áudio,
│   ├── index.html         #     grava webcam, gera log de eventos com timestamps.
│   ├── app.js
│   └── protocolo.json     #     definição dos trials, palavras, onsets
├── estimulos/
│   ├── imagens/           #     PNG 512x512, fundo branco liso
│   └── audio/             #     WAV 48kHz, voz feminina, fala dirigida à criança
├── analisador/            # (B) Python. Roda iCatcher+, sincroniza, calcula TR e acurácia.
│   ├── sincronizar.py     #     detecta o bipe no áudio do vídeo
│   ├── classificar.py     #     wrapper do iCatcher+
│   ├── calcular.py        #     TR, acurácia, baseline, exclusões
│   └── relatorio.py       #     CSV + gráficos + PDF
├── codificador/           # (C) Codificação manual quadro a quadro (padrão-ouro)
│   └── index.html         #     vídeo + teclas E/D/X/? + navegação por frame
└── dados/
    ├── P07_2026-08-12/    #     vídeo, log de eventos, anotações, resultados
    └── participantes.csv  #     chave protegida
```

## Por que o apresentador é web e não Python

O navegador dá de graça: `AudioContext` com agendamento em amostras (precisão de
sub-milissegundo no *agendamento*), `MediaRecorder` para gravar a webcam,
`requestVideoFrameCallback` para timestamps de quadro, e tela cheia. E roda igual em
qualquer máquina da escola sem instalar nada. O único cuidado: **latência real de saída
de áudio é desconhecida** — daí o bipe de sincronização.

## Fluxo de dados

```
1. Apresentador  → video_criança.webm + eventos.json (t=0 lógico, bipes marcados)
2. sincronizar.py → offset real entre linha do tempo lógica e quadros do vídeo
3. classificar.py → anotacoes.csv (frame, timestamp, L/R/Away, confiança)
4. calcular.py   → trials.csv (por trial: TR, acurácia, baseline, motivo de exclusão)
5. relatorio.py  → resumo.csv + curva de olhar ao longo do tempo + PDF
```

---

# PARTE 3 — Os três setups

## Setup A — Casa (simples)

**Equipamento:** notebook com webcam. Só isso.

- Criança no colo do responsável, de costas para ele (para não ver o rosto dele), ou em
  cadeirinha alta com o responsável ao lado, fora do campo de visão.
- Distância olho-tela: **50-60 cm**.
- Câmera no centro superior da tela (a interna do notebook já está no lugar certo).
- Luz **na frente** da criança, nunca atrás. Janela atrás = rosto preto = classificador falha.
- Parede lisa atrás da criança. Sem irmãos, TV, pets no campo de visão.
- Fones de ouvido **no responsável**, tocando música mascarante — para ele não ouvir o
  nome do alvo e inconscientemente sinalizar. (Detalhe do protocolo original que parece
  exagero e não é.)
- Volume alto o bastante para o bipe ser captado pelo microfone.

**Limitação honesta:** 30 fps, resolução baixa, ângulo visual pequeno em tela de 14".
Serve para triagem, brincadeira e demonstração. Não para publicação.

## Setup B — Escola (avançado)

- **Tela grande** (monitor 27" ou TV 40" a 80-100 cm). Ângulo visual maior = separação
  esquerda/direita muito mais clara = classificação muito mais confiável. É o ganho
  isolado mais importante.
- **Webcam externa** que faça 60 fps (Logitech C922/Brio ou similar), em tripé no centro,
  logo abaixo da tela, na altura dos olhos.
- **Cadeira infantil com cinto**, fixada a distância marcada no chão.
- Cortina/tecido preto fosco atrás da criança e nas laterais.
- Iluminação LED difusa frontal, constante (não depender de luz do dia).
- Alto-falantes externos calibrados no mesmo volume sempre (~65 dB na posição da criança).
- Sala silenciosa, porta fechada, aviso na porta.
- **Opcional:** segunda câmera (celular) em close nos olhos, para ter as duas fontes.

## Setup C — Celular como câmera

Esta é a variação com melhor custo-benefício.

**Regra importante: o celular é a CÂMERA, nunca a TELA.** Numa tela de 6", as duas figuras
ficam separadas por poucos graus de ângulo visual — o movimento ocular fica pequeno demais
para classificar com confiança. A tela tem que ser o notebook ou o monitor.

- Celular em tripé de mesa, logo abaixo do centro da tela, apontado para o rosto.
- Gravar em **60 fps ou 120 fps**, 1080p, foco travado no rosto, **modo avião**.
- Enquadramento: cabeça e ombros. Não dar zoom só nos olhos — o iCatcher+ precisa ver
  o rosto inteiro para estimar a pose da cabeça.
- Áudio do celular **ligado** — é o que carrega os bipes de sincronização.
- Depois: transferir o arquivo para o PC (cabo, não nuvem) e apontar o analisador para ele.

**Vantagens:** melhor sensor, melhor taxa de quadros, melhor foco. Foi exatamente para
este cenário (webcam + celular em casa) que o OWLET foi desenvolvido.

---

# PARTE 4 — Passo a passo para executar com o Claude Code

> **Estado em 25/07/2026.** As fases 0, 1, 2, 3, 5 e 6 estão feitas, a partir da fusão
> com a versão da sessão Cowork. Existe e está testado: apresentador com 32 trials,
> 8 imagens com saliência equalizada, 16 áudios com onset verificado, sincronização por
> bipe, cálculo de TR e acurácia, codificador manual com kappa, e três suítes de teste
> incluindo integração ponta a ponta. Veja o [README.md](README.md).
>
> **Falta:** instalar o codificador automático de olhar e fazer o teste de espelhamento
> (Fase 4 — precisa de uma gravação real), o relatório (Fase 7) e a gestão de dados
> (Fase 8). Recomendado: substituir a voz sintética por gravação humana.
>
> As fases abaixo ficam como registro do desenho e para as partes ainda não feitas.

---

### Fase 0 — Esqueleto e ambiente

```
Crie a estrutura de pastas do projeto teste-lwl em C:\Users\USER\Documents\teste-lwl
conforme a arquitetura do PLANO.md. Crie um ambiente virtual Python, um requirements.txt
(opencv-python, numpy, pandas, scipy, matplotlib, soundfile) e um README com instruções
de uso. Não instale o iCatcher+ ainda.
```

**Verificar:** pastas criadas, `pip install -r requirements.txt` roda sem erro.

---

### Fase 1 — Protocolo e estímulos

```
Crie protocolo.json com 32 trials. Use 8 palavras familiares em português
(bola, gato, sapato, livro, banana, carro, cachorro, colher), cada uma como alvo 4 vezes,
2x à esquerda e 2x à direita, pareada com distratores de categoria semântica diferente e
sílaba inicial diferente. Gere duas ordens contrabalanceadas (A e B), sem mais de 2 trials
seguidos com alvo do mesmo lado. Cada trial tem: id, imagem_alvo, imagem_distrator,
lado_alvo, arquivo_audio, onset_palavra_ms (deixe null por enquanto).
Estrutura de tempo de cada trial: 2000ms de pré-visualização silenciosa → frase →
2500ms após o fim da frase → 1500ms de atrator central.
Crie também um script gerar_placeholders.py que produza PNGs 512x512 de teste com o nome
da palavra escrito, para eu poder testar antes de ter as imagens reais.
```

**Verificar:** `protocolo.json` válido, contagem de lados equilibrada, placeholders gerados.

---

### Fase 2 — Apresentador (o coração)

```
Construa apresentador/index.html + app.js: aplicação de página única, funciona offline,
abre em tela cheia.

Requisitos:
- Fundo cinza médio uniforme. Duas figuras lado a lado, cada uma ocupando 30% da largura,
  centros a 25% e 75% da largura, centralizadas verticalmente.
- Áudio via Web AudioContext, agendado com audioCtx.currentTime (não usar <audio>.play()).
- No início exato de cada trial, tocar um bipe de 1000 Hz por 30 ms num canal, em volume
  baixo mas audível, para sincronização.
- Gravar a webcam com MediaRecorder (pedir 1280x720 a 60fps, aceitar o que vier),
  com áudio do microfone ligado. Salvar como .webm.
- Registrar em eventos.json, com timestamps de audioCtx.currentTime e de performance.now():
  início do trial, início do bipe, início da frase, onset previsto da palavra-alvo,
  fim da frase, fim do trial, e a taxa de quadros efetiva da câmera.
- Atrator central entre trials: círculo colorido pulsante + som curto.
- Tecla ESPAÇO pausa; ESC encerra e salva o que já tem.
- Tela inicial pedindo: ID do participante, data de nascimento, ordem (A ou B),
  e uma checagem de câmera com preview ao vivo e alerta se a taxa de quadros < 25fps.
- Ao final, oferecer download do .webm e do eventos.json.

Modo de teste: parâmetro ?demo=1 roda só 4 trials, sem gravar vídeo.
```

**Verificar:** rodar `?demo=1`, conferir que o áudio toca sincronizado com as imagens e
que o `eventos.json` sai coerente.

---

### Fase 3 — Sincronização

```
Escreva analisador/sincronizar.py. Ele recebe o .webm e o eventos.json.
- Extrai a trilha de áudio do vídeo com ffmpeg.
- Detecta os bipes de 1000 Hz por filtro passa-banda + envelope de energia + correlação
  cruzada com o modelo do bipe.
- Casa cada bipe detectado com o trial correspondente do eventos.json.
- Calcula o offset entre a linha do tempo lógica e a do vídeo, e verifica se há deriva
  (drift) ao longo da sessão — ajuste linear se houver.
- Emite sincronizacao.json com offset, deriva, número de bipes encontrados vs esperados,
  e um alerta claro se faltar bipe.
Inclua um teste com áudio sintético de bipes em posições conhecidas.
```

**Verificar:** teste sintético passa; num vídeo real, todos os 32 bipes são achados.

---

### Fase 4 — Classificação do olhar

```
Escreva analisador/classificar.py como wrapper do iCatcher+ (pip install icatcher, precisa
de ffmpeg no PATH). Ele roda o iCatcher+ sobre o vídeo e normaliza a saída para
anotacoes.csv com colunas: frame, tempo_ms, direcao (esquerda/direita/desviado),
confianca.
Detecte automaticamente se há GPU e use; senão CPU, avisando que vai demorar.
Importante: o iCatcher+ reporta a direção do ponto de vista da CRIANÇA. Verifique isso
com um vídeo de teste em que eu olho deliberadamente para um lado, e documente a
convenção adotada em comentário no topo do arquivo. Espelhamento trocado é o erro mais
provável do projeto inteiro.
Adicione --backend owlet como alternativa, deixando a interface igual.
```

**Verificar (crítico):** grave-se olhando para a bola à esquerda e confirme que o CSV diz
`esquerda`. Este é o teste que impede o erro mais caro do projeto.

---

### Fase 5 — Cálculo das medidas

```
Escreva analisador/calcular.py implementando o protocolo de Fernald:
- Para cada trial, alinhar as anotações à janela do trial usando sincronizacao.json.
- Baseline: proporção de olhar para o alvo nos 2000ms antes do onset da palavra.
- Determinar a fixação no instante do onset (alvo, distrator ou desviado).
- TR: só para trials com fixação inicial no DISTRATOR. É a latência até a primeira mudança
  para o alvo que se sustente por pelo menos 3 quadros consecutivos.
- Excluir TR < 300ms (rápido demais para ser resposta à palavra) e > 1800ms.
- Acurácia: proporção de quadros olhando o alvo entre 300 e 1800ms, sobre o total de
  quadros em que estava olhando para alguma das duas figuras (desviado não conta no
  denominador).
- Excluir o trial se mais de 50% dos quadros da janela forem "desviado", ou se a
  classificação tiver confiança baixa.
- Excluir a sessão se sobrarem menos de 12 trials válidos.
- Registrar em cada linha o MOTIVO da exclusão — nunca descartar em silêncio.
Saída: trials.csv (uma linha por trial) e resumo.json (TR mediano, acurácia média,
nº de válidos, viés de lado no baseline).
Use a mediana para o TR, não a média — a distribuição é assimétrica à direita.
```

**Verificar:** rodar sobre dados sintéticos com TR conhecido e conferir que ele recupera
os valores.

---

### Fase 6 — Codificador manual (padrão-ouro)

```
Construa codificador/index.html: player de vídeo para codificação quadro a quadro.
- Navegação: seta esquerda/direita = 1 quadro; shift = 10 quadros.
- Teclas de codificação: A = esquerda, D = direita, X = desviado, ? = incerto.
- A tecla marca do quadro atual em diante até a próxima marcação (codificação por eventos,
  não quadro a quadro individual — é muito mais rápido).
- O codificador NÃO vê qual lado era o alvo (cego). Só depois de salvar.
- Exporta anotacoes_manuais.csv no mesmo formato do automático.
- Uma tela de comparação que roda a concordância (% de quadros iguais e kappa de Cohen)
  entre manual e automático, com um gráfico de onde eles divergem.
```

**Verificar:** codificar 20-25% dos trials à mão e olhar a concordância. O padrão da
literatura para concordância entre dois codificadores humanos é **> 95%**; para o
automático contra o humano, abaixo de 90% não confie — investigue luz, ângulo e
enquadramento antes de olhar qualquer resultado.

---

### Fase 7 — Relatório

```
Escreva analisador/relatorio.py:
- Curva temporal: proporção de olhar para o alvo de -2000ms a +3000ms em relação ao onset
  da palavra, com faixa de erro padrão, linha vertical em 0 e sombreamento na janela
  300-1800ms. É o gráfico canônico da literatura.
- Histograma dos TRs válidos.
- Tabela por palavra.
- PDF de uma página, em português, com um cabeçalho que diz explicitamente:
  "Instrumento de pesquisa. Não é avaliação diagnóstica. Resultado individual de uma
  sessão tem variabilidade alta e não deve ser interpretado isoladamente."
- Um script agregar.py que junta várias sessões e faz o gráfico de evolução por criança
  ao longo do tempo.
```

---

### Fase 8 — Pipeline único e proteção de dados

```
Crie processar.py que roda tudo em sequência para uma pasta de sessão
(sincronizar → classificar → calcular → relatório), com barra de progresso e log.
Crie também gerenciar_dados.py com: cadastro de participante gerando ID anônimo,
listagem de sessões, e um comando apagar_participante que remove vídeos e dados de uma
criança de forma irreversível, com dupla confirmação.
Adicione .gitignore que exclua dados/ inteiro. Vídeos de crianças nunca vão para repositório.
Gere também um modelo de termo de consentimento em docx para os responsáveis.
```

---

## Ordem prática recomendada

1. Fases 0-2, e teste o apresentador consigo mesmo em frente à tela.
2. Fase 4 **isolada e primeiro** — instale o iCatcher+ e valide num vídeo seu.
   Se ele não funcionar bem no seu setup, o resto do projeto muda. Descubra isso cedo.
3. Fases 3 e 5.
4. Grave uma sessão real com uma criança conhecida e rode o pipeline.
5. Fase 6, codifique à mão e compare.
6. Fases 7-8 quando o núcleo estiver confiável.

---

# PARTE 5 — Riscos conhecidos e checklist

## Riscos, em ordem de probabilidade

| Risco | Sinal | Mitigação |
|---|---|---|
| **Espelhamento invertido** | Acurácia perto de 0% em vez de perto de 100% | Teste da Fase 4 com você mesmo, antes de tudo |
| **Bipe não detectado** | Faltam bipes no sincronizacao.json | Aumentar volume; verificar que o microfone da câmera está ativo |
| **Criança desiste no meio** | Poucos trials válidos | Dois blocos de 16 com pausa; sessão de no máximo 5 min |
| **Luz de fundo** | iCatcher+ com confiança baixa em toda a sessão | Luz sempre frontal; nunca janela atrás |
| **Ângulo visual pequeno** | Confusão esquerda/direita em tela pequena | Tela maior é o upgrade mais eficaz |
| **Criança não conhece a palavra** | Acurácia baixa só em palavras específicas | Checklist de vocabulário com os pais antes |
| **Deriva de taxa de quadros** | Erro cresce ao longo da sessão | Bipe em *todo* trial permite corrigir localmente |

## Checklist antes de cada sessão

- [ ] Consentimento assinado
- [ ] Criança descansada, alimentada, sem fome nem sono
- [ ] Checklist de vocabulário preenchido pelos responsáveis
- [ ] Luz frontal ligada, sem janela atrás
- [ ] Distância marcada, câmera centralizada na altura dos olhos
- [ ] Preview de câmera OK, taxa de quadros ≥ 25 fps
- [ ] Volume testado, bipe audível
- [ ] Responsável com fones e música mascarante
- [ ] Espaço em disco livre
- [ ] Celular (se usado) em modo avião, 60 fps, foco travado

---

# PARTE 6 — Referências

**Palestra (bom material para apresentar aos pais):**
- Anne Fernald — *Why talking to little kids matters*, TEDxMonterey.
  [YouTube](https://www.youtube.com/watch?v=IpHwJyjm7rM) — mostra o paradigma em vídeo,
  com a tela dividida e o olhar do bebê. É a melhor peça de comunicação do método para
  quem não vai ler os artigos.

**Paradigma:**
- Fernald, Zangl, Portillo & Marchman (2008). *Looking while listening: Using eye movements
  to monitor spoken language comprehension by infants and young children.* — o capítulo
  metodológico, é o que descreve o procedimento em detalhe.
  [PDF](https://www.uu.nl/sites/default/files/looking_while_listening.pdf)
- Fernald, Pinto, Swingley, Weinberg & McRoberts (1998). *Rapid gains in speed of verbal
  processing by infants in the 2nd year.* Psychological Science.
  [Link](https://journals.sagepub.com/doi/10.1111/1467-9280.00044)
- Fernald, Marchman & Weisleder (2013). *SES differences in language processing skill and
  vocabulary are evident at 18 months.* Developmental Science.
  [Link](https://onlinelibrary.wiley.com/doi/abs/10.1111/desc.12019)
- Weisleder & Fernald (2013). *Talking to children matters.* Psychological Science.
  [Link](https://journals.sagepub.com/doi/abs/10.1177/0956797613488145)

**Ferramentas abertas:**
- iCatcher+ — [site](https://icatcherplus.github.io/) ·
  [GitHub](https://github.com/icatcherplus/icatcher_plus) ·
  [artigo](https://pubmed.ncbi.nlm.nih.gov/37655047/)
- OWLET — [GitHub](https://github.com/denisemw/OWLET) ·
  [artigo](https://link.springer.com/article/10.3758/s13428-022-01962-w) ·
  [guia do usuário](https://denisewerchan.com/documents/OWLET_UserGuide.pdf)
- Lookit / Children Helping Science (MIT) — a plataforma aberta que você lembrava.
  [artigo Open Mind](https://direct.mit.edu/opmi/article/1/1/4/2933/Lookit-Part-1-A-New-Online-Platform-for) ·
  [lookit.mit.edu](https://lookit.mit.edu) · [childrenhelpingscience.com](https://childrenhelpingscience.com)
- **Peekbank** (Stanford) — banco de dados aberto de estudos looking-while-listening.
  Use para calibrar o desenho contra a literatura e para alinhar o esquema de dados ao
  padrão da área. https://peekbank.github.io/peekbank-website/
- WebGazer em primeira infância — validação —
  [Infancy 2024](https://onlinelibrary.wiley.com/doi/10.1111/infa.12564)
