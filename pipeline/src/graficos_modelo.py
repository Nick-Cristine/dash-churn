"""Graficos do modelo de churn, compartilhados pelo dashboard e pelo relatorio.

Seguem o sistema visual dos graficos da carteira: superficie clara, tinta quase
preta, grade recessiva e um unico eixo por grafico. O modelo aparece em verde e
as referencias em cinza. Quando duas series dividem o grafico, cada uma tem
tambem marcador proprio e legenda, para a identidade nunca depender so da cor;
os rotulos de valor usam a cor do texto, nunca a da serie.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

TINTA, SECUNDARIA, SUAVE = "#0b0b0b", "#52514e", "#898781"
GRADE, EIXO, SUPERFICIE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
NEUTRO_CLARO = "#a3a198"
VERDE = "#0f8a58"
# Modelo contra referencia cinza: o par #0f8a58 x #898781 reprova no validador
# (dE 13,8 em visao normal, 5,7 em protanopia). #00522a x #898781 passa com folga
# (dE 25,6; 21,5 no pior caso de daltonismo) e e o passo escuro da rampa verde.
VERDE_MODELO = "#00522a"
VERMELHO, VERMELHO_CLARO = "#d03b3b", "#ef9393"
FONTE = "system-ui, -apple-system, 'Segoe UI', sans-serif"
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Numeracao por risco no treino (celula 11 do notebook do modelo). Os builds
# conferem os perfis antes de usar estes nomes.
NOMES_CLUSTER = {
    "C1": "Reativados",
    "C2": "Pequenos e irregulares",
    "C3": "Novos ativos",
    "C4": "Recém-chegados de TPV alto",
    "C5": "Carteira madura média",
    "C6": "Carteira madura grande",
}
DESCRICAO_CLUSTER = {
    "C1": "Voltaram a vender depois de um mês zerado. Pequenos, com hiato longo.",
    "C2": "TPV baixo, dias sem venda no fim do mês e hiatos frequentes. Concentram "
          "a maior parte dos churns.",
    "C3": "Primeiro mês de venda depois de três meses zerados.",
    "C4": "Chegaram há pouco, com TPV alto e só um mês ativo entre os três anteriores.",
    "C5": "Vendem quase todo dia, com TPV intermediário. Metade da base, risco baixo.",
    "C6": "Maior TPV e mais tempo de casa. O menor risco da carteira.",
}

DESCRICAO_FEATURES = {
    "tpv_total": ("TPV Total do mês", "Adquirência mais PIX QR Code validado."),
    "tpv_total_medio_m1_m3": ("TPV médio dos 3 meses anteriores", "Média simples de M-1 a M-3."),
    "transacoes": ("Transações no mês", "Quantidade de vendas processadas."),
    "Mensalidade_m0": ("Mensalidade", "Receita de mensalidade de equipamento no mês."),
    "Flag_IPV": ("Isenção por volume", "Isenção de mensalidade condicionada a TPV."),
    "Receita_Bruta_Banking": ("Receita bruta de banking", "Receita da conta Stone no mês."),
    "Tem_seguro": ("Tem seguro", "Seguro de vida ou de loja contratado."),
    "flag_multi_stonecode": ("Mais de um cadastro", "Documento com mais de um Stonecode."),
    "flag_novo_ativo": ("Novo ativo no mês", "Vendeu após três meses zerados."),
    "flag_reativacao": ("Reativação no mês", "Voltou a vender após um mês zerado."),
    "flag_novo_ativo_m1": ("Novo ativo no mês anterior", "Primeiro mês cheio de venda."),
    "Rota_atual": ("Rota", "Rota vigente do cliente, aplicada a todo o histórico."),
    "dias_sem_transacao_fim_mes": ("Dias sem venda no fim do mês",
                                   "Dias entre a última venda em cartão e o fim do mês."),
    "maior_hiato_sem_transacao": ("Maior hiato sem venda",
                                  "Maior sequência de dias seguidos sem venda em cartão."),
    "dias_ativos_ultimos_7": ("Dias com venda na última semana",
                              "Dias com venda nos 7 últimos dias do mês."),
    "share_tpv_ultimos_10_dias": ("Peso dos 10 últimos dias",
                                  "TPV dos 10 últimos dias sobre o TPV do mês."),
    "cv_tpv_diario": ("Volatilidade diária", "Desvio padrão sobre média do TPV diário."),
    "mes_calendario": ("Mês do ano", "Captura a sazonalidade."),
    "tempo_ativacao_meses": ("Meses desde a ativação", "Tempo desde a primeira transação."),
    "tem_contrato_multa": ("Contrato com multa", "Contrato vigente com multa por rescisão."),
    "conta_stone_fechada": ("Conta Stone encerrada", "Conta encerrada até o fim do mês."),
    "razao_tpv_m0_media_m1_m3": ("TPV do mês sobre a média anterior",
                                 "Abaixo de 1: vendeu menos que nos 3 meses anteriores."),
    "meses_ativos_m1_m3": ("Meses ativos entre os 3 anteriores", "De 0 a 3."),
    "share_pix": ("Peso do PIX", "PIX QR Code validado sobre o TPV Total."),
    "share_credito": ("Peso do crédito", "Crédito sobre o TPV de cartão."),
    "ticket_medio": ("Ticket médio", "TPV de cartão por transação."),
    "aderencia_tpv_estimado": ("TPV sobre o TPV estimado",
                               "Volume realizado contra o compromisso declarado."),
    "tipo_documento": ("Tipo de documento", "CNPJ, CPF ou MEI."),
    "canal_venda": ("Canal de venda", "Franquia, comercial, inbound, polo e outros."),
    "cadastro_rav": ("Modalidade de antecipação", "Automática, pontual ou Fast."),
    "domicilio_stone": ("Recebe na Stone", "Domicílio bancário na própria Stone."),
    "mcc_grupo": ("Segmento (MCC)", "15 MCCs mais frequentes e Outros."),
}


def rotulo_mes(texto, longo: bool = False) -> str:
    """'2026-08' -> 'Ago/26' (ou 'Ago/2026')."""
    ano, mes = str(texto).split("-")
    return f"{MESES[int(mes) - 1]}/{ano if longo else ano[2:]}"


def pct(valor, casas: int = 1) -> str:
    if valor is None or pd.isna(valor):
        return "–"
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def _padrao(eixo, **propriedades):
    """Aplica um valor so onde o grafico ainda nao definiu o seu."""
    for nome, valor in propriedades.items():
        if getattr(eixo, nome) is None:
            setattr(eixo, nome, valor)


def _layout(fig, titulo, subtitulo, altura, *, legenda=True, esquerda=64, direita=28):
    fig.update_layout(
        title=dict(text=(f"<b>{titulo}</b><br><span style='font-size:13px;"
                         f"color:{SECUNDARIA}'>{subtitulo}</span>"),
                   x=0.01, xanchor="left", yref="container", y=1, yanchor="top",
                   pad=dict(t=16), font=dict(size=17, color=TINTA)),
        height=altura, margin=dict(t=112 if legenda else 90, r=direita, b=56, l=esquerda),
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, separators=",.",
        font=dict(family=FONTE, size=13, color=SECUNDARIA),
        hoverlabel=dict(bgcolor=SUPERFICIE, bordercolor=EIXO,
                        font=dict(family=FONTE, color=TINTA)),
        showlegend=legenda,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                    font=dict(size=12, color=SECUNDARIA)),
        bargap=0.32, bargroupgap=0.1,
    )
    # padroes que cada grafico pode ter sobrescrito antes (grade, cor dos rotulos)
    _padrao(fig.layout.xaxis, showgrid=False, linecolor=EIXO, ticks="")
    _padrao(fig.layout.yaxis, gridcolor=GRADE, zeroline=False, showline=False)
    return fig


# =============================================================================
# Validacao
# =============================================================================
def grafico_backtest(backtest: pd.DataFrame, capacidade: int = 120, altura: int = 400):
    """Recall mensal da lista: modelo contra a regra simples, walk-forward."""
    b = backtest.dropna(subset=[f"modelo_recall@{capacidade}"])
    x = [rotulo_mes(m) for m in b["mes_lista"]]
    fig = go.Figure()
    for nome, prefixo, cor, simbolo in (("Regra: dias sem venda no fim do mês", "regra", SUAVE, "square"),
                                        ("Gradient boosting", "modelo", VERDE_MODELO, "circle")):
        fig.add_scatter(
            x=x, y=b[f"{prefixo}_recall@{capacidade}"], name=nome, mode="lines+markers",
            line=dict(color=cor, width=2),
            marker=dict(color=cor, size=9, symbol=simbolo, line=dict(color=SUPERFICIE, width=2)),
            customdata=np.column_stack([b[f"{prefixo}_churns@{capacidade}"], b["churns_realizados"]]),
            hovertemplate=(f"<b>%{{x}}</b><br>{nome}<br>%{{y:.1%}} dos churns do mês "
                           "(%{customdata[0]:.0f} de %{customdata[1]:.0f})<extra></extra>"))

    # rotulo direto so no ultimo ponto de cada serie
    fim = b.iloc[-1]
    modelo, regra = fim[f"modelo_recall@{capacidade}"], fim[f"regra_recall@{capacidade}"]
    for valor, acima in ((modelo, modelo >= regra), (regra, regra > modelo)):
        fig.add_annotation(x=x[-1], y=valor, text=f"<b>{pct(valor, 0)}</b>", showarrow=False,
                           xanchor="left", xshift=10, yshift=9 if acima else -9,
                           font=dict(color=TINTA, size=12))

    total = b["churns_realizados"].sum()
    fig.update_yaxes(tickformat=".0%", range=[0, 1.0], dtick=0.2)
    return _layout(
        fig, f"Churns do mês seguinte capturados pela lista de {capacidade}",
        f"Cada ponto é uma lista gerada por um modelo treinado só com os meses anteriores. "
        f"No acumulado de {len(b)} listas: modelo "
        f"{pct(b[f'modelo_churns@{capacidade}'].sum() / total)}, regra "
        f"{pct(b[f'regra_churns@{capacidade}'].sum() / total)}.",
        altura, direita=56)


def grafico_comparacao(comparacao: pd.DataFrame, churns_teste: int, capacidade: int = 120,
                       altura: int = 320):
    """Recall da lista de 120 no teste de jan-jun/2026, por abordagem."""
    ordem = [("Sorteio (referencia)", "Lista sorteada"),
             ("Regra: dias sem venda no fim do mes", "Regra: dias sem venda"),
             ("Regressao logistica", "Regressão logística"),
             ("Gradient boosting", "Gradient boosting")]
    valores = [comparacao.loc[chave, f"recall@{capacidade}"] for chave, _ in ordem]
    precisoes = [comparacao.loc[chave, f"precisao@{capacidade}"] for chave, _ in ordem]
    fig = go.Figure(go.Bar(
        y=[nome for _, nome in ordem], x=valores, orientation="h", width=0.58,
        marker=dict(color=[SUAVE, SUAVE, SUAVE, VERDE_MODELO], cornerradius=4),
        text=[f"<b>{pct(v)}</b>" for v in valores], textposition="outside",
        textfont=dict(color=TINTA, size=13), cliponaxis=False, customdata=precisoes,
        hovertemplate="<b>%{y}</b><br>Recall: %{x:.1%}<br>Precisão: %{customdata:.1%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, max(valores) * 1.2], showgrid=True,
                     gridcolor=GRADE)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=TINTA, size=13))
    return _layout(fig, f"Churns capturados pela lista de {capacidade}, teste jan–jun/2026",
                   f"Treino em jan–nov/2025. Seis meses de teste, {churns_teste} churns no total.",
                   altura, legenda=False, esquerda=170)


def grafico_importancia(importancia: pd.DataFrame, n: int = 12, altura: int = 460):
    """Importancia por permutacao das n features mais usadas."""
    top = importancia.head(n).iloc[::-1]
    nomes = [DESCRICAO_FEATURES.get(f, (f, ""))[0] for f in top["feature"]]
    valores = top["queda_%"] / 100
    fig = go.Figure(go.Bar(
        y=nomes, x=valores, orientation="h", width=0.62,
        marker=dict(color=VERDE, cornerradius=4),
        text=[pct(v) for v in valores], textposition="outside",
        textfont=dict(color=TINTA, size=12), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Queda do PR-AUC ao embaralhar: %{x:.1%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, valores.max() * 1.18], showgrid=True,
                     gridcolor=GRADE)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=TINTA, size=12))
    return _layout(fig, "O que o modelo usa para ranquear os clientes",
                   f"Queda do PR-AUC no teste quando a variável é embaralhada, em % do PR-AUC "
                   f"do modelo. As {n} maiores.", altura, legenda=False, esquerda=260)


def grafico_clusters(perfil: pd.DataFrame, altura: int = 420):
    """Taxa de churn por cluster, 2025 contra 2026."""
    x = [f"<b>{c}</b><br>{NOMES_CLUSTER[c]}" for c in perfil.index]
    fig = go.Figure()
    for ano, coluna, cor, rotula in (("2025", "churn_2025", VERMELHO_CLARO, False),
                                     ("2026", "churn_2026", VERMELHO, True)):
        valores = perfil[coluna] / 100
        fig.add_bar(
            x=x, y=valores, name=f"Churn no mês seguinte, {ano}",
            marker=dict(color=cor, cornerradius=4),
            text=[f"<b>{pct(v)}</b>" for v in valores] if rotula else None,
            textposition="outside", textfont=dict(color=TINTA, size=12), cliponaxis=False,
            customdata=np.column_stack([perfil["parte_base_2026"], perfil["parte_churns_2026"]]),
            hovertemplate=(f"<b>%{{x}}</b><br>{ano}: %{{y:.1%}}<br>Em 2026: %{{customdata[0]:.1f}}% "
                           "da base e %{customdata[1]:.1f}% dos churns<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", range=[0, (perfil[["churn_2025", "churn_2026"]].max().max()
                                                  / 100) * 1.22])
    fig.update_xaxes(tickfont=dict(color=TINTA, size=12))
    return _layout(fig, "Taxa de churn no mês seguinte por perfil de cliente",
                   "Clusters ajustados com os ativos de 2025 e aplicados a 2026 sem reajuste. "
                   "Rótulos mostram 2026.", altura)


def grafico_calibracao(avaliacao: pd.DataFrame, mes_rotulo: str, altura: int = 400):
    """Risco medio previsto contra churn realizado, por faixa de risco."""
    d = avaliacao[avaliacao["presente"]]
    faixa = pd.cut(d["risco"], [0, .05, .2, .5, 1.0001], include_lowest=True,
                   labels=["0 a 5%", "5 a 20%", "20 a 50%", "50 a 100%"])
    g = d.groupby(faixa, observed=True).agg(clientes=("risco", "size"),
                                            previsto=("risco", "mean"),
                                            realizado=("churn_realizado", "mean"),
                                            churns=("churn_realizado", "sum"))
    # os valores vao no rotulo da categoria: dentro do grafico o rotulo da barra
    # colidia com o losango do previsto quando os dois ficam proximos
    x = [f"<b>Risco {faixa_}</b><br>{format(n, ',').replace(',', '.')} clientes<br>"
         f"previsto {pct(p)} · realizado <b>{pct(r)}</b>"
         for faixa_, n, p, r in zip(g.index, g["clientes"], g["previsto"], g["realizado"])]
    fig = go.Figure()
    fig.add_bar(x=x, y=g["realizado"], name="Churn realizado", width=0.5,
                marker=dict(color=VERDE, cornerradius=4),
                customdata=g["churns"],
                hovertemplate="<b>%{x}</b><br>Realizado: %{y:.1%} (%{customdata:.0f} churns)<extra></extra>")
    fig.add_scatter(x=x, y=g["previsto"], name="Risco médio previsto", mode="markers",
                    marker=dict(symbol="diamond", size=13, color=TINTA,
                                line=dict(color=SUPERFICIE, width=2)),
                    hovertemplate="<b>%{x}</b><br>Previsto: %{y:.1%}<extra></extra>")
    fig.update_yaxes(tickformat=".0%", range=[0, max(g["realizado"].max(), g["previsto"].max()) * 1.25])
    fig.update_xaxes(tickfont=dict(color=TINTA, size=12))
    return _layout(fig, f"Risco previsto e churn realizado, {mes_rotulo}",
                   "Clientes ativos no mês anterior, agrupados pela faixa de risco atribuída "
                   "pelo modelo.", altura)


# =============================================================================
# Preparacao da base
# =============================================================================
def grafico_vazamento(base_treino: pd.DataFrame, altura: int = 300):
    """Taxa de churn no mes seguinte conforme a data da ultima transacao."""
    y = base_treino["alvo_churn_m1"].astype(int)
    depois = base_treino["Data_ultima_transacao"] > base_treino["data_referencia"]
    nomes = [f"Última transação depois<br>do fechamento ({pct(depois.mean(), 0)} das linhas)",
             f"Sem transação depois<br>do fechamento ({pct(1 - depois.mean(), 0)} das linhas)"]
    valores = [y[depois].mean(), y[~depois].mean()]
    fig = go.Figure(go.Bar(
        y=nomes, x=valores, orientation="h", width=0.55,
        marker=dict(color=VERMELHO, cornerradius=4),
        text=[f"<b>{pct(v, 2)}</b>" for v in valores], textposition="outside",
        textfont=dict(color=TINTA, size=13), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Churn no mês seguinte: %{x:.2%}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, max(valores) * 1.25], showgrid=True,
                     gridcolor=GRADE)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=TINTA, size=12))
    return _layout(fig, "Churn no mês seguinte conforme a data da última transação",
                   "A data vem de uma extração feita cerca de 10 dias após o fechamento e já "
                   "enxerga o mês que se quer prever.", altura, legenda=False, esquerda=210)


ROTULOS_MOTIVOS = {
    "sugestao": "Dependentes de outra variável (decisão da equipe)",
    "vazamento": "Vazamento comprovado",
    "suspeita": "Suspeita de vazamento",
    "identificador": "Identificador ou alta cardinalidade",
    "substituida": "Substituídas por features derivadas",
    "sem_sinal": "Sem significado conhecido ou sem sinal",
    "quase_constante": "Variância quase nula",
    "populacao": "Constantes na população do modelo",
}


def destinos_colunas(exclusoes: dict, features_base: list, n_chaves: int = 3):
    """Lista (rotulo, quantidade, papel) com o destino de cada coluna da base."""
    destinos = [("Mantidas como features", len(features_base), "mantida")]
    for chave, rotulo in ROTULOS_MOTIVOS.items():
        quantidade = sum(1 for motivo in exclusoes.values() if motivo == chave)
        papel = "vazamento" if chave in {"vazamento", "suspeita"} else "excluida"
        destinos.append((rotulo, quantidade, papel))
    destinos.append(("Chaves (documento, mês e data)", n_chaves, "chave"))
    return destinos


def grafico_reducao(destinos: list[tuple[str, int, str]], altura: int = 420):
    """Destino das colunas da base tratada. destinos: (rotulo, quantidade, papel)."""
    cores = {"mantida": VERDE, "vazamento": VERMELHO, "excluida": SUAVE, "chave": NEUTRO_CLARO}
    destinos = destinos[::-1]
    fig = go.Figure(go.Bar(
        y=[r for r, _, _ in destinos], x=[q for _, q, _ in destinos], orientation="h",
        width=0.62, marker=dict(color=[cores[p] for _, _, p in destinos], cornerradius=4),
        text=[f"<b>{q}</b>" for _, q, _ in destinos], textposition="outside",
        textfont=dict(color=TINTA, size=12), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x} colunas<extra></extra>"))
    fig.update_xaxes(range=[0, max(q for _, q, _ in destinos) * 1.15], showgrid=True,
                     gridcolor=GRADE)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=TINTA, size=12))
    total = sum(q for _, q, _ in destinos)
    return _layout(fig, f"Destino das {total} colunas da base tratada",
                   "Verde: entram no modelo como estão. Vermelho: vazamento comprovado ou "
                   "suspeito. Cinza: excluídas por redundância ou falta de sinal.",
                   altura, legenda=False, esquerda=300)
