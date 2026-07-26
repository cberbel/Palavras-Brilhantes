# Como gravar e testar — 20 minutos

Este é o teste que você faz **em você mesmo**, antes de qualquer criança. Ele responde
a uma pergunta específica: o sistema está medindo o lado certo?

Se houver inversão de espelhamento, a acurácia sai perto de **zero** em vez de perto de
**cem**. É o erro mais provável do projeto inteiro, é invisível se ninguém procurar, e
descobri-lo depois significa jogar fora gravações de crianças reais.

---

## Antes de começar

- Notebook numa mesa, você sentado de frente, **50 a 60 cm** da tela.
- Luz **na sua frente**. Se houver janela atrás de você, feche a cortina.
- Volume alto o bastante para você ouvir bem — o microfone precisa captar o bipe.
- Fones **desligados**: o som tem que sair pelo alto-falante para ser gravado.

---

## 1. Rodar a sessão

Dê dois cliques em **`1-INICIAR TESTE.cmd`**.

Abre uma janela preta (o servidor — deixe aberta) e o Chrome no apresentador.

Na tela de configuração:

- **ID do participante:** `TESTE`
- **Rodar apenas os primeiros N trials:** `8`
- Autorize a câmera quando o Chrome pedir.
- Confira embaixo: tem que dizer que o `protocolo.txt` carregou com 32 trials, e que o
  áudio está ativo. Se disser que não há trilha de áudio, o bipe não será gravado e nada
  adiante funciona.

Clique em **Iniciar sessão**. Vai para tela cheia.

### O que fazer durante os 8 trials

Este é o ponto do teste. Faça exatamente assim:

1. Aparece uma **estrela no centro** — olhe para ela.
2. Aparecem **duas figuras** e ficam 2 segundos em silêncio — escolha **uma qualquer** e
   olhe fixo para ela. Não fique alternando.
3. Você ouve a frase: *"Cadê o gato?"* — **mova os olhos para a figura nomeada**, e
   fique nela até as figuras sumirem.

Mexa só os olhos, mantendo a cabeça parada e o rosto voltado para a tela.

O passo 2 é o que gera tempo de reação: em cerca de metade dos trials você terá escolhido
a figura errada, e é nesses que dá para medir quanto tempo levou para corrigir.

Ao final, clique nos dois botões e **baixe os dois arquivos**: o `.webm` e o
`_eventos.csv`.

Feche a janela preta do servidor.

---

## 2. Juntar os arquivos

Crie uma pasta, por exemplo `dados\TESTE-espelhamento`, e mova para dentro dela os dois
arquivos que acabou de baixar (estarão em Downloads).

---

## 3. Sincronizar

Arraste **a pasta** para cima de **`3-PROCESSAR SESSAO.cmd`**.

Ele acha o bipe de cada trial dentro do vídeo. O que você quer ver:

```
Trials esperados : 8
Bipes localizados: 8
Margem           : 3.20x
```

Bipes localizados tem que ser igual a trials esperados, e a margem acima de 1,5x. Se não
for, o problema é de áudio: volume baixo demais, ou microfone não gravou.

Ele vai avisar que falta a codificação do olhar. É o próximo passo.

---

## 4. Codificar o olhar

Dê dois cliques em **`2-CODIFICAR OLHAR.cmd`**.

- Carregue o `.webm` da sessão.
- Confirme o **fps** (o apresentador mostrou a taxa efetiva; normalmente 30).
- Ande com **→** um quadro por vez e marque:
  **A** quando seu olhar está na figura da esquerda, **D** na direita, **X** quando está
  fora das duas.
- Cada marca vale **do quadro atual até a próxima** — você só marca quando o olhar muda,
  não quadro a quadro.

Não precisa codificar os 8 trials para este teste. **Três já bastam** para revelar
inversão de espelhamento.

Clique em **Baixar anotacoes_manuais.csv** e salve na mesma pasta da sessão.

> **Esquerda é do seu ponto de vista olhando a tela**, não do vídeo espelhado.
> A prévia da câmera aparece espelhada, como um espelho de banheiro — se você olhou para
> a figura à sua esquerda, marque **A**, mesmo que no vídeo pareça o contrário.
> Esta convenção é a mesma que o codificador automático usa.

---

## 5. Processar de novo

Arraste a pasta para o **`3-PROCESSAR SESSAO.cmd`** outra vez. Agora ele roda a análise.

### Como ler o resultado

```
Acurácia média     : 0.95
TR mediano         : 480 ms
Baseline médio     : 0.48
```

- **Acurácia perto de 1,0** — está correto. Você olhou para a figura nomeada e o sistema
  concordou. Pode seguir para as crianças.
- **Acurácia perto de 0,0** — **espelhamento invertido.** O sistema está trocando
  esquerda com direita. Não é para consertar codificando ao contrário: me avise, ou
  inverta o mapeamento na conversão da saída do codificador.
- **Acurácia perto de 0,5** — nem acertou nem errou sistematicamente. Provavelmente a
  codificação está desalinhada no tempo. Confira o fps que você informou.
- **Baseline perto de 0,5** é o esperado: antes da palavra você não tinha preferência.
- Seu **TR** vai ser mais rápido que o de uma criança — adulto conhece as palavras. Entre
  300 e 700 ms é normal.

O aviso de "menos de 12 trials válidos" é esperado num teste de 8 trials. Ignore.

---

## Depois que passar

Aí sim vale instalar o codificador automático (OWLET ou iCatcher+) e rodá-lo sobre este
mesmo vídeo. Como você já tem a codificação manual da mesma gravação, a tela de
comparação do codificador dá na hora a concordância e o kappa entre os dois — e você
descobre se o automático serve, no seu setup, antes de depender dele.

E ouça os 16 clipes de áudio uma vez. A verificação automática confere tempo, não
pronúncia.
