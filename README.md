# Radar de Churn — protótipo

Dois protótipos do mesmo produto de dados: Top 10 clientes ativos com maior
risco de churn no próximo mês, card com informações do cliente, gráficos que
atualizam ao passar o mouse/clicar, e botão para preparar o e-mail de contato
ativo para o vendedor.

## 1. Gerar os dados (rodar sempre que a base mudar)

```
python build_churn_data.py
```

Lê `../../base_edited.parquet`, calcula o score de risco provisório e escreve
`clientes_risco.json`, consumido pelos dois protótipos abaixo.

**Importante**: `risk_score` é uma regra provisória (não é o modelo de ML),
documentada no topo de `build_churn_data.py`. Quando o modelo treinado com
`flag_churn` estiver pronto, troque `compute_risk_score` pela saída do modelo
— o resto do pipeline (JSON, dashboards) não muda.

## 2. Protótipo A — Streamlit (interatividade real, precisa de servidor)

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Clique/passe o mouse no gráfico de ranking ou selecione uma linha na tabela
para atualizar o card do cliente. O formulário de e-mail gera um link
`mailto:` pré-preenchido (não envia sozinho — abre o cliente de e-mail do
vendedor). Para envio automático real, seria necessário integrar com a
API/SMTP de e-mail da empresa.

## 3. Protótipo B — Quarto + Plotly (HTML estático, mesmo padrão do dashboard atual)

```
quarto render clientes_risco.qmd
```

Gera `clientes_risco.html`, autocontido (inclui `plotly.min.js` local, sem
depender de internet). Passe o mouse ou clique nas barras do ranking para
atualizar o card, o gráfico de TPV e o botão de e-mail ao lado — tudo via
JavaScript, sem precisar de servidor rodando.

## Dados de contato

A base já está anonimizada (Documento, Nome_fantasia e Vendedor viram
`cnpj_/cpf_NNN`, `cliente_NNN`, `colaborador_NNN`) e não tem telefone/e-mail
reais do cliente nem do vendedor. Por isso o campo de e-mail do vendedor é
digitado manualmente no protótipo — em produção, viria do CRM.
