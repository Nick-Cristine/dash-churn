"""Gera o dashboard interativo da carteira do Polo Parnaiba.

Uso:  python src/build_dashboard.py
Saida: dashboard_carteira.html (arquivo unico, compartilhavel, funciona offline)

FONTE DE VERDADE: este script NAO reimplementa o tratamento da base. Ele executa
as celulas de codigo de `base_dashboard.ipynb` em um namespace proprio e reusa de
la o dataframe tratado e as funcoes de grafico. Mudou a regra no notebook, o
dashboard segue junto. O que vive aqui e so a especificacao de cada grafico
(titulo, paleta, que matriz alimenta cada um) e o layout da pagina.

O seletor de rotas refaz TODOS os graficos para a rota escolhida. As figuras de
todas as rotas sao pre-calculadas e embutidas no HTML, entao a troca e instantanea
e a pagina nao depende de servidor nem de internet.

A aba "Lista de visitas" vem de `modelo_churn.ipynb`, tambem executado por dentro:
as listas mensais do backtest walk-forward (celula 14), cada uma gerada por um
modelo treinado so com os meses anteriores ao mes-base.
"""
from __future__ import annotations

import io
import json
import os
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

import nbformat
import pandas as pd
import plotly.io as pio

import caminhos
import graficos_modelo as gm

NOTEBOOK = caminhos.NOTEBOOK
SAIDA = caminhos.SAIDAS / "dashboard_carteira.html"
CELULAS_IGNORADAS = {"backup"}      # nao reescreve o parquet de backup
MIN_DOCUMENTOS_ROTA = 20            # rotas menores que isso nao entram no seletor
ALTURA_GRANDE, ALTURA_MEDIA = 470, 330
# As pontes laterais ficam na altura em que foram desenhadas. Esticar ate a
# altura dos tres graficos empilhados ao lado transformava as colunas em palitos
# e empurrava a legenda para cima do subtitulo; a coluna da direita e centralizada
# no CSS, o que resolve o desalinhamento sem deformar o grafico.
ALTURA_PONTE_LATERAL = 620
ALTURA_PONTE_LARGA = 620


# =============================================================================
# 1. Carrega o notebook como modulo
# =============================================================================
@contextmanager
def _na_pasta(pasta: Path):
    """Os notebooks acham a raiz a partir do diretorio de trabalho."""
    anterior = Path.cwd()
    os.chdir(pasta)
    try:
        yield
    finally:
        os.chdir(anterior)


def carrega_notebook(caminho: Path = NOTEBOOK, ignoradas: set | None = None,
                     nome: str = "carteira") -> dict:
    """Executa as celulas de codigo do notebook e devolve o namespace resultante."""
    ignoradas = CELULAS_IGNORADAS if ignoradas is None else ignoradas
    nb = nbformat.read(caminho, as_version=4)
    codigo = [c.source for c in nb.cells
              if c.cell_type == "code" and c.get("id") not in ignoradas]
    ns: dict = {"__name__": nome}
    with _na_pasta(caminhos.NOTEBOOKS):
        exec(compile("\n\n".join(codigo), f"<{caminho.name}>", "exec"), ns)
    return ns


def carrega_modelo() -> dict:
    """Executa o notebook do modelo em silencio, inclusive o backtest das listas."""
    with redirect_stdout(io.StringIO()):
        return carrega_notebook(caminhos.NOTEBOOK_MODELO, ignoradas=set(), nome="modelo")


# =============================================================================
# 2. Especificacao dos graficos
# =============================================================================
FALHAS: list[tuple[str, str, str]] = []


def constroi_figuras(ns: dict, dados: pd.DataFrame) -> dict:
    """Monta as figuras do dashboard para um recorte da base."""
    g = ns  # atalho para as funcoes vindas do notebook
    figuras: dict = {}

    def registra(nome, construtor):
        """Um grafico sem dados suficientes vira um aviso, nao um erro."""
        try:
            figuras[nome] = construtor()
        except Exception as erro:                      # noqa: BLE001
            figuras[nome] = None
            FALHAS.append((nome, type(erro).__name__, str(erro)[:90]))

    base_mensal = g["base_ativa_mensal"](dados)
    ativos = dados[dados["transacionou"] == 1]
    primeiro = dados["periodo"].min()

    def colunas(matriz, **kwargs):
        media, _, janela = g["media_ytd"](matriz)
        kwargs.setdefault("rotulo_ytd", f"Média Jan-{g['MESES_PT'][janela[-1] - 1]}")
        return g["grafico_colunas_ano"](matriz, ytd=media, **kwargs)

    # ---- carteira -----------------------------------------------------------
    registra("base_ativa", lambda: colunas(
        g["matriz_ano_mes"](ativos, "Documento", contagem=True), paleta="verde",
        titulo="Evolução da base ativa",
        subtitulo="Clientes com TPV Total maior que zero no mês. "
                  "Acima da coluna, a variação contra o mesmo mês do ano anterior.",
        altura=ALTURA_GRANDE))

    def fluxo(coluna, paleta, titulo, desde, alta_e_boa=True):
        matriz = g["matriz_ano_mes"](dados, coluna, desde=desde)
        taxa = g["matriz_taxa"](matriz, base_mensal)
        media, taxa_media, janela = g["media_ytd"](matriz, base_mensal)
        return g["grafico_colunas_ano"](
            matriz, paleta=paleta, titulo=titulo,
            subtitulo="Entre parênteses, o percentual sobre a base ativa do mês anterior.",
            taxa=taxa, ytd=media, ytd_taxa=taxa_media,
            rotulo_ytd=f"Média Jan-{g['MESES_PT'][janela[-1] - 1]}",
            alta_e_boa=alta_e_boa, altura=ALTURA_MEDIA)

    registra("novos_ativos", lambda: fluxo(
        "flag_novo_ativo", "azul", "Novos ativos", primeiro + 3))
    registra("reativacoes", lambda: fluxo(
        "flag_reativacao", "amarelo", "Reativações", primeiro + 3))
    registra("churn", lambda: fluxo(
        "flag_churn", "vermelho", "Churn", primeiro + 1, alta_e_boa=False))

    # ---- pontes da carteira -------------------------------------------------
    def ponte_semestral():
        janelas = g["janelas_de_meses"](fim=dados["periodo"].max(), passo=6,
                                        primeiro_valido=primeiro + 3)
        base_inicial, blocos = g["etapas_ponte_janelas"](dados, base_mensal, janelas)
        return g["grafico_ponte_janelas"](
            janelas[0][0] - 1, base_inicial, blocos,
            titulo="Ponte da base ativa em janelas de 6 meses",
            subtitulo="Colunas verdes são a base ativa ao fim de cada janela. "
                      "Entre elas, os fluxos acumulados do período.",
            altura=ALTURA_PONTE_LATERAL)

    def ponte_mensal():
        ano = int(dados["periodo"].max().year)
        inicio, base_inicial, passos = g["etapas_ponte_mensal"](dados, ano, base_mensal)
        return g["grafico_ponte_com_taxas"](
            inicio, base_inicial, passos, base_mensal,
            titulo=f"Ponte da base ativa em {ano}, com as taxas de fluxo",
            subtitulo="Colunas em escala absoluta, em clientes, no eixo da esquerda. "
                      "As linhas trazem cada fluxo como percentual da base ativa do mês "
                      "anterior,<br>no eixo da direita, ancorado ao da esquerda: 0% sobre "
                      "o zero e 10% sobre os 1.000 clientes. A tracejada é a meta de 5%.",
            altura=ALTURA_PONTE_LARGA)

    registra("ponte_semestral", ponte_semestral)
    registra("ponte_mensal", ponte_mensal)

    # ---- TPV ----------------------------------------------------------------
    matriz_tpv = g["matriz_ano_mes"](dados, "tpv_total") / g["MILHAO"]
    matriz_base = g["matriz_ano_mes"](ativos, "Documento", contagem=True)

    registra("tpv_total", lambda: colunas(
        matriz_tpv, paleta="verde_bandeira", titulo="TPV Total por mês",
        subtitulo="Adquirência mais PIX QR Code validado, em milhões de reais. "
                  "Acima da coluna, a variação contra o mesmo mês do ano anterior.",
        formato=g["em_milhoes"], altura=ALTURA_GRANDE))

    registra("tpv_medio", lambda: colunas(
        (matriz_tpv * g["MILHAO"] / matriz_base) / g["MIL"], paleta="verde_bandeira",
        titulo="TPV médio por cliente ativo",
        subtitulo="TPV Total do mês dividido pela base ativa, em milhares de reais.",
        formato=g["em_milhares"], altura=ALTURA_MEDIA))

    registra("tpv_na_m1", lambda: colunas(
        g["matriz_tpv_por_flag"](dados, "tpv_total", "flag_novo_ativo_m1",
                                 desde=primeiro + 4),
        paleta="azul", titulo="TPV do Novo Ativo no mês seguinte",
        subtitulo="TPV do mês dos clientes que foram Novo Ativo no mês anterior, "
                  "em milhões de reais.",
        formato=g["em_milhoes_1"], altura=ALTURA_MEDIA))

    registra("perda_churn", lambda: colunas(
        g["matriz_tpv_por_flag"](dados, "tpv_total_medio_m1_m3", "flag_churn",
                                 desde=primeiro + 3),
        paleta="vermelho", titulo="Perda de TPV por churn",
        subtitulo="Média do TPV do cliente em M-1, M-2 e M-3, somada, em milhões de "
                  "reais. Queda é resultado bom.",
        alta_e_boa=False, formato=g["em_milhoes_1"], altura=ALTURA_MEDIA))

    def ponte_tpv():
        ultimo, ano = int(dados["periodo"].max().month), int(dados["periodo"].max().year)
        etapas, _ = g["ponte_tpv_safra"](
            dados, g["janela_meses"](ano - 1, ultimo), g["janela_meses"](ano, ultimo),
            safra_desde=g["SAFRA_DESDE"])
        return g["grafico_ponte_tpv"](
            etapas,
            titulo=f"Ponte do TPV médio mensal, Jan-{g['MESES_PT'][ultimo - 1]} de "
                   f"{ano - 1} para {ano}",
            subtitulo="Cada cliente entra pela sua situação nas duas janelas: entrou, "
                      "ficou ou saiu. Valores em milhões de reais por mês.",
            altura=ALTURA_PONTE_LATERAL)

    registra("ponte_tpv", ponte_tpv)
    return figuras


# =============================================================================
# 3. Indicadores do cabecalho
# =============================================================================
def calcula_kpis(ns: dict, dados: pd.DataFrame) -> dict:
    """Numeros do cabecalho para um recorte da base."""
    g = ns
    mes = dados["periodo"].max()
    base_mensal = g["base_ativa_mensal"](dados)

    def soma(periodo, coluna, filtro=None):
        recorte = dados[dados["periodo"] == periodo]
        if filtro is not None:
            recorte = recorte[recorte[filtro] == 1]
        return float(recorte[coluna].sum())

    def valor_base(periodo):
        return float(base_mensal.get(periodo, float("nan")))

    def variacao(atual, anterior):
        if not anterior or pd.isna(anterior) or pd.isna(atual):
            return None
        return (atual / anterior - 1) * 100

    base_atual, base_anterior = valor_base(mes), valor_base(mes - 1)
    base_ano_passado = valor_base(mes - 12)

    def sobre_base_anterior(valor):
        return None if not base_anterior else valor / base_anterior * 100

    novos = soma(mes, "flag_novo_ativo")
    reativados = soma(mes, "flag_reativacao")
    perdidos = soma(mes, "flag_churn")

    # bloco de TPV do mes e a media mensal do ano, na mesma janela do ano anterior
    ultimo_mes, ano = int(mes.month), int(mes.year)
    def serie_tpv(periodo):
        return {
            "tpv": soma(periodo, "tpv_total"),
            "tpv_na_m1": soma(periodo, "tpv_total", "flag_novo_ativo_m1"),
            "tpv_reativacao": soma(periodo, "tpv_total", "flag_reativacao"),
            "perda_churn": soma(periodo, "tpv_total_medio_m1_m3", "flag_churn"),
        }

    tpv_mes, tpv_mes_ano_passado = serie_tpv(mes), serie_tpv(mes - 12)

    def por_cliente(periodo):
        """Ticket medio de cada fluxo: TPV dividido pelo numero de clientes dele.

        O denominador do TPV do Novo Ativo M1 e a contagem de novos ativos do mes
        ANTERIOR, que e a coorte que gerou esse TPV.
        """
        tpv = serie_tpv(periodo)
        divide = lambda valor, qtd: (valor / qtd) if qtd else None  # noqa: E731
        return {
            "tpv": divide(tpv["tpv"], valor_base(periodo)),
            "tpv_na_m1": divide(tpv["tpv_na_m1"], soma(periodo - 1, "flag_novo_ativo")),
            "tpv_reativacao": divide(tpv["tpv_reativacao"],
                                     soma(periodo, "flag_reativacao")),
            "perda_churn": divide(tpv["perda_churn"], soma(periodo, "flag_churn")),
        }

    ticket, ticket_ano_passado = por_cliente(mes), por_cliente(mes - 12)

    return {
        "documentos": int(dados["Documento"].nunique()),
        "mes": f"{g['MESES_PT'][mes.month - 1]}/{mes.year}",
        "janela": f"Jan-{g['MESES_PT'][ultimo_mes - 1]}",
        "carteira": [
            {"rotulo": "Base ativa", "valor": base_atual, "formato": "inteiro",
             "nota": variacao(base_atual, base_ano_passado), "nota_tipo": "variacao",
             "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "Novos ativos", "valor": novos, "formato": "inteiro",
             "nota": sobre_base_anterior(novos), "nota_tipo": "percentual",
             "nota_rotulo": "da base ativa do mês anterior"},
            {"rotulo": "Reativações", "valor": reativados, "formato": "inteiro",
             "nota": sobre_base_anterior(reativados), "nota_tipo": "percentual",
             "nota_rotulo": "da base ativa do mês anterior"},
            {"rotulo": "Churn", "valor": perdidos, "formato": "inteiro",
             "nota": sobre_base_anterior(perdidos), "nota_tipo": "percentual",
             "nota_rotulo": "da base ativa do mês anterior", "alta_e_boa": False},
        ],
        "tpv_mes": [
            {"rotulo": "TPV Total", "valor": tpv_mes["tpv"], "formato": "milhoes",
             "nota": variacao(tpv_mes["tpv"], tpv_mes_ano_passado["tpv"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "TPV do Novo Ativo M1", "valor": tpv_mes["tpv_na_m1"],
             "formato": "milhoes",
             "nota": variacao(tpv_mes["tpv_na_m1"], tpv_mes_ano_passado["tpv_na_m1"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "TPV de reativações", "valor": tpv_mes["tpv_reativacao"],
             "formato": "milhoes",
             "nota": variacao(tpv_mes["tpv_reativacao"],
                              tpv_mes_ano_passado["tpv_reativacao"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "Perda de TPV por churn", "valor": tpv_mes["perda_churn"],
             "formato": "milhoes", "alta_e_boa": False,
             "nota": variacao(tpv_mes["perda_churn"], tpv_mes_ano_passado["perda_churn"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
        ],
        "tpv_medio": [
            {"rotulo": "TPV por cliente ativo", "valor": ticket["tpv"],
             "formato": "milhoes",
             "nota": variacao(ticket["tpv"], ticket_ano_passado["tpv"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "TPV por novo ativo (M-1)", "valor": ticket["tpv_na_m1"],
             "formato": "milhoes",
             "nota": variacao(ticket["tpv_na_m1"], ticket_ano_passado["tpv_na_m1"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "TPV por reativação", "valor": ticket["tpv_reativacao"],
             "formato": "milhoes",
             "nota": variacao(ticket["tpv_reativacao"],
                              ticket_ano_passado["tpv_reativacao"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
            {"rotulo": "Perda por cliente em churn", "valor": ticket["perda_churn"],
             "formato": "milhoes", "alta_e_boa": False,
             "nota": variacao(ticket["perda_churn"], ticket_ano_passado["perda_churn"]),
             "nota_tipo": "variacao", "nota_rotulo": "vs mesmo mês do ano anterior"},
        ],
    }


# =============================================================================
# 4. Montagem do HTML
# =============================================================================
GRAFICOS_NA_PAGINA = ["base_ativa", "novos_ativos", "reativacoes", "churn",
                      "ponte_semestral", "ponte_mensal", "tpv_total", "tpv_medio",
                      "tpv_na_m1", "perda_churn", "ponte_tpv"]


NOTA_LISTA = (
    "Cada lista é gerada por um modelo de gradient boosting treinado apenas com os meses "
    "anteriores ao mês-base (backtest walk-forward) e ranqueia os clientes ativos no "
    "fechamento do mês pelo risco de zerar o TPV no mês seguinte. A posição é o ranking da "
    "carteira inteira; o filtro de rota apenas recorta a lista. O resultado no mês seguinte "
    "é o churn realizado e aparece quando a carteira daquele mês fecha. Os identificadores "
    "são pseudonimizados: a correspondência com o cliente é feita internamente, pelo de-para "
    "restrito. Para medir o efeito das abordagens, recomenda-se manter um grupo de controle "
    "sorteado dentro da lista, que não é abordado.")


def dados_lista(nsm: dict) -> dict:
    """Listas mensais do backtest walk-forward, prontas para a aba de visitas."""
    perfil = nsm["perfil_clusters"]
    assert perfil.loc["C1", "reativacao"] > 90 and perfil.loc["C3", "novo_ativo"] > 90, (
        "a numeracao dos clusters mudou: revise graficos_modelo.NOMES_CLUSTER")
    cap, cap_tel = nsm["CAPACIDADE"], nsm["CAPACIDADE_TELEFONE"]
    historico = nsm["historico_listas"]
    backtest = nsm["backtest_mensal"].set_index("mes_base")

    def numero(valor, casas=2):
        return None if pd.isna(valor) else round(float(valor), casas)

    linhas = [{
        "mes_base": r.mes_base, "posicao": int(r.posicao), "cliente": r.Documento,
        "rota": r.Rota_atual, "cluster": r.cluster, "risco": numero(r.risco, 4),
        "tpv_mes": numero(r.tpv_total), "tpv_medio_3m": numero(r.tpv_total_medio_m1_m3),
        "dias_sem_venda": numero(r.dias_sem_transacao_fim_mes, 0),
        "maior_hiato": numero(r.maior_hiato_sem_transacao, 0),
        "dias_ativos_ult7": numero(r.dias_ativos_ultimos_7, 0),
        "meses_ativacao": numero(r.tempo_ativacao_meses, 0),
        "novo_ativo": int(r.flag_novo_ativo), "reativacao": int(r.flag_reativacao),
        "churn_realizado": None if pd.isna(r.churn_realizado) else int(r.churn_realizado),
    } for r in historico.itertuples(index=False)]

    resumo, meses = {}, []
    for mes in sorted(backtest.index, reverse=True):
        linha = backtest.loc[mes]
        resumo[mes] = {
            "risco_mediano_ativos": numero(linha["risco_mediano_ativos"], 4),
            "churns_realizados": numero(linha.get("churns_realizados"), 0),
            f"recall@{cap}": numero(linha.get(f"modelo_recall@{cap}"), 4),
            f"recall@{cap_tel}": numero(linha.get(f"modelo_recall@{cap_tel}"), 4),
        }
        lista = linha["mes_lista"]
        meses.append({"base": mes, "lista": lista,
                      "base_rotulo": gm.rotulo_mes(mes, longo=True),
                      "lista_rotulo": gm.rotulo_mes(lista, longo=True),
                      "rotulo": f"{gm.rotulo_mes(lista, longo=True)} (base "
                                f"{gm.rotulo_mes(mes, longo=True)})"})

    return {"linhas": linhas, "meses": meses, "backtest": resumo,
            "capacidade": cap, "capacidade_telefone": cap_tel,
            "nomes_perfis": gm.NOMES_CLUSTER, "perfis": gm.DESCRICAO_CLUSTER,
            "figura_backtest": figura_para_json(
                gm.grafico_backtest(nsm["backtest_mensal"], cap, altura=380))}


def figura_para_json(fig):
    if fig is None:
        return None
    return {"data": json.loads(pio.to_json(fig))["data"],
            "layout": json.loads(pio.to_json(fig))["layout"]}


def monta_html(rotas: list[str], figuras: dict, kpis: dict, plotly_js: str,
               rodape: str, lista: dict, nota_lista: str, cap: int, cap_tel: int) -> str:
    dados_js = json.dumps({"figuras": figuras, "kpis": kpis, "lista": lista},
                          ensure_ascii=False, separators=(",", ":"))
    opcoes = "\n".join(f'<option value="{r}">{r}</option>' for r in rotas)
    perfis = "".join(f"<div><dt>{c} · {gm.NOMES_CLUSTER[c]}</dt><dd>{texto}</dd></div>"
                     for c, texto in gm.DESCRICAO_CLUSTER.items())
    return TEMPLATE.format(plotly_js=plotly_js, opcoes=opcoes, dados=dados_js,
                           rodape=rodape, nota_lista=nota_lista, cap=cap, cap_tel=cap_tel,
                           perfis=perfis)


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carteira Polo Parnaíba</title>
<script>{plotly_js}</script>
<style>
  :root {{
    --superficie: #fcfcfb; --plano: #f4f4f1; --tinta: #0b0b0b; --secundaria: #52514e;
    --suave: #898781; --grade: #e1e0d9; --eixo: #c3c2b7;
    --sobe: #006300; --cai: #d03b3b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--plano); color: var(--tinta);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 14px;
  }}
  .pagina {{ max-width: 1640px; margin: 0 auto; padding: 24px 20px 56px; }}
  header {{ margin-bottom: 18px; }}
  h1 {{ font-size: 22px; margin: 0 0 2px; }}
  .sub {{ color: var(--secundaria); font-size: 13px; margin: 0; }}
  .controles {{
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    /* acompanha a rolagem: trocar de rota nao exige voltar ao topo */
    position: sticky; top: 0; z-index: 20; margin: 16px -20px 18px;
    padding: 12px 20px; background: var(--plano);
    border-bottom: 1px solid var(--grade);
  }}
  .controles label {{ color: var(--secundaria); font-size: 13px; }}
  select {{
    font: inherit; padding: 7px 12px; border: 1px solid var(--eixo); border-radius: 8px;
    background: var(--superficie); color: var(--tinta); min-width: 240px;
  }}
  .kpis {{ display: grid; grid-template-columns: 1.05fr 1fr 1fr; gap: 14px; }}
  .painel {{
    background: var(--superficie); border: 1px solid var(--grade); border-radius: 12px;
    padding: 14px 16px 16px;
  }}
  .painel h2 {{
    font-size: 12px; text-transform: uppercase; letter-spacing: .05em;
    color: var(--suave); margin: 0 0 12px; font-weight: 600;
  }}
  .cartoes {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px 18px; }}
  .cartao .rotulo {{ color: var(--secundaria); font-size: 12px; }}
  .cartao .valor {{ font-size: 23px; font-weight: 700; line-height: 1.25; }}
  .cartao .nota {{ font-size: 12px; font-weight: 700; }}
  .cartao .nota span {{ font-weight: 400; color: var(--suave); }}
  .bloco {{ margin-top: 16px; }}
  .bloco.dividido {{ display: grid; grid-template-columns: 1fr 1.18fr; gap: 14px; }}
  .coluna {{ display: grid; gap: 14px; align-content: start; }}
  .coluna.centrada {{ align-content: center; }}
  .grafico {{
    background: var(--superficie); border: 1px solid var(--grade); border-radius: 12px;
    padding: 6px 8px;
  }}
  .vazio {{
    display: flex; align-items: center; justify-content: center; color: var(--suave);
    font-size: 13px; min-height: 220px; text-align: center; padding: 20px;
  }}
  footer {{ margin-top: 28px; color: var(--suave); font-size: 12px; line-height: 1.6; }}
  [hidden] {{ display: none !important; }}
  .abas {{ display: flex; gap: 4px; margin-top: 14px; border-bottom: 1px solid var(--grade); }}
  .aba {{
    font: inherit; font-weight: 600; color: var(--secundaria); background: none; border: 0;
    border-bottom: 3px solid transparent; padding: 9px 14px 8px; cursor: pointer;
  }}
  .aba:hover {{ color: var(--tinta); }}
  .aba[aria-selected="true"] {{ color: var(--tinta); border-bottom-color: #0f8a58; }}
  .aba:focus-visible, .botao:focus-visible, select:focus-visible {{
    outline: 2px solid #256abf; outline-offset: 2px;
  }}
  .so-lista {{ display: inline-flex; align-items: center; gap: 10px; flex-wrap: wrap;
               margin-left: auto; }}
  select.estreito {{ min-width: 0; }}
  .botao {{
    font: inherit; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--eixo);
    background: var(--superficie); color: var(--tinta); cursor: pointer;
  }}
  .botao:hover {{ background: var(--grade); }}
  .kpis-lista {{ grid-template-columns: 1fr; }}
  .cartoes.quatro {{ grid-template-columns: repeat(4, 1fr); }}
  .tabela-cabecalho {{ display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
                       margin-bottom: 6px; }}
  .tabela-cabecalho h2 {{ margin: 0; }}
  .rolagem {{ overflow-x: auto; }}
  table.lista {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  table.lista caption {{ text-align: left; color: var(--secundaria); font-size: 12px;
                         padding-bottom: 6px; }}
  table.lista th {{
    text-align: left; font-size: 11px; font-weight: 600; color: var(--secundaria);
    text-transform: uppercase; letter-spacing: .03em; padding: 8px 10px;
    border-bottom: 1px solid var(--eixo); vertical-align: bottom;
  }}
  table.lista td {{ padding: 7px 10px; border-bottom: 1px solid var(--grade); white-space: nowrap; }}
  table.lista .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  table.lista tbody tr:hover {{ background: var(--plano); }}
  .faixa {{
    display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .04em; padding: 1px 6px; border-radius: 6px; margin-left: 8px;
  }}
  .faixa.visita {{ background: #e3f1ea; color: #00522a; }}
  .faixa.telefone {{ background: #ecebe6; color: var(--secundaria); }}
  .risco {{ display: inline-flex; align-items: center; gap: 8px; }}
  .risco .trilho {{ width: 64px; height: 6px; background: var(--grade); border-radius: 3px;
                    overflow: hidden; }}
  .risco .barra {{ display: block; height: 100%; background: #d03b3b; border-radius: 3px; }}
  .resultado.saiu {{ color: #b52f2f; font-weight: 700; }}
  .resultado.ficou {{ color: #006300; font-weight: 600; }}
  .resultado.aguarda {{ color: var(--secundaria); }}
  dl.perfis {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px 22px; font-size: 12px;
    margin: 16px 0 4px; color: var(--secundaria);
  }}
  dl.perfis dt {{ font-weight: 700; color: var(--tinta); }}
  dl.perfis dd {{ margin: 0 0 6px; }}
  .nota-lista {{ color: var(--suave); font-size: 12px; line-height: 1.6; margin-top: 14px;
                 max-width: 1100px; }}
  @media (max-width: 1100px) {{
    .cartoes.quatro {{ grid-template-columns: repeat(2, 1fr); }}
    dl.perfis {{ grid-template-columns: 1fr; }}
    .so-lista {{ margin-left: 0; }}
  }}
  @media (max-width: 1100px) {{
    .kpis, .bloco.dividido {{ grid-template-columns: 1fr; }}
    .cartoes {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>
<div class="pagina">
  <header>
    <h1>Carteira Polo Parnaíba</h1>
    <p class="sub" id="legenda-periodo"></p>
  </header>

  <nav class="abas" role="tablist" aria-label="Seções do dashboard">
    <button class="aba" role="tab" aria-selected="true" aria-controls="aba-carteira"
            data-aba="carteira">Carteira</button>
    <button class="aba" role="tab" aria-selected="false" aria-controls="aba-lista"
            data-aba="lista">Lista de visitas</button>
  </nav>

  <div class="controles">
    <label for="rota">Rota</label>
    <select id="rota">{opcoes}</select>
    <span class="sub" id="legenda-rota"></span>
    <span class="so-lista" hidden>
      <label for="mes-lista">Lista para</label>
      <select id="mes-lista" class="estreito"></select>
      <label for="faixa-lista">Faixa</label>
      <select id="faixa-lista" class="estreito">
        <option value="{cap}">Visitas (posições 1 a {cap})</option>
        <option value="{cap_tel}">Visitas e telefone (1 a {cap_tel})</option>
      </select>
      <button type="button" id="exportar" class="botao">Exportar CSV</button>
    </span>
  </div>

  <div id="aba-carteira" role="tabpanel">
  <section class="kpis">
    <div class="painel"><h2 id="titulo-carteira">Carteira</h2>
      <div class="cartoes" id="kpi-carteira"></div></div>
    <div class="painel"><h2 id="titulo-tpv">TPV do mês</h2>
      <div class="cartoes" id="kpi-tpv"></div></div>
    <div class="painel"><h2 id="titulo-media">Ticket médio por cliente</h2>
      <div class="cartoes" id="kpi-media"></div></div>
  </section>

  <div class="bloco"><div class="grafico" id="base_ativa"></div></div>

  <div class="bloco dividido">
    <div class="coluna">
      <div class="grafico" id="novos_ativos"></div>
      <div class="grafico" id="reativacoes"></div>
      <div class="grafico" id="churn"></div>
    </div>
    <div class="coluna centrada"><div class="grafico" id="ponte_semestral"></div></div>
  </div>

  <div class="bloco"><div class="grafico" id="ponte_mensal"></div></div>

  <div class="bloco"><div class="grafico" id="tpv_total"></div></div>

  <div class="bloco dividido">
    <div class="coluna">
      <div class="grafico" id="tpv_medio"></div>
      <div class="grafico" id="tpv_na_m1"></div>
      <div class="grafico" id="perda_churn"></div>
    </div>
    <div class="coluna centrada"><div class="grafico" id="ponte_tpv"></div></div>
  </div>
  </div>

  <div id="aba-lista" role="tabpanel" hidden>
    <section class="kpis kpis-lista">
      <div class="painel"><h2 id="titulo-lista">Lista de visitas</h2>
        <div class="cartoes quatro" id="kpi-lista"></div></div>
    </section>

    <div class="bloco painel">
      <div class="tabela-cabecalho">
        <h2 id="titulo-tabela">Clientes</h2>
        <span class="sub" id="legenda-tabela"></span>
      </div>
      <div class="rolagem">
        <table class="lista">
          <caption>Clientes ordenados pelo risco de zerar o TPV no mês seguinte.</caption>
          <thead><tr>
            <th class="num">Posição</th><th>Cliente</th><th>Rota</th><th>Perfil</th>
            <th class="num">Risco</th><th class="num">TPV do mês</th>
            <th class="num">TPV médio<br>3 meses</th><th class="num">Dias sem venda<br>no fim do mês</th>
            <th class="num">Maior hiato<br>(dias)</th><th class="num">Dias com venda<br>última semana</th>
            <th class="num">Meses desde<br>a ativação</th><th>Situação<br>no mês</th>
            <th>Resultado no<br>mês seguinte</th>
          </tr></thead>
          <tbody id="corpo-lista"></tbody>
        </table>
      </div>
      <dl class="perfis">{perfis}</dl>
    </div>

    <div class="bloco"><div class="grafico" id="backtest"></div></div>
    <p class="nota-lista">{nota_lista}</p>
  </div>

  <footer>{rodape}</footer>
</div>

<script>
const PAINEL = {dados};
const GRAFICOS = ["base_ativa","novos_ativos","reativacoes","churn","ponte_semestral",
                  "ponte_mensal","tpv_total","tpv_medio","tpv_na_m1","perda_churn",
                  "ponte_tpv"];
const CONFIG = {{responsive: true, displayModeBar: false, locale: "pt-br"}};

const formatador = new Intl.NumberFormat("pt-BR");
const umaCasa = new Intl.NumberFormat("pt-BR", {{minimumFractionDigits: 1,
                                                maximumFractionDigits: 1}});
function numero(valor, formato) {{
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "–";
  if (formato === "milhoes") {{
    // abaixo de um milhao o valor vai em milhares, para nao virar "0,1MM"
    if (Math.abs(valor) < 1e6) {{
      return "R$ " + formatador.format(Math.round(valor / 1e3)) + "k";
    }}
    return "R$ " + umaCasa.format(valor / 1e6) + "MM";
  }}
  return formatador.format(Math.round(valor));
}}

function nota(item) {{
  if (item.nota === null || item.nota === undefined) return '<div class="nota">&nbsp;</div>';
  const sinal = item.nota >= 0 ? "+" : "−";
  const texto = formatador.format(Math.abs(Math.round(item.nota * 10) / 10));
  // a cor segue o RESULTADO: em churn e perda de TPV, cair e bom
  const bom = (item.alta_e_boa === false) ? item.nota <= 0 : item.nota >= 0;
  const cor = item.nota_tipo === "variacao"
    ? (bom ? "var(--sobe)" : "var(--cai)") : "var(--secundaria)";
  const prefixo = item.nota_tipo === "variacao" ? sinal : "";
  return `<div class="nota" style="color:${{cor}}">${{prefixo}}${{texto}}%` +
         ` <span>${{item.nota_rotulo}}</span></div>`;
}}

function cartoes(destino, itens) {{
  document.getElementById(destino).innerHTML = itens.map(item => `
    <div class="cartao">
      <div class="rotulo">${{item.rotulo}}</div>
      <div class="valor">${{numero(item.valor, item.formato)}}</div>
      ${{nota(item)}}
    </div>`).join("");
}}

function desenha(rota) {{
  const kpi = PAINEL.kpis[rota];
  document.getElementById("legenda-periodo").textContent =
    `Mês de referência ${{kpi.mes}} · janela ${{kpi.janela}}`;
  document.getElementById("legenda-rota").textContent =
    `${{formatador.format(kpi.documentos)}} documentos na rota`;
  document.getElementById("titulo-carteira").textContent = `Carteira · ${{kpi.mes}}`;
  document.getElementById("titulo-tpv").textContent = `TPV · ${{kpi.mes}}`;
  document.getElementById("titulo-media").textContent =
    `Ticket médio por cliente · ${{kpi.mes}}`;
  cartoes("kpi-carteira", kpi.carteira);
  cartoes("kpi-tpv", kpi.tpv_mes);
  cartoes("kpi-media", kpi.tpv_medio);

  GRAFICOS.forEach(id => {{
    const alvo = document.getElementById(id);
    const fig = PAINEL.figuras[rota][id];
    if (!fig) {{
      alvo.innerHTML = '<div class="vazio">Sem dados suficientes nesta rota ' +
                       'para montar este gráfico.</div>';
      return;
    }}
    if (alvo.firstChild && alvo.firstChild.className !== "vazio") {{
      Plotly.react(alvo, fig.data, fig.layout, CONFIG);
    }} else {{
      alvo.innerHTML = "";
      Plotly.newPlot(alvo, fig.data, fig.layout, CONFIG);
    }}
  }});
}}

const seletor = document.getElementById("rota");

// ---- aba Lista de visitas ------------------------------------------------------
const LISTA = PAINEL.lista;
const selMes = document.getElementById("mes-lista");
const selFaixa = document.getElementById("faixa-lista");
const vazio = v => v === null || v === undefined || Number.isNaN(v);
const pct1 = v => vazio(v) ? "–" : umaCasa.format(v * 100) + "%";
const reais = v => vazio(v) ? "–" : "R$ " + formatador.format(Math.round(v));
const inteiro = v => vazio(v) ? "–" : formatador.format(Math.round(v));
let abaAtual = "carteira";
let backtestDesenhado = false;

LISTA.meses.forEach(m => {{
  const opcao = document.createElement("option");
  opcao.value = m.base;
  opcao.textContent = m.rotulo;
  selMes.appendChild(opcao);
}});

function linhasLista() {{
  const rota = seletor.value, cap = Number(selFaixa.value);
  return LISTA.linhas.filter(l => l.mes_base === selMes.value && l.posicao <= cap &&
                                  (rota === "Todas as rotas" || l.rota === rota));
}}

function situacao(l) {{
  if (l.novo_ativo) return "Novo ativo";
  if (l.reativacao) return "Reativação";
  return "Recorrente";
}}

function resultado(l) {{
  if (l.churn_realizado === null) return '<span class="resultado aguarda">Aguardando</span>';
  return l.churn_realizado === 1 ? '<span class="resultado saiu">Saiu</span>'
                                 : '<span class="resultado ficou">Ficou</span>';
}}

function desenhaLista() {{
  const rota = seletor.value, cap = Number(selFaixa.value);
  const mes = LISTA.meses.find(m => m.base === selMes.value);
  const resumo = LISTA.backtest[selMes.value];
  const linhas = linhasLista();
  const esperados = linhas.reduce((soma, l) => soma + l.risco, 0);
  const avaliadas = linhas.filter(l => l.churn_realizado !== null);
  const sairam = avaliadas.filter(l => l.churn_realizado === 1).length;
  const riscos = linhas.map(l => l.risco).sort((a, b) => a - b);
  const mediana = riscos.length ? riscos[Math.floor((riscos.length - 1) / 2)] : null;

  document.getElementById("titulo-lista").textContent =
    `Lista de visitas · ${{mes.lista_rotulo}} · base ${{mes.base_rotulo}}`;
  const cartoesLista = [
    {{rotulo: "Clientes na lista", valor: formatador.format(linhas.length),
      nota: rota === "Todas as rotas" ? `posições 1 a ${{cap}} da carteira`
                                      : `entre as posições 1 a ${{cap}}, nesta rota`}},
    {{rotulo: "Churns esperados", valor: umaCasa.format(esperados),
      nota: "soma das probabilidades de churn"}},
    {{rotulo: "Risco mediano na lista", valor: pct1(mediana),
      nota: `na carteira ativa: ${{pct1(resumo.risco_mediano_ativos)}}`}},
  ];
  if (!avaliadas.length) {{
    cartoesLista.push({{rotulo: `Resultado em ${{mes.lista_rotulo}}`, valor: "Aguardando",
                        nota: "a carteira do mês ainda não fechou"}});
  }} else {{
    const precisao = sairam / avaliadas.length;
    const recall = resumo["recall@" + cap];
    const semResultado = linhas.length - avaliadas.length;
    const nota = ((rota === "Todas as rotas" && !vazio(recall))
      ? `precisão ${{pct1(precisao)}} · ${{pct1(recall)}} dos ${{inteiro(resumo.churns_realizados)}} churns da carteira`
      : `precisão ${{pct1(precisao)}} nesta rota`) +
      (semResultado ? ` · ${{semResultado}} sem resultado (fora da carteira seguinte)` : "");
    cartoesLista.push({{rotulo: `Saíram em ${{mes.lista_rotulo}}`, valor: formatador.format(sairam), nota}});
  }}
  document.getElementById("kpi-lista").innerHTML = cartoesLista.map(c => `
    <div class="cartao">
      <div class="rotulo">${{c.rotulo}}</div>
      <div class="valor">${{c.valor}}</div>
      <div class="nota"><span>${{c.nota}}</span></div>
    </div>`).join("");

  document.getElementById("titulo-tabela").textContent =
    `${{formatador.format(linhas.length)}} clientes`;
  document.getElementById("legenda-tabela").textContent =
    (rota === "Todas as rotas" ? "Carteira inteira." : `Rota ${{rota}}.`) +
    " A posição é o ranking de risco da carteira inteira.";

  document.getElementById("corpo-lista").innerHTML = linhas.map(l => {{
    const visita = l.posicao <= LISTA.capacidade;
    return `<tr>
      <td class="num">${{l.posicao}}<span class="faixa ${{visita ? "visita" : "telefone"}}">${{visita ? "visita" : "telefone"}}</span></td>
      <td>${{l.cliente}}</td>
      <td>${{l.rota}}</td>
      <td title="${{LISTA.perfis[l.cluster] || ""}}">${{l.cluster}} · ${{LISTA.nomes_perfis[l.cluster] || ""}}</td>
      <td class="num"><span class="risco">${{pct1(l.risco)}}<span class="trilho"><span class="barra" style="width:${{Math.round(l.risco * 100)}}%"></span></span></span></td>
      <td class="num">${{reais(l.tpv_mes)}}</td>
      <td class="num">${{reais(l.tpv_medio_3m)}}</td>
      <td class="num">${{inteiro(l.dias_sem_venda)}}</td>
      <td class="num">${{inteiro(l.maior_hiato)}}</td>
      <td class="num">${{inteiro(l.dias_ativos_ult7)}}</td>
      <td class="num">${{inteiro(l.meses_ativacao)}}</td>
      <td>${{situacao(l)}}</td>
      <td>${{resultado(l)}}</td>
    </tr>`;
  }}).join("");
}}

function exportaCsv() {{
  const mes = LISTA.meses.find(m => m.base === selMes.value);
  const decimal = v => vazio(v) ? "" : String(Math.round(v * 100) / 100).replace(".", ",");
  const cabecalho = ["posicao", "faixa", "cliente", "rota", "perfil", "risco_pct", "tpv_mes",
                     "tpv_medio_3m", "dias_sem_venda_fim_mes", "maior_hiato",
                     "dias_com_venda_ult7", "meses_desde_ativacao", "situacao", "resultado"];
  const corpo = linhasLista().map(l => [
    l.posicao, l.posicao <= LISTA.capacidade ? "visita" : "telefone", l.cliente, l.rota,
    `${{l.cluster}} ${{LISTA.nomes_perfis[l.cluster]}}`, decimal(l.risco * 100), decimal(l.tpv_mes),
    decimal(l.tpv_medio_3m), decimal(l.dias_sem_venda), decimal(l.maior_hiato),
    decimal(l.dias_ativos_ult7), decimal(l.meses_ativacao), situacao(l),
    l.churn_realizado === null ? "" : (l.churn_realizado === 1 ? "saiu" : "ficou")]);
  const csv = "\\ufeff" + [cabecalho, ...corpo]
    .map(linha => linha.map(c => `"${{String(c).split('"').join('""')}}"`).join(";"))
    .join("\\r\\n");
  const url = URL.createObjectURL(new Blob([csv], {{type: "text/csv;charset=utf-8"}}));
  const link = document.createElement("a");
  link.href = url;
  link.download = `lista_visitas_${{mes.lista}}_${{seletor.value.split(" ").join("_")}}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}}

function mostraAba(aba) {{
  abaAtual = aba;
  document.getElementById("aba-carteira").hidden = aba !== "carteira";
  document.getElementById("aba-lista").hidden = aba !== "lista";
  document.querySelector(".so-lista").hidden = aba !== "lista";
  document.querySelectorAll(".aba").forEach(botao =>
    botao.setAttribute("aria-selected", String(botao.dataset.aba === aba)));
  if (aba === "lista") {{
    desenhaLista();
    const alvo = document.getElementById("backtest");
    if (!backtestDesenhado) {{
      Plotly.newPlot(alvo, LISTA.figura_backtest.data, LISTA.figura_backtest.layout, CONFIG);
      backtestDesenhado = true;
    }} else {{
      Plotly.Plots.resize(alvo);
    }}
  }} else {{
    // graficos redesenhados enquanto a aba estava oculta precisam da largura real
    GRAFICOS.forEach(id => {{
      const alvo = document.getElementById(id);
      if (alvo && alvo.data) Plotly.Plots.resize(alvo);
    }});
  }}
}}

document.querySelectorAll(".aba").forEach(botao =>
  botao.addEventListener("click", () => mostraAba(botao.dataset.aba)));
seletor.addEventListener("change", () => {{
  desenha(seletor.value);
  if (abaAtual === "lista") desenhaLista();
}});
selMes.addEventListener("change", desenhaLista);
selFaixa.addEventListener("change", desenhaLista);
document.getElementById("exportar").addEventListener("click", exportaCsv);
desenha(seletor.value);
// link direto para a aba: dashboard_carteira.html#lista
if (location.hash === "#lista") mostraAba("lista");
</script>
</body>
</html>
"""


# =============================================================================
# 5. Execucao
# =============================================================================
def main() -> None:
    print("Executando as celulas do notebook...")
    ns = carrega_notebook()
    df = ns["df"]

    contagem = (df.drop_duplicates("Documento")["Rota_atual"].value_counts())
    rotas = ["Todas as rotas"] + [r for r, n in contagem.items()
                                  if n >= MIN_DOCUMENTOS_ROTA]
    descartadas = [r for r, n in contagem.items() if n < MIN_DOCUMENTOS_ROTA]

    figuras, kpis = {}, {}
    for rota in rotas:
        recorte = df if rota == "Todas as rotas" else df[df["Rota_atual"] == rota]
        FALHAS.clear()
        figuras[rota] = {nome: figura_para_json(fig)
                         for nome, fig in constroi_figuras(ns, recorte).items()}
        kpis[rota] = calcula_kpis(ns, recorte)
        aviso = f"  falhas: {FALHAS}" if FALHAS else ""
        print(f"  {rota:<22} {recorte['Documento'].nunique():>5} documentos"
              f"   {len(figuras[rota]) - len(FALHAS)}/{len(figuras[rota])} gráficos{aviso}")

    print("\nExecutando o notebook do modelo (inclui o backtest mensal das listas)...")
    ns_modelo = carrega_modelo()
    lista = dados_lista(ns_modelo)
    print(f"  {len(lista['meses'])} listas mensais, {len(lista['linhas']):,} linhas")

    from plotly.offline import get_plotlyjs
    rodape = (
        "Base do Polo Franquia de Parnaíba. "
        f"Período de {df['periodo'].min()} a {df['periodo'].max()}. "
        "Base ativa é o cliente com TPV Total maior que zero no mês; TPV Total soma "
        "adquirência e PIX QR Code de clientes com equipamento instalado.<br>"
        "Novos ativos, reativações e churn seguem as regras de fluxo do projeto e "
        "começam em abr/2024, quando existem três meses de histórico. "
        f"Rotas com menos de {MIN_DOCUMENTOS_ROTA} documentos ficam fora do seletor"
        + (f" ({', '.join(descartadas)})." if descartadas else ".") +
        "<br>Gerado por build_dashboard.py a partir de base_dashboard.ipynb e "
        "modelo_churn.ipynb.")

    SAIDA.write_text(monta_html(rotas, figuras, kpis, get_plotlyjs(), rodape, lista,
                                NOTA_LISTA, ns_modelo["CAPACIDADE"],
                                ns_modelo["CAPACIDADE_TELEFONE"]),
                     encoding="utf-8")
    tamanho = SAIDA.stat().st_size / 1024**2
    print(f"\n{SAIDA} gerado: {tamanho:,.1f} MB, {len(rotas)} rotas, "
          f"{len(GRAFICOS_NA_PAGINA)} gráficos por rota, aba de lista com "
          f"{len(lista['meses'])} meses")


if __name__ == "__main__":
    main()
