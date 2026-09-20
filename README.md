# Carteira Polo Parnaíba — dashboard (Streamlit)

Reproduz o dashboard da carteira do projeto `projeto_churn-main` (evolução da
base ativa, pontes de fluxo, TPV, e a lista de visitas gerada pelo modelo de
churn com backtest walk-forward), com uma aba a mais — **E-mail** — para
preparar o contato ativo com um cliente da lista.

Veja [DOCUMENTACAO_DADOS.md](DOCUMENTACAO_DADOS.md) para o detalhe de onde
vem cada número e como adaptar o pipeline se a base mudar de formato.

## Como os dados chegam no app

```
pipeline/notebooks/*.ipynb  →  pipeline/gerar_painel_json.py  →  painel_carteira.json  →  streamlit_app.py
   (base_dashboard,             (executa os notebooks de         (figuras + KPIs +
    modelo_churn)                 verdade, não lê HTML nenhum)     lista já prontos)
```

`pipeline/gerar_painel_json.py` executa os DOIS notebooks originais do
`projeto_churn-main` (`base_dashboard.ipynb` para a base tratada e os
gráficos da carteira, `modelo_churn.ipynb` para o modelo de gradient
boosting e o backtest walk-forward das listas de visita) e salva o
resultado — os mesmos objetos Python que os notebooks calculam — em
`painel_carteira.json`. O app Streamlit só lê esse JSON; ele nunca lê a base
`.parquet` nem os notebooks diretamente, e nunca dependeu de nenhum
`dashboard_carteira.html` pronto — só rodou o pipeline de verdade.

**Isso demora ~2-3 minutos** (o backtest walk-forward treina 13+ modelos, um
por mês), por isso é rodado uma vez, localmente, e não a cada acesso ao
dashboard — bem mais rápido que treinar tudo de novo a cada carregamento da
página, e sem precisar de `lightgbm`/`scikit-learn` no servidor do app.

## 1. Regenerar os dados (rodar sempre que a base mudar)

```bash
pip install -r pipeline/requirements.txt
python pipeline/gerar_painel_json.py
```

Lê `pipeline/data/raw/base.parquet` e sobrescreve `painel_carteira.json` na
raiz do projeto. Se a base bruta for atualizada, troque
`pipeline/data/raw/base.parquet` pela versão nova antes de rodar.

## 2. Rodar o dashboard localmente

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- **Carteira**: evolução da base ativa, novos ativos/reativações/churn,
  pontes de fluxo (semestral e mensal) e os gráficos de TPV — filtráveis por
  rota.
- **Lista de visitas**: ranking de risco de churn dos clientes ativos
  (modelo de gradient boosting), com filtro por mês, faixa de capacidade
  (visita/telefone) e rota, tabela detalhada, exportação em CSV e o gráfico
  de backtest do modelo.
- **E-mail** (não existe no dashboard original): usa a mesma lista filtrada
  na aba "Lista de visitas" — escolha um cliente no dropdown e gere o e-mail
  pro vendedor/dono do polo. Gera um link `mailto:` pré-preenchido (não
  envia sozinho — abre o cliente de e-mail). Para envio automático real,
  seria necessário integrar com a API/SMTP de e-mail da empresa.

## 3. Deploy (link compartilhável)

Via [Streamlit Community Cloud](https://share.streamlit.io):

1. Repositório já está no GitHub (privado, recomendado, já que os dados vêm
   de uma base interna anonimizada).
2. Em share.streamlit.io → **New app** → selecionar este repo/branch →
   arquivo principal `streamlit_app.py` → **Deploy**. O Community Cloud só
   instala o `requirements.txt` da raiz (pandas/plotly/streamlit) — os
   pacotes de `pipeline/requirements.txt` (lightgbm, scikit-learn, nbformat)
   não são necessários lá, já que `painel_carteira.json` já vem pronto no
   repo.
3. Se o repo não aparecer na lista, autorize o GitHub App do Streamlit em
   [github.com/settings/installations](https://github.com/settings/installations)
   → Streamlit → Configure → adicionar o repo.
4. Em "Sharing" nas configurações do app, restrinja quem pode ver por e-mail
   (dados internos, mesmo anonimizados).

## Dados de contato

A base já vem anonimizada (Documento pseudonimizado tipo `cnpj_2019`) e não
tem telefone/e-mail reais do cliente nem do vendedor. Por isso o campo de
e-mail do vendedor é digitado manualmente no app — em produção, viria do CRM.

## Estrutura do repositório

```
streamlit_app.py           app Streamlit (3 abas: Carteira, Lista de visitas, E-mail)
painel_carteira.json       dado pronto que o app lê (gerado pelo pipeline abaixo)
requirements.txt           dependências do app (deploy)
pipeline/
  gerar_painel_json.py     roda os notebooks e gera painel_carteira.json
  requirements.txt         dependências só do pipeline (nbformat, lightgbm, ...)
  src/                     código-fonte do projeto original (caminhos, gráficos, build_dashboard)
  notebooks/                base_dashboard.ipynb e modelo_churn.ipynb
  data/raw/base.parquet     base bruta de entrada
  data/processed/           saídas intermediárias do pipeline (cache do modelo)
  churn/models/              modelos treinados salvos (.joblib)
```
