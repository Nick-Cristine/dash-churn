"""Caminhos do projeto, resolvidos a partir da raiz do repositorio.

Todo script e todo notebook deve pedir os caminhos aqui em vez de escrever
caminhos relativos soltos. Assim `python src/build_dashboard.py` funciona de
qualquer diretorio, e o notebook funciona tanto aberto no Jupyter (rodando de
`notebooks/`) quanto executado por dentro dos scripts de build.
"""
from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

DADOS_BRUTOS = RAIZ / "data" / "raw"
DADOS_TRATADOS = RAIZ / "data" / "processed"
NOTEBOOKS = RAIZ / "notebooks"
SAIDAS = RAIZ / "outputs"
FIGURAS = SAIDAS / "figuras"

BASE_PARQUET = DADOS_BRUTOS / "base.parquet"
# RESTRITOS: valor real -> pseudonimo. So para pseudonimizar meses novos; nunca exibir.
# Por padrao ficam em data/raw/. Para guarda-los fora do projeto, defina a variavel de
# ambiente CHURN_RESTRITO com a pasta onde estao (nenhum caminho local vai para o Git).
RESTRITO = Path(os.environ["CHURN_RESTRITO"]) if os.environ.get("CHURN_RESTRITO") else DADOS_BRUTOS
DE_PARA = RESTRITO / "de_para_clientes_RESTRITO.csv"
DE_PARA_STONECODES = RESTRITO / "de_para_stonecodes_RESTRITO.csv"
DE_PARA_COLABORADORES = RESTRITO / "de_para_colaboradores_RESTRITO.csv"
BACKUP_DE_PARA = RESTRITO / "backup_de_para"
BASE_EDITADA_PARQUET = DADOS_TRATADOS / "base_edited.parquet"
NOTEBOOK = NOTEBOOKS / "base_dashboard.ipynb"
NOTEBOOK_MODELO = NOTEBOOKS / "modelo_churn.ipynb"
BASE_MODELO_PARQUET = DADOS_TRATADOS / "base_modelo.parquet"


def encontra_raiz(inicio: Path | None = None) -> Path:
    """Sobe a arvore de diretorios ate achar a raiz do projeto.

    Usada pelo notebook, que nao tem `__file__` e pode rodar com o diretorio de
    trabalho em `notebooks/` ou na raiz, dependendo de quem o executa.
    """
    inicio = (inicio or Path.cwd()).resolve()
    for pasta in (inicio, *inicio.parents):
        if (pasta / "data").is_dir() and (pasta / "notebooks").is_dir():
            return pasta
    raise FileNotFoundError(
        "Raiz do projeto nao encontrada a partir de "
        f"{inicio}. Rode de dentro do repositorio."
    )
