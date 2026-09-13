"""
Protótipo (Streamlit) do produto de dados de churn — Polo Franquia Parnaíba / Stone.

Mostra o Top 10 de clientes ATIVOS com maior risco de churn no próximo mês
(score provisório, ver `build_churn_data.py`), com filtros por nome/TPV/score,
card de detalhes que só aparece quando um cliente é selecionado (hover ou
clique), gráficos que atualizam junto, e um botão para preparar o e-mail de
contato ativo para o vendedor responsável.

Rodar com:  streamlit run streamlit_app.py
"""
import json
import urllib.parse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

DATA_PATH = Path(__file__).resolve().parent / "clientes_risco.json"

STONE_GREEN = "#52C465"
STONE_RED = "#FC4828"
STONE_DARK = "#3A3A3A"
STONE_GRAY = "#B0B0B0"

st.set_page_config(page_title="Radar de Churn — Polo Parnaíba", layout="wide", page_icon="📉")


@st.cache_data
def load_data():
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(payload["clientes"])
    return payload, df


payload, df = load_data()

st.title("📉 Radar de Churn — Polo Franquia Parnaíba")
st.caption(
    f"Mês de referência: **{payload['mes_referencia']}** · "
    f"{payload['total_clientes_ativos']} clientes ativos na carteira · "
    f"gerado em {payload['gerado_em']}"
)
with st.expander("⚠️ Sobre o score de risco (metodologia provisória)", expanded=False):
    st.write(payload["metodologia"])
    st.caption(
        "Este é um placeholder por regra de negócio, criado para validar o protótipo do "
        "dashboard. Quando o modelo de Machine Learning (treinado com a coluna `flag_churn`) "
        "estiver pronto, o ranking passa a vir da probabilidade prevista pelo modelo, sem "
        "mudar o restante do dashboard."
    )

if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None


def select_client(doc: str):
    st.session_state.selected_doc = doc


# ---------------------------------------------------------------------------
# Filtros + gráfico ranking (passar o mouse ou clicar em uma barra escolhe
# o cliente; sem seleção, o card ao lado fica com "—")
# ---------------------------------------------------------------------------
left, right = st.columns([1.1, 1.6], gap="large")

with left:
    st.subheader("Filtros")
    f1, f2, f3 = st.columns(3)
    nome_filtro = f1.text_input("Nome do cliente", placeholder="ex.: cliente_6740")
    tpv_min, tpv_max = float(df["tpv_m0"].min()), float(df["tpv_m0"].max())
    score_min, score_max = float(df["risk_score"].min()), float(df["risk_score"].max())
    tpv_range = f2.slider(
        "TPV do mês atual (R$)", min_value=tpv_min, max_value=tpv_max,
        value=(tpv_min, tpv_max),
    )
    score_range = f3.slider(
        "Score de risco", min_value=score_min, max_value=score_max,
        value=(score_min, score_max),
    )

    df_filtrado = df[
        df["nome_fantasia"].str.contains(nome_filtro, case=False, na=False)
        & df["tpv_m0"].between(tpv_range[0], tpv_range[1])
        & df["risk_score"].between(score_range[0], score_range[1])
    ]

    if st.session_state.selected_doc not in df_filtrado["documento"].values:
        st.session_state.selected_doc = None

    st.subheader("Top 10 — maior risco de churn")
    if df_filtrado.empty:
        st.warning("Nenhum cliente encontrado com esses filtros.")
    else:
        df_plot = df_filtrado.sort_values("risk_score")
        colors = [
            STONE_RED if doc == st.session_state.selected_doc else STONE_GRAY
            for doc in df_plot["documento"]
        ]
        # Listas Python puras (não Series/ndarray): o Plotly.js antigo embutido
        # no componente streamlit-plotly-events não decodifica o formato binário
        # "bdata" que o plotly.py novo usa por padrão para arrays numpy/pandas —
        # isso fazia o eixo de score aparecer errado (0–9 em vez de 0–100).
        fig_rank = go.Figure(
            go.Bar(
                x=df_plot["risk_score"].tolist(),
                y=df_plot["nome_fantasia"].tolist(),
                orientation="h",
                marker_color=colors,
                customdata=df_plot["documento"].tolist(),
                hovertemplate="<b>%{y}</b><br>Score de risco: %{x}<extra></extra>",
            )
        )
        fig_rank.update_layout(
            template="simple_white",
            height=430,
            margin=dict(t=10, l=10, r=10, b=10),
            xaxis_title="Score de risco (0–100)",
        )
        st.caption("Passe o mouse ou clique em uma barra para ver os detalhes do cliente →")
        clicked_or_hovered = plotly_events(
            fig_rank,
            click_event=True,
            hover_event=True,
            select_event=False,
            override_height=430,
            key="rank_chart",
        )
        if clicked_or_hovered:
            idx = clicked_or_hovered[0]["pointIndex"]
            select_client(df_plot.iloc[idx]["documento"])

        st.divider()
        st.caption("Ou selecione diretamente na tabela:")
        table_view = df_filtrado[[
            "rank", "nome_fantasia", "documento", "risk_score", "cidade", "uf", "vendedor",
        ]].rename(columns={
            "rank": "#", "nome_fantasia": "Cliente", "documento": "Documento",
            "risk_score": "Score", "cidade": "Cidade", "uf": "UF", "vendedor": "Vendedor",
        })
        sel = st.dataframe(
            table_view,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="table_select",
        )
        if sel.selection.rows:
            select_client(df_filtrado.iloc[sel.selection.rows[0]]["documento"])

# ---------------------------------------------------------------------------
# Card do cliente selecionado (placeholder "—" enquanto nada for selecionado)
# ---------------------------------------------------------------------------
with right:
    if st.session_state.selected_doc is None:
        st.subheader("Nenhum cliente selecionado")
        st.info(
            "Passe o mouse ou clique em uma barra do ranking (ou selecione uma linha na "
            "tabela) para ver os detalhes do cliente aqui."
        )
        m1, m2, m3, m4 = st.columns(4)
        for col, label in zip(
            (m1, m2, m3, m4),
            ["Score de risco", "Dias sem transacionar", "Queda de TPV (3m vs. atual)", "Tempo de casa"],
        ):
            col.metric(label, "—")
        st.markdown(
            "**Documento:** —  \n**Cidade/UF:** —  \n**Rota:** —  \n**Segmento (MCC):** —  \n"
            "**Vendedor responsável:** —  \n**Tipo de contrato:** —  \n"
            "**Antecipação (RAV):** —  \n**Canais já utilizados:** —"
        )
    else:
        cliente = df[df["documento"] == st.session_state.selected_doc].iloc[0]

        st.subheader(f"#{int(cliente['rank'])} · {cliente['nome_fantasia']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score de risco", f"{cliente['risk_score']:.1f}")
        m2.metric("Dias sem transacionar", f"{cliente['dias_sem_transacionar']:.0f}" if cliente["dias_sem_transacionar"] is not None else "—")
        queda = cliente["queda_tpv_pct"]
        m3.metric("Queda de TPV (3m vs. atual)", f"{queda:+.1f}%" if queda is not None else "—")
        m4.metric("Tempo de casa", f"{cliente['tempo_casa_anos']:.1f} anos" if cliente["tempo_casa_anos"] is not None else "—")

        info_cols = st.columns(2)
        with info_cols[0]:
            st.markdown(
                f"""
**Documento:** {cliente['documento']}
**Cidade/UF:** {cliente['cidade']} / {cliente['uf']}
**Rota:** {cliente['rota']}
**Segmento (MCC):** {cliente['mcc']}
"""
            )
        with info_cols[1]:
            st.markdown(
                f"""
**Vendedor responsável:** {cliente['vendedor']}
**Tipo de contrato:** {cliente['tipo_contrato'] or '—'}
**Antecipação (RAV):** {cliente['cadastro_rav']}
**Canais já utilizados ({cliente['n_canais_historico']}):** {', '.join(cliente['canais_historico'])}
"""
            )
        st.caption(
            "ℹ️ A base disponível para este protótipo já está anonimizada (sem telefone/e-mail "
            "reais do cliente). Em produção, os campos de contato viriam do CRM."
        )

        ytd = pd.DataFrame(cliente["tpv_ytd"])
        fig_tpv = go.Figure(
            go.Scatter(
                x=ytd["mes"], y=ytd["tpv"], mode="lines+markers",
                line=dict(color=STONE_RED, width=2.5),
                hovertemplate="%{x}<br>TPV: R$ %{y:,.0f}<extra></extra>",
            )
        )
        fig_tpv.add_hline(
            y=payload["media_tpv_ativos_m0"], line_dash="dot", line_color=STONE_GRAY,
            annotation_text="média da carteira ativa (mês atual)", annotation_position="top left",
        )
        fig_tpv.update_layout(
            template="simple_white", height=320,
            title=f"TPV mensal em {payload['ano_ytd']} (YTD)",
            margin=dict(t=40, l=10, r=10, b=10),
            xaxis=dict(type="category"),
        )
        st.plotly_chart(fig_tpv, use_container_width=True)

        st.divider()
        st.subheader("📧 Contato ativo")
        with st.form("email_form"):
            vendedor_email = st.text_input(
                "E-mail do vendedor/dono do polo",
                placeholder="vendedor@querostone.com.br",
            )
            assunto = f"[Risco de churn] Ação necessária — {cliente['nome_fantasia']}"
            corpo = (
                f"Olá,\n\n"
                f"O cliente {cliente['nome_fantasia']} (documento {cliente['documento']}, "
                f"{cliente['cidade']}/{cliente['uf']}, rota {cliente['rota']}) está classificado "
                f"como Top {int(cliente['rank'])} em risco de churn para o próximo mês "
                f"(score {cliente['risk_score']:.1f}/100).\n\n"
                f"Resumo:\n"
                f"- Dias sem transacionar: {cliente['dias_sem_transacionar']}\n"
                f"- Queda de TPV (3m vs. atual): {queda if queda is not None else 'n/d'}%\n"
                f"- TPV do mês atual: R$ {cliente['tpv_m0']:,.2f}\n"
                f"- Tempo de casa: {cliente['tempo_casa_anos']} anos\n"
                f"- Segmento: {cliente['mcc']}\n"
                f"- Canais já utilizados: {', '.join(cliente['canais_historico'])}\n\n"
                f"Recomenda-se iniciar contato ativo com o cliente o quanto antes.\n\n"
                f"— Radar de Churn (protótipo)"
            )
            st.text_area("Prévia do e-mail", value=f"Assunto: {assunto}\n\n{corpo}", height=260)
            enviar = st.form_submit_button("Gerar e-mail para o vendedor")

        if enviar:
            if not vendedor_email:
                st.warning("Informe o e-mail do vendedor para gerar o link.")
            else:
                mailto = "mailto:{}?subject={}&body={}".format(
                    urllib.parse.quote(vendedor_email),
                    urllib.parse.quote(assunto),
                    urllib.parse.quote(corpo),
                )
                st.success("E-mail preparado. Clique abaixo para abrir no seu cliente de e-mail.")
                st.link_button("✉️ Abrir e-mail para o vendedor", mailto)
                st.caption(
                    "Protótipo: este botão NÃO envia o e-mail automaticamente, apenas abre seu "
                    "cliente de e-mail com o texto pronto. Para envio automático real, integrar "
                    "com a API/SMTP de e-mail da empresa (ex.: Outlook/Gmail corporativo)."
                )
