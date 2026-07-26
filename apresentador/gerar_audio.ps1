<#
Gera os áudios das frases-portadoras com a voz pt-BR instalada no Windows e
registra o onset EXATO da palavra-alvo dentro de cada arquivo.

Por que isso resolve o problema do TTS no navegador: aqui a fala vira um ARQUIVO,
e a API de síntese informa a posição, em milissegundos dentro do áudio gerado, em
que cada palavra começa. O onset deixa de ser estimativa e passa a ser conhecido
por construção — que é a condição para o tempo de reação ser válido.

Limitação que permanece: a voz sintética não tem a prosódia da fala dirigida à
criança (mais lenta, mais aguda, com contorno melódico exagerado). Para coleta de
dados de verdade, grave uma voz humana e marque o onset com o marcar_onset.py.
Estes arquivos servem para pilotar o fluxo inteiro e para o teste de espelhamento.

Cada frase nomeia o alvo UMA vez. Repetir o nome dentro da frase colocaria uma
segunda nomeação dentro da janela de 300-1800 ms, e um deslocamento do olhar
causado pela segunda seria contado como resposta à primeira.

Uso:  powershell -ExecutionPolicy Bypass -File gerar_audio.ps1
#>

param(
  [string]$Saida = (Join-Path $PSScriptRoot "estimulos\audio"),
  [string]$Voz   = "Microsoft Maria Desktop",
  [int]$Rate     = -2
)

Add-Type -AssemblyName System.Speech

# O artigo acompanha o gênero da palavra. "Cadê o bola?" soa errado para
# qualquer falante e não é fala dirigida à criança, é ruído.
$palavras = @(
  @{ nome = "gato";     artigo = "o" }
  @{ nome = "bola";     artigo = "a" }
  @{ nome = "cachorro"; artigo = "o" }
  @{ nome = "sapato";   artigo = "o" }
  @{ nome = "banana";   artigo = "a" }
  # "carro" saiu: nao existe foto livre de um carro unico em fundo limpo, so
  # grupos, modelos de LEGO e ilustracoes. "livro" e igualmente familiar nessa
  # idade e fotografa bem.
  @{ nome = "livro";    artigo = "o" }
  @{ nome = "pato";     artigo = "o" }
  @{ nome = [string]([char]0x6D + [char]0x61 + [char]0xE7 + [char]0xE3); artigo = "a" }  # maçã
)
# "Cadê" escrito por código de caractere: este arquivo precisa continuar legível
# mesmo se for reaberto por um editor que erre a codificação.
$cade = "Cad" + [char]0xEA
$portadora = @{ a = "$cade {1} {0}?"; b = "Olha {1} {0}!" }

if (-not (Test-Path $Saida)) { New-Item -ItemType Directory -Force -Path $Saida | Out-Null }

$sint = New-Object System.Speech.Synthesis.SpeechSynthesizer
$vozes = $sint.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }
if ($vozes -notcontains $Voz) {
  Write-Output "Voz '$Voz' nao encontrada. Instaladas: $($vozes -join ', ')"
  exit 1
}
$sint.SelectVoice($Voz)
$sint.Rate = $Rate

$script:evts = @()
$sint.add_SpeakProgress({ param($snd,$e)
  $script:evts += [pscustomobject]@{ Texto = $e.Text; Ms = $e.AudioPosition.TotalMilliseconds } })

$linhas = @()
$problemas = 0

function Remove-Acento([string]$s) {
  $n = $s.Normalize([Text.NormalizationForm]::FormD).ToCharArray() | Where-Object {
    [Globalization.CharUnicodeInfo]::GetUnicodeCategory($_) -ne 'NonSpacingMark' }
  return (-join $n)
}

foreach ($w in $palavras) {
  $p = $w.nome
  foreach ($k in @("a","b")) {
    $frase = [string]::Format($portadora[$k], $p, $w.artigo)
    # nome de arquivo sem acento, para nao depender de codificacao no navegador
    $base  = (Remove-Acento $p).ToLower()
    $arq   = Join-Path $Saida "$base`_$k.wav"

    $script:evts = @()
    $sint.SetOutputToWaveFile($arq)
    $sint.Speak($frase)
    $sint.SetOutputToNull()

    # a palavra-alvo e a ultima do enunciado; casa ignorando acento e caixa.
    # Se a sintese fragmentar a palavra em mais de um evento (acontece com
    # 'maca'), vale o PRIMEIRO fragmento: e ali que o som comeca.
    $alvoNorm = $base
    $hit = $script:evts | Where-Object {
      $t = (Remove-Acento $_.Texto).ToLower()
      $t -eq $alvoNorm -or ($t.Length -ge 2 -and $alvoNorm.StartsWith($t))
    } | Select-Object -First 1

    if ($null -eq $hit) {
      Write-Output ("FALHA: nao achei '{0}' nos eventos de '{1}' (eventos: {2})" -f `
        $p, $frase, (($script:evts | ForEach-Object { $_.Texto }) -join '/'))
      $problemas++
      continue
    }

    # Ponto decimal invariante, nao a virgula do locale pt-BR: o parseFloat do
    # navegador leria "948,3" como 948 e perderia a fracao sem avisar.
    $onset = [math]::Round($hit.Ms, 1).ToString([Globalization.CultureInfo]::InvariantCulture)

    # Exporta TODAS as fronteiras de palavra. O risco real nao e a sintese errar
    # a posicao — ela sabe exatamente quando comecou a emitir cada palavra — e sim
    # eu casar o evento errado (pegar "o" em vez de "gato"). Com a lista completa
    # da para conferir que o alvo e mesmo a ULTIMA palavra do enunciado.
    $limites = ($script:evts | ForEach-Object {
      $_.Texto + ":" + [math]::Round($_.Ms,1).ToString([Globalization.CultureInfo]::InvariantCulture)
    }) -join "|"
    $ultimo = $script:evts[-1]
    $alvoEhUltimo = if ($ultimo.Ms -eq $hit.Ms) { "sim" } else { "nao" }

    $linhas += [pscustomobject]@{
      alvo = $p; variante = $k; arquivo = "estimulos/audio/$base`_$k.wav"
      frase = $frase; onset_ms = $onset
      alvo_eh_ultima_palavra = $alvoEhUltimo; limites = $limites
    }
    Write-Output ("{0,-9} {1}  onset {2,7} ms   {3}" -f $p, $k, $onset, $frase)
  }
}

$sint.Dispose()

$csv = Join-Path $Saida "onsets.csv"
$linhas | Export-Csv -Path $csv -NoTypeInformation -Encoding UTF8
Write-Output ""
Write-Output ("{0} arquivos gerados. Indice: {1}" -f $linhas.Count, $csv)
if ($problemas -gt 0) { Write-Output "$problemas frases falharam."; exit 1 }
