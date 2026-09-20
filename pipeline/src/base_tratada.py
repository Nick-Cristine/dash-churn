"""Carrega a base tratada executando as celulas de tratamento do notebook.

`notebooks/base_dashboard.ipynb` e a fonte unica de verdade do tratamento. O
dashboard executa o notebook inteiro; o modelo so precisa da base, entao roda
apenas as celulas de consolidacao e de feature engineering, sem os graficos.
"""
from __future__ import annotations

import io
from contextlib import nullcontext, redirect_stdout

import nbformat
import pandas as pd

import caminhos

CELULAS_TRATAMENTO = ("consolida", "features")


def carrega_base_tratada(verboso: bool = False) -> pd.DataFrame:
    """Devolve o `df` tratado, identico ao usado pelo dashboard."""
    nb = nbformat.read(caminhos.NOTEBOOK, as_version=4)
    por_id = {c.get("id"): c for c in nb.cells if c.cell_type == "code"}
    faltando = [i for i in CELULAS_TRATAMENTO if i not in por_id]
    if faltando:
        raise KeyError(f"Celulas nao encontradas em {caminhos.NOTEBOOK.name}: {faltando}")

    codigo = "\n\n".join(por_id[i].source for i in CELULAS_TRATAMENTO)
    ns: dict = {"__name__": "base_tratada"}
    with nullcontext() if verboso else redirect_stdout(io.StringIO()):
        exec(compile(codigo, f"<{caminhos.NOTEBOOK.name}>", "exec"), ns)
    return ns["df"]
