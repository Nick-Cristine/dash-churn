"""
Gera `painel_carteira.json` executando o pipeline REAL do projeto (os notebooks
`base_dashboard.ipynb` e `modelo_churn.ipynb`, através de `build_dashboard.py`)
— não lê nem depende do `dashboard_carteira.html` em nenhum momento.

É essencialmente o mesmo cálculo que `build_dashboard.py` faz para montar o
HTML, mas em vez de gerar uma página com os dados embutidos em JS, salva
`figuras` + `kpis` + `lista` como JSON puro, que o app Streamlit
(`../streamlit_app.py`) lê para desenhar os mesmos gráficos e tabelas.

Demora ~2-3 min (o notebook do modelo treina 13+ modelos de gradient boosting
no backtest walk-forward). Rodar de novo sempre que a base (`data/raw/base.parquet`)
mudar:

    python pipeline/gerar_painel_json.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import build_dashboard as bd  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent.parent / "painel_carteira.json"


def main() -> None:
    t0 = time.perf_counter()
    print("1/3 — Executando base_dashboard.ipynb (tratamento da base + gráficos da carteira)...")
    ns = bd.carrega_notebook()
    df = ns["df"]

    contagem = df.drop_duplicates("Documento")["Rota_atual"].value_counts()
    rotas = ["Todas as rotas"] + [
        r for r, n in contagem.items() if n >= bd.MIN_DOCUMENTOS_ROTA
    ]

    figuras, kpis = {}, {}
    for rota in rotas:
        recorte = df if rota == "Todas as rotas" else df[df["Rota_atual"] == rota]
        bd.FALHAS.clear()
        figuras[rota] = {
            nome: bd.figura_para_json(fig)
            for nome, fig in bd.constroi_figuras(ns, recorte).items()
        }
        kpis[rota] = bd.calcula_kpis(ns, recorte)
        aviso = f"  falhas: {bd.FALHAS}" if bd.FALHAS else ""
        print(f"  {rota:<22} {recorte['Documento'].nunique():>5} documentos{aviso}")

    print("\n2/3 — Executando modelo_churn.ipynb (treino + backtest walk-forward, ~2-3 min)...")
    ns_modelo = bd.carrega_modelo()
    lista = bd.dados_lista(ns_modelo)
    print(f"  {len(lista['meses'])} listas mensais, {len(lista['linhas']):,} linhas")

    print("\n3/3 — Salvando painel_carteira.json...")
    payload = {"figuras": figuras, "kpis": kpis, "lista": lista}
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    tamanho = OUT_PATH.stat().st_size / 1024**2
    print(f"\n{OUT_PATH} gerado: {tamanho:,.1f} MB em {time.perf_counter() - t0:,.0f}s")


if __name__ == "__main__":
    main()
