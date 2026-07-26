#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processa uma sessão inteira a partir da pasta onde estão os arquivos.

Encontra sozinho o vídeo, o eventos.csv e (se já existir) a codificação do
olhar, roda a sincronização e a análise na ordem certa e diz, em português, o
que fazer em seguida. Existe para que rodar uma sessão não dependa de lembrar
dois comandos e a ordem deles.

Uso:
    python processar.py PASTA_DA_SESSAO
"""
from __future__ import annotations
import argparse, glob, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def acha(pasta: str, padroes: list[str], excluir: list[str] | None = None) -> str | None:
    for p in padroes:
        for c in sorted(glob.glob(os.path.join(pasta, p))):
            nome = os.path.basename(c).lower()
            if excluir and any(e in nome for e in excluir):
                continue
            return c
    return None


def roda(titulo: str, cmd: list[str]) -> bool:
    # O flush é necessário: sem ele o print fica no buffer do Python enquanto o
    # subprocesso escreve direto no console, e o cabeçalho aparece depois da
    # saída da etapa que ele anuncia.
    print(f"\n{'='*60}\n{titulo}\n{'='*60}", flush=True)
    r = subprocess.run(cmd)
    sys.stdout.flush()
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", help="pasta com o vídeo e o eventos.csv da sessão")
    a = ap.parse_args()
    pasta = os.path.abspath(a.pasta)
    if not os.path.isdir(pasta):
        print(f"Não é uma pasta: {pasta}")
        return 1

    video = acha(pasta, ["*.webm", "*.mp4", "*.mov", "*.MOV"])
    eventos = acha(pasta, ["*eventos*.csv", "*_eventos.csv"])
    # a codificação do olhar é qualquer csv que não seja o de eventos nem saída nossa
    olhar = acha(pasta, ["*olhar*.csv", "*anotacoes*.csv", "*gaze*.csv", "*.csv"],
                 excluir=["eventos", "por_trial", "onsets"])
    sinc = os.path.join(pasta, "sincronizacao.json")
    resultados = os.path.join(pasta, "resultados")

    print(f"Pasta   : {pasta}")
    print(f"Vídeo   : {os.path.basename(video) if video else '— não encontrado'}")
    print(f"Eventos : {os.path.basename(eventos) if eventos else '— não encontrado'}")
    print(f"Olhar   : {os.path.basename(olhar) if olhar else '— ainda não codificado'}")

    if not video or not eventos:
        print("\nFaltam arquivos. Coloque nesta pasta o .webm e o _eventos.csv que o "
              "apresentador baixou ao fim da sessão.")
        return 1

    if not roda("1/2 — sincronização (achando os bipes no vídeo)",
                [sys.executable, os.path.join(AQUI, "sincronizar.py"),
                 video, eventos, "--saida", sinc]):
        print("\nA sincronização falhou. Sem ela não dá para seguir.")
        return 1

    if not olhar:
        print(f"\n{'='*60}")
        print("Sincronização pronta. Falta a codificação do olhar.")
        print("\nPróximo passo: abra codificador/index.html no navegador, carregue")
        print(f"  {os.path.basename(video)}")
        print("e marque com A (esquerda), D (direita), X (fora). Baixe o CSV,")
        print("salve nesta mesma pasta e rode este comando de novo.")
        return 0

    if not roda("2/2 — análise (tempo de reação e acurácia)",
                [sys.executable, os.path.join(AQUI, "analisar.py"),
                 sinc, olhar, "--saida", resultados]):
        return 1

    print(f"\n{'='*60}")
    print(f"Pronto. Resultados em {resultados}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
