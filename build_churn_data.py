"""
Gera o payload de dados (JSON) usado pelos dois protótipos de dashboard
(Streamlit e Quarto/Plotly): ranking provisório de risco de churn + todas
as informações/gráficos de cada um dos Top 10 clientes.

IMPORTANTE: o "risk_score" aqui é uma REGRA PROVISÓRIA (placeholder), não um
modelo de Machine Learning. Serve para validar o protótipo do dashboard
enquanto o modelo real (treinado com a coluna flag_churn) não fica pronto.
Quando o modelo estiver pronto, basta substituir a função `compute_risk_score`
por `model.predict_proba(X)[:, 1]` mantendo o resto do pipeline igual.

Regra provisória = média de duas percentis (0 a 1), cada uma calculada
apenas entre os clientes ATIVOS no mês mais recente:
  - dias_sem_transacionar (quanto maior, mais tempo sem vender -> mais risco)
  - queda percentual do TPV do mês atual vs. a média dos 3 meses anteriores
    (quanto maior a queda, mais risco)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent.parent
OUT_PATH = BASE_DIR / "clientes_risco.json"

TOP_N = 10


def load_base() -> pd.DataFrame:
    df = pd.read_parquet(PROJECT_DIR / "base_edited.parquet")
    df["data_referencia"] = pd.to_datetime(df["data_referencia"])
    return df


def compute_risk_score(snap: pd.DataFrame) -> pd.Series:
    dias = snap["dias_sem_transacionar"].fillna(snap["dias_sem_transacionar"].median())
    baseline = snap[["tpv_m1", "tpv_m2", "tpv_m3"]].mean(axis=1)
    queda_pct = ((baseline - snap["tpv_m0"]) / baseline.replace(0, np.nan)).clip(lower=0, upper=1)
    queda_pct = queda_pct.fillna(0.0)

    dias_pct = dias.rank(pct=True)
    queda_rank = queda_pct.rank(pct=True)

    score = 0.5 * dias_pct + 0.5 * queda_rank
    return (score * 100).round(1)


def build_ytd_series(df: pd.DataFrame, documento: str, ano: int) -> list[dict]:
    hist = df[(df.Documento == documento) & (df.data_referencia.dt.year == ano)]
    hist = hist.sort_values("data_referencia")
    return [
        {"mes": row.data_referencia.strftime("%Y-%m"), "tpv": None if pd.isna(row.tpv_m0) else round(float(row.tpv_m0), 2)}
        for row in hist.itertuples()
    ]


def build_channel_info(df: pd.DataFrame, documento: str) -> dict:
    # canais_venda vem como string com múltiplos canais separados por "|"
    # (ex.: "FRANQUIA|LINKABC|TAPONPHONE"); juntamos o histórico inteiro do
    # cliente e contamos canais distintos únicos, não strings compostas.
    hist = df[df.Documento == documento]
    canais = set()
    for valor in hist["canais_venda"].dropna():
        canais.update(valor.split("|"))
    canais = sorted(canais)
    return {"n_canais": len(canais), "canais": canais}


def safe(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def main():
    df = load_base()
    ultimo_mes = df.data_referencia.max()
    ano_atual = ultimo_mes.year
    snap = df[df.data_referencia == ultimo_mes].drop_duplicates("Documento").copy()
    ativos = snap[snap.status_ba_m0 == "Ativo"].copy()

    ativos["risk_score"] = compute_risk_score(ativos)
    top10 = ativos.sort_values("risk_score", ascending=False).head(TOP_N)
    media_tpv_ativos = round(float(ativos["tpv_m0"].mean()), 2)

    clientes = []
    for rank, row in enumerate(top10.itertuples(), start=1):
        documento = row.Documento
        tenure_anos = (ultimo_mes - row.Data_credenciamento).days / 365 if pd.notna(row.Data_credenciamento) else None
        canal_info = build_channel_info(df, documento)
        queda_pct = None
        baseline = pd.Series([row.tpv_m1, row.tpv_m2, row.tpv_m3]).mean()
        if baseline and baseline > 0:
            queda_pct = round(float((baseline - row.tpv_m0) / baseline) * 100, 1)

        clientes.append({
            "rank": rank,
            "documento": documento,
            "nome_fantasia": safe(row.Nome_fantasia),
            "risk_score": safe(row.risk_score),
            "cidade": safe(row.Cidade),
            "uf": safe(row.UF),
            "vendedor": safe(row.Vendedor),
            "mcc": safe(row.mcc),
            "rota": safe(row.Rota_atual),
            "tipo_contrato": safe(row.Tipo_contrato),
            "cadastro_rav": safe(row.Cadastro_RAV),
            "dias_sem_transacionar": safe(row.dias_sem_transacionar),
            "tempo_casa_anos": round(tenure_anos, 1) if tenure_anos is not None else None,
            "tpv_m0": safe(row.tpv_m0),
            "tpv_m1": safe(row.tpv_m1),
            "tpv_m2": safe(row.tpv_m2),
            "tpv_m3": safe(row.tpv_m3),
            "queda_tpv_pct": queda_pct,
            "qtd_stonecodes": safe(row.qtd_stonecodes),
            "qtd_stonecodes_ativos": safe(row.qtd_stonecodes_ativos),
            "n_canais_historico": canal_info["n_canais"],
            "canais_historico": canal_info["canais"],
            "tpv_ytd": build_ytd_series(df, documento, ano_atual),
        })

    payload = {
        "gerado_em": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "mes_referencia": ultimo_mes.strftime("%Y-%m"),
        "ano_ytd": ano_atual,
        "total_clientes_ativos": int(len(ativos)),
        "media_tpv_ativos_m0": media_tpv_ativos,
        "metodologia": (
            "Score provisorio (regra), NAO e um modelo de ML: "
            "50% percentil de dias_sem_transacionar + 50% percentil da queda "
            "percentual do TPV do mes atual vs. media dos 3 meses anteriores, "
            "calculado apenas entre os clientes ativos no mes de referencia."
        ),
        "clientes": clientes,
    }

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(clientes)} clientes -> {OUT_PATH}")
    for c in clientes:
        print(f"  #{c['rank']:>2} score={c['risk_score']:>5} doc={c['documento']} nome={c['nome_fantasia']}")


if __name__ == "__main__":
    main()
