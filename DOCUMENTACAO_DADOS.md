# Documentação — pipeline de dados do dashboard

Este documento explica de onde vêm os números e gráficos do dashboard
Streamlit: o que é calculado nos notebooks originais do `projeto_churn-main`,
como isso chega em `painel_carteira.json`, e como adaptar se a base mudar.

## 1. Visão geral

```
pipeline/data/raw/base.parquet
        │
        ▼
pipeline/notebooks/base_dashboard.ipynb   (tratamento da base + gráficos da carteira)
        │
        ▼
pipeline/notebooks/modelo_churn.ipynb     (features, modelo, backtest walk-forward, listas)
        │
        ▼
pipeline/gerar_painel_json.py             (roda os dois notebooks de verdade via nbformat,
        │                                   NÃO lê nenhum HTML pronto)
        ▼
painel_carteira.json                      (figuras Plotly + KPIs + lista, já prontos)
        │
        ▼
streamlit_app.py                          (só lê o JSON e desenha)
```

`gerar_painel_json.py` reaproveita as funções do `pipeline/src/build_dashboard.py`
original do projeto (`carrega_notebook`, `carrega_modelo`, `constroi_figuras`,
`calcula_kpis`, `dados_lista`) — são as mesmas usadas para gerar o
`dashboard_carteira.html` do projeto original, só que aqui o resultado vira
JSON em vez de virar uma página HTML. **O app Streamlit nunca leu, nem lê, o
HTML gerado** — os dados vêm de rodar o pipeline (notebooks) de novo, por
conta própria.

Rodar o pipeline (demora ~2-3 min, majoritariamente o treino do backtest):

```bash
pip install -r pipeline/requirements.txt
python pipeline/gerar_painel_json.py
```

## 2. O que `base_dashboard.ipynb` calcula (aba "Carteira")

Fonte: `pipeline/data/raw/base.parquet` (uma linha por mês × Stonecode).

- **Célula `consolida`**: várias linhas de Stonecode de um mesmo Documento no
  mesmo mês viram uma linha por (mês, Documento) — métricas somadas, flags
  por `max`, campos categóricos herdados do Stonecode "principal" (o que não
  é cadastro acessório tipo Link ABC/WhatsAppPay/Tap On Phone, priorizando
  quem está ativo e tem mais TPV). Descarta colunas descontinuadas (que
  pararam de ser alimentadas em algum mês, ex. `Receita_GDA` zerada desde
  jan/2026).
- **Célula `features`**: deriva `TPV Total` (adquirência + PIX QR Code
  validado, descartando PIX sem equipamento instalado), `status_movimento`
  (Novo Ativo / Reativação / Churn / Ativo recorrente / Sem transação) e as
  flags `flag_novo_ativo`, `flag_reativacao`, `flag_churn` a partir da
  sequência de TPV mês a mês de cada cliente, além de `Rota_atual` (a rota
  mais recente de cada Documento, aplicada retroativamente ao histórico
  inteiro — por isso um cliente aparece sempre na mesma rota, mesmo em meses
  antigos onde a malha de rotas era outra).
- **Células `grafico_*`**: cada uma define as funções que montam um gráfico
  específico (`matriz_ano_mes`, `grafico_colunas_ano`, `grafico_ponte_*`
  etc.) — é aqui que fica a lógica visual (cores, pontes/waterfall, taxas).
  `build_dashboard.py` (e agora `gerar_painel_json.py`) chama essas funções
  para cada rota, pré-computando os 11 gráficos da aba Carteira.

## 3. O que `modelo_churn.ipynb` calcula (aba "Lista de visitas")

- **Alvo (célula `alvo`)**: para cada cliente ativo no fechamento do mês `t`,
  `alvo_churn_m1 = 1` se o TPV Total dele zerar em `t+1`. O modelo nunca vê o
  próprio mês do churn (nele o TPV já é zero e entregaria a resposta) — só
  enxerga o comportamento ANTES da saída.
- **Features (`features_diarias`, `features_derivadas`)**: 33 variáveis,
  incluindo `dias_sem_transacao_fim_mes`, `maior_hiato_sem_transacao`,
  `dias_ativos_ultimos_7`, `tempo_ativacao_meses`, `razao_tpv_m0_media_m1_m3`,
  segmento (MCC agrupado), canal de venda, modalidade de antecipação, entre
  outras — lista completa e descrição de cada uma em
  `pipeline/src/graficos_modelo.py` (dicionário `DESCRICAO_FEATURES`).
- **Modelo (célula `modelos`)**: `sklearn.ensemble.HistGradientBoostingClassifier`
  (gradient boosting), comparado contra uma regra simples (dias sem venda no
  fim do mês) e uma regressão logística. Parâmetros fixos com
  `random_state=0` — determinístico, sempre reproduz os mesmos números para
  a mesma base.
- **Clusters (célula `clusters`)**: 6 perfis de cliente (K-means ou similar
  sobre os ativos de 2025, aplicado a 2026 sem reajuste) — nomes e descrições
  em `graficos_modelo.NOMES_CLUSTER` / `DESCRICAO_CLUSTER`.
- **Lista do mês corrente (célula `lista_risco`)**: escora os clientes ativos
  no último mês da base e ranqueia pelo risco previsto.
- **Backtest walk-forward (célula `historico_listas`)**: para cada mês-base
  de jul/2025 até o mês mais recente, treina um modelo NOVO só com dados até
  aquele mês, escora os ativos daquele mês, e compara com o churn
  efetivamente realizado no mês seguinte. Isso gera 13+ modelos treinados —
  é a parte lenta do pipeline (~2 min) — e é o que alimenta a tabela e o
  gráfico de recall da aba "Lista de visitas".

## 4. Schema de `painel_carteira.json`

```jsonc
{
  "figuras": {
    "<nome da rota>": {
      "<nome do gráfico>": {"data": [...], "layout": {...}}  // objeto Plotly puro
    }
  },
  "kpis": {
    "<nome da rota>": {
      "documentos": 7076, "mes": "Jul/2026", "janela": "Jan-Jul",
      "carteira": [{"rotulo", "valor", "formato", "nota", "nota_tipo", "nota_rotulo", "alta_e_boa"?}, ...],
      "tpv_mes": [...], "tpv_medio": [...]
    }
  },
  "lista": {
    "linhas": [{"mes_base", "posicao", "cliente", "rota", "cluster", "risco",
                "tpv_mes", "tpv_medio_3m", "dias_sem_venda", "maior_hiato",
                "dias_ativos_ult7", "meses_ativacao", "novo_ativo",
                "reativacao", "churn_realizado"}, ...],
    "meses": [{"base", "lista", "base_rotulo", "lista_rotulo", "rotulo"}, ...],
    "backtest": {"<mes_base>": {"risco_mediano_ativos", "churns_realizados",
                                 "recall@120", "recall@200"}},
    "capacidade": 120, "capacidade_telefone": 200,
    "nomes_perfis": {"C1": "Reativados", ...}, "perfis": {"C1": "...", ...},
    "figura_backtest": {"data": [...], "layout": {...}}
  }
}
```

`streamlit_app.py` só depende **desse schema**. Enquanto
`gerar_painel_json.py` continuar produzindo essas mesmas chaves, o app não
precisa mudar em nada.

## 5. Como adaptar se a base mudar

- **Base com colunas novas/renomeadas/removidas**: o tratamento e as regras
  de negócio ficam inteiramente dentro de `pipeline/notebooks/*.ipynb` — é lá
  que se ajusta, não em `gerar_painel_json.py` nem em `streamlit_app.py`.
  Abra os notebooks (Jupyter/VS Code, com o kernel do projeto) e ajuste as
  células que referenciam a coluna afetada (busque o nome da coluna dentro
  do `.ipynb`).
- **Depois de editar os notebooks**: rode `python pipeline/gerar_painel_json.py`
  de novo. Se o schema do JSON (seção 4) não mudar, `streamlit_app.py`
  continua funcionando sem alteração nenhuma.
- **Se um gráfico novo for adicionado no notebook**: adicione o nome dele em
  `GRAFICOS_NA_PAGINA`/`constroi_figuras` (`pipeline/src/build_dashboard.py`)
  e depois chame `plot(figs["nome_novo"])` em `streamlit_app.py`, no bloco da
  aba Carteira.
- **Se o schema da lista mudar** (novo campo por cliente): adicione a chave
  em `dados_lista()` (`pipeline/src/build_dashboard.py`) e depois use
  `l["novo_campo"]` onde for preciso em `streamlit_app.py` (tabela, CSV, ou
  aba E-mail).

## 6. Limitações conhecidas

- **Dados de contato**: a base já vem anonimizada (Documento pseudonimizado,
  ex. `cnpj_2019`) e não tem telefone/e-mail reais — por isso o e-mail do
  vendedor é digitado manualmente na aba E-mail, não vem preenchido.
- **`painel_carteira.json` é um snapshot**: reflete a base no momento em que
  `gerar_painel_json.py` rodou. Rode de novo sempre que
  `pipeline/data/raw/base.parquet` for atualizado — o app não recalcula nada
  sozinho, só lê o JSON.
- **Backtest não é ao vivo no app**: o treino walk-forward (13+ modelos) só
  roda quando você chama `gerar_painel_json.py` manualmente — não a cada
  acesso ao dashboard. Isso é proposital (evita 2-3 min de espera por
  usuário e a dependência de `lightgbm`/`scikit-learn` no servidor do app),
  mas significa que o backtest exibido pode estar um pouco desatualizado em
  relação à base mais recente até alguém rodar o script de novo.
