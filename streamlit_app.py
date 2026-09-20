"""
Dashboard da Carteira Polo Parnaíba (Streamlit).

Reproduz o dashboard estático `dashboard_carteira.html` (gerado por
`build_dashboard.py` a partir de `base_dashboard.ipynb` e `modelo_churn.ipynb`
no projeto `projeto_churn-main`), lendo o MESMO payload de dados
(`painel_carteira.json` — figuras, KPIs e lista de visitas já calculados) para
garantir que os gráficos e números sejam idênticos aos da versão HTML.

Acrescenta uma terceira aba, "E-mail", para preparar o contato ativo com um
cliente da lista de visitas — funcionalidade que não existe na versão HTML.

Rodar com:  streamlit run streamlit_app.py

Como atualizar os dados quando a base mudar: ver README.md.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.parse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "painel_carteira.json"

NOTA_LISTA = (
    "Cada lista é gerada por um modelo de gradient boosting treinado apenas com os meses "
    "anteriores ao mês-base (backtest walk-forward) e ranqueia os clientes ativos no "
    "fechamento do mês pelo risco de zerar o TPV no mês seguinte. A posição é o ranking da "
    "carteira inteira; o filtro de rota apenas recorta a lista. O resultado no mês seguinte "
    "é o churn realizado e aparece quando a carteira daquele mês fecha. Os identificadores "
    "são pseudonimizados: a correspondência com o cliente é feita internamente, pelo de-para "
    "restrito. Para medir o efeito das abordagens, recomenda-se manter um grupo de controle "
    "sorteado dentro da lista, que não é abordado."
)

st.set_page_config(page_title="Carteira Polo Parnaíba", layout="wide", page_icon="📊")


@st.cache_data
def load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Formatação (replica numero()/pct1()/reais()/inteiro() do dashboard_carteira.html)
# ---------------------------------------------------------------------------
def fmt_int(v) -> str:
    if v is None:
        return "–"
    return f"{round(v):,}".replace(",", ".")


def fmt_milhoes(v) -> str:
    if v is None:
        return "–"
    if abs(v) < 1e6:
        return "R$ " + fmt_int(round(v / 1e3)) + "k"
    return "R$ " + f"{v / 1e6:.1f}".replace(".", ",") + "MM"


def fmt_valor(v, formato: str) -> str:
    if v is None:
        return "–"
    return fmt_milhoes(v) if formato == "milhoes" else fmt_int(v)


def fmt_pct1(v) -> str:
    if v is None:
        return "–"
    return f"{v * 100:.1f}".replace(".", ",") + "%"


def fmt_reais(v) -> str:
    if v is None:
        return "–"
    return "R$ " + fmt_int(v)


def montar_delta(item: dict) -> tuple[str | None, str]:
    """Replica a lógica de cor/sinal de nota() no dashboard_carteira.html."""
    nota = item.get("nota")
    if nota is None:
        return None, "off"
    texto_valor = f"{abs(round(nota, 1)):.1f}".replace(".", ",")
    if item["nota_tipo"] == "variacao":
        sinal = "-" if nota < 0 else ""
        delta = f"{sinal}{texto_valor}%"
        cor = "inverse" if item.get("alta_e_boa") is False else "normal"
    else:
        delta = f"{texto_valor}%"
        cor = "off"
    return delta, cor


def cartoes_kpi(itens: list[dict]):
    cols = st.columns(2)
    for i, item in enumerate(itens):
        delta, cor = montar_delta(item)
        with cols[i % 2]:
            st.metric(
                item["rotulo"], fmt_valor(item["valor"], item["formato"]),
                delta=delta, delta_color=cor, help=item.get("nota_rotulo"),
            )


def to_fig(fig_json) -> go.Figure | None:
    if fig_json is None:
        return None
    return go.Figure(data=fig_json["data"], layout=fig_json["layout"])


def plot(fig_json, titulo_vazio="Sem dados suficientes nesta rota para montar este gráfico."):
    fig = to_fig(fig_json)
    if fig is None:
        st.info(titulo_vazio)
        return
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Carrega dados e monta o seletor de rota (compartilhado pelas 3 abas)
# ---------------------------------------------------------------------------
data = load_data()
rotas = list(data["figuras"].keys())

st.title("📊 Carteira Polo Parnaíba")

rota = st.selectbox("Rota", rotas, key="rota_sel")
kpi = data["kpis"][rota]
st.caption(
    f"Mês de referência {kpi['mes']} · janela {kpi['janela']} · "
    f"{fmt_int(kpi['documentos'])} documentos na rota"
)

tab_carteira, tab_lista, tab_email = st.tabs(["Carteira", "Lista de visitas", "E-mail"])

# ---------------------------------------------------------------------------
# Aba 1 — Carteira
# ---------------------------------------------------------------------------
with tab_carteira:
    figs = data["figuras"][rota]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader(f"Carteira · {kpi['mes']}")
        cartoes_kpi(kpi["carteira"])
    with c2:
        st.subheader(f"TPV · {kpi['mes']}")
        cartoes_kpi(kpi["tpv_mes"])
    with c3:
        st.subheader(f"Ticket médio por cliente · {kpi['mes']}")
        cartoes_kpi(kpi["tpv_medio"])

    st.divider()
    plot(figs["base_ativa"])

    col_esq, col_dir = st.columns([1, 1.18])
    with col_esq:
        plot(figs["novos_ativos"])
        plot(figs["reativacoes"])
        plot(figs["churn"])
    with col_dir:
        plot(figs["ponte_semestral"])

    plot(figs["ponte_mensal"])
    plot(figs["tpv_total"])

    col_esq2, col_dir2 = st.columns([1, 1.18])
    with col_esq2:
        plot(figs["tpv_medio"])
        plot(figs["tpv_na_m1"])
        plot(figs["perda_churn"])
    with col_dir2:
        plot(figs["ponte_tpv"])

# ---------------------------------------------------------------------------
# Aba 2 — Lista de visitas
# ---------------------------------------------------------------------------
lista = data["lista"]
meses_por_rotulo = {m["rotulo"]: m for m in lista["meses"]}
faixas_por_rotulo = {
    f"Visitas (posições 1 a {lista['capacidade']})": lista["capacidade"],
    f"Visitas e telefone (1 a {lista['capacidade_telefone']})": lista["capacidade_telefone"],
}

with tab_lista:
    fc1, fc2 = st.columns([2, 2])
    mes_rotulo = fc1.selectbox("Lista para", list(meses_por_rotulo.keys()), key="mes_lista_sel")
    faixa_rotulo = fc2.selectbox("Faixa", list(faixas_por_rotulo.keys()), key="faixa_sel")
    mes = meses_por_rotulo[mes_rotulo]
    cap = faixas_por_rotulo[faixa_rotulo]

    linhas = sorted(
        (l for l in lista["linhas"] if l["mes_base"] == mes["base"] and l["posicao"] <= cap
         and (rota == "Todas as rotas" or l["rota"] == rota)),
        key=lambda l: l["posicao"],
    )

    st.subheader(f"Lista de visitas · {mes['lista_rotulo']} · base {mes['base_rotulo']}")

    esperados = sum(l["risco"] for l in linhas)
    avaliadas = [l for l in linhas if l["churn_realizado"] is not None]
    sairam = sum(1 for l in avaliadas if l["churn_realizado"] == 1)
    riscos = sorted(l["risco"] for l in linhas)
    mediana = riscos[(len(riscos) - 1) // 2] if riscos else None
    resumo = lista["backtest"].get(mes["base"], {})

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Clientes na lista", fmt_int(len(linhas)))
        st.caption(
            f"posições 1 a {cap} da carteira" if rota == "Todas as rotas"
            else f"entre as posições 1 a {cap}, nesta rota"
        )
    with k2:
        st.metric("Churns esperados", f"{esperados:.1f}".replace(".", ","))
        st.caption("soma das probabilidades de churn")
    with k3:
        st.metric("Risco mediano na lista", fmt_pct1(mediana))
        st.caption(f"na carteira ativa: {fmt_pct1(resumo.get('risco_mediano_ativos'))}")
    with k4:
        if not avaliadas:
            st.metric(f"Resultado em {mes['lista_rotulo']}", "Aguardando")
            st.caption("a carteira do mês ainda não fechou")
        else:
            precisao = sairam / len(avaliadas)
            recall = resumo.get(f"recall@{cap}")
            sem_resultado = len(linhas) - len(avaliadas)
            nota = (
                f"precisão {fmt_pct1(precisao)} · {fmt_pct1(recall)} dos "
                f"{fmt_int(resumo.get('churns_realizados'))} churns da carteira"
                if rota == "Todas as rotas" and recall is not None
                else f"precisão {fmt_pct1(precisao)} nesta rota"
            )
            if sem_resultado:
                nota += f" · {sem_resultado} sem resultado (fora da carteira seguinte)"
            st.metric(f"Saíram em {mes['lista_rotulo']}", fmt_int(sairam))
            st.caption(nota)

    st.caption(
        ("Carteira inteira." if rota == "Todas as rotas" else f"Rota {rota}.")
        + " A posição é o ranking de risco da carteira inteira."
    )

    def situacao(l: dict) -> str:
        if l["novo_ativo"]:
            return "Novo ativo"
        if l["reativacao"]:
            return "Reativação"
        return "Recorrente"

    def resultado(l: dict) -> str:
        if l["churn_realizado"] is None:
            return "⏳ Aguardando"
        return "🔴 Saiu" if l["churn_realizado"] == 1 else "🟢 Ficou"

    tabela = [{
        "Posição": l["posicao"],
        "Faixa": "visita" if l["posicao"] <= lista["capacidade"] else "telefone",
        "Cliente": l["cliente"],
        "Rota": l["rota"],
        "Perfil": f"{l['cluster']} · {lista['nomes_perfis'].get(l['cluster'], '')}",
        "Risco (%)": round(l["risco"] * 100, 1),
        "TPV do mês": fmt_reais(l["tpv_mes"]),
        "TPV médio 3 meses": fmt_reais(l["tpv_medio_3m"]),
        "Dias sem venda no fim do mês": fmt_int(l["dias_sem_venda"]),
        "Maior hiato (dias)": fmt_int(l["maior_hiato"]),
        "Dias com venda última semana": fmt_int(l["dias_ativos_ult7"]),
        "Meses desde a ativação": fmt_int(l["meses_ativacao"]),
        "Situação no mês": situacao(l),
        "Resultado no mês seguinte": resultado(l),
    } for l in linhas]

    if not tabela:
        st.warning("Nenhum cliente nesta combinação de rota/mês/faixa.")
    else:
        df_tabela = pd.DataFrame(tabela)

        st.dataframe(
            df_tabela,
            hide_index=True,
            use_container_width=True,
            height=min(38 * (len(df_tabela) + 1), 560),
            column_config={
                "Posição": st.column_config.NumberColumn("Posição", format="%d"),
                "Risco (%)": st.column_config.ProgressColumn(
                    "Risco", format="%.1f%%", min_value=0.0, max_value=100.0,
                ),
            },
        )

        def linha_csv(l: dict) -> list:
            def dec(v, casas=2):
                if v is None:
                    return ""
                return str(round(v, casas)).replace(".", ",")
            return [
                l["posicao"], "visita" if l["posicao"] <= lista["capacidade"] else "telefone",
                l["cliente"], l["rota"],
                f"{l['cluster']} {lista['nomes_perfis'].get(l['cluster'], '')}",
                dec(l["risco"] * 100), dec(l["tpv_mes"]), dec(l["tpv_medio_3m"]),
                dec(l["dias_sem_venda"], 0), dec(l["maior_hiato"], 0),
                dec(l["dias_ativos_ult7"], 0), dec(l["meses_ativacao"], 0),
                situacao(l),
                {None: "", 1: "saiu", 0: "ficou"}[l["churn_realizado"]],
            ]

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writerow(["posicao", "faixa", "cliente", "rota", "perfil", "risco_pct", "tpv_mes",
                          "tpv_medio_3m", "dias_sem_venda_fim_mes", "maior_hiato",
                          "dias_com_venda_ult7", "meses_desde_ativacao", "situacao", "resultado"])
        for l in linhas:
            writer.writerow(linha_csv(l))
        csv_bytes = ("﻿" + buffer.getvalue()).encode("utf-8")

        st.download_button(
            "⬇️ Exportar CSV", data=csv_bytes,
            file_name=f"lista_visitas_{mes['lista']}_{rota.replace(' ', '_')}.csv",
            mime="text/csv",
        )

    st.divider()
    st.markdown("**Perfis de cliente**")
    cols_perfil = st.columns(3)
    for i, (c, nome) in enumerate(lista["nomes_perfis"].items()):
        with cols_perfil[i % 3]:
            st.markdown(f"**{c} · {nome}**  \n{lista['perfis'].get(c, '')}")

    st.divider()
    plot(lista.get("figura_backtest"))
    st.caption(NOTA_LISTA)

# ---------------------------------------------------------------------------
# Aba 3 — E-mail (novo: não existe na versão HTML)
# ---------------------------------------------------------------------------
with tab_email:
    st.subheader("Preparar contato ativo para um cliente da lista")
    st.caption(
        "Usa a mesma lista filtrada na aba \"Lista de visitas\" (rota, mês e faixa). "
        "Ajuste os filtros lá para mudar as opções aqui."
    )

    if not linhas:
        st.info("Nenhum cliente na lista atual — ajuste os filtros na aba \"Lista de visitas\".")
    else:
        opcoes = [f"#{l['posicao']} · {l['cliente']} · {l['rota']}" for l in linhas]
        escolha = st.selectbox("Cliente", opcoes, key="email_cliente_sel")
        cliente = linhas[opcoes.index(escolha)]

        perfil_nome = lista["nomes_perfis"].get(cliente["cluster"], "")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Posição na lista", f"#{cliente['posicao']}")
        m2.metric("Risco", fmt_pct1(cliente["risco"]))
        m3.metric("Dias sem venda", fmt_int(cliente["dias_sem_venda"]))
        m4.metric("Perfil", f"{cliente['cluster']}")
        st.caption(f"{cliente['cluster']} · {perfil_nome} — {lista['perfis'].get(cliente['cluster'], '')}")

        info_a, info_b = st.columns(2)
        with info_a:
            st.markdown(
                f"**Documento:** {cliente['cliente']}  \n"
                f"**Rota:** {cliente['rota']}  \n"
                f"**Situação no mês:** {situacao(cliente)}"
            )
        with info_b:
            # "$" é escapado porque st.markdown trata "$...$" como LaTeX
            st.markdown(
                f"**TPV do mês:** {fmt_reais(cliente['tpv_mes']).replace('$', chr(92) + '$')}  \n"
                f"**TPV médio (3 meses):** "
                f"{fmt_reais(cliente['tpv_medio_3m']).replace('$', chr(92) + '$')}  \n"
                f"**Meses desde a ativação:** {fmt_int(cliente['meses_ativacao'])}"
            )

        with st.form("email_form"):
            vendedor_email = st.text_input(
                "E-mail do vendedor/dono do polo", placeholder="vendedor@querostone.com.br",
            )
            assunto = f"[Risco de churn] Ação necessária — {cliente['cliente']}"
            corpo = (
                f"Olá,\n\n"
                f"O cliente {cliente['cliente']} (rota {cliente['rota']}) está na lista de "
                f"visitas de {mes['lista_rotulo']} na posição #{cliente['posicao']}, com risco "
                f"de {fmt_pct1(cliente['risco'])} de zerar o TPV no mês seguinte.\n\n"
                f"Resumo:\n"
                f"- Perfil: {cliente['cluster']} · {perfil_nome}\n"
                f"- Situação no mês: {situacao(cliente)}\n"
                f"- TPV do mês: {fmt_reais(cliente['tpv_mes'])}\n"
                f"- TPV médio (3 meses): {fmt_reais(cliente['tpv_medio_3m'])}\n"
                f"- Dias sem venda no fim do mês: {fmt_int(cliente['dias_sem_venda'])}\n"
                f"- Maior hiato sem venda: {fmt_int(cliente['maior_hiato'])} dias\n"
                f"- Dias com venda na última semana: {fmt_int(cliente['dias_ativos_ult7'])}\n"
                f"- Meses desde a ativação: {fmt_int(cliente['meses_ativacao'])}\n\n"
                f"Recomenda-se iniciar contato ativo com o cliente o quanto antes.\n\n"
                f"— Radar de Churn (Polo Parnaíba)"
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
