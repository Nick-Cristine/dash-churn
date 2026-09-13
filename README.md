# Radar de Churn — protótipo (Streamlit)

Dashboard interativo: Top 10 clientes ativos com maior risco de churn no
próximo mês, com filtros por nome/TPV/score, card de detalhes que atualiza ao
passar o mouse ou clicar em um cliente, e um botão para preparar o e-mail de
contato ativo para o vendedor responsável.

Veja [DOCUMENTACAO_DADOS.md](DOCUMENTACAO_DADOS.md) para o detalhe completo de
como os dados são calculados/manipulados, o mapa de colunas da base usadas, e
como trocar o score provisório pelo modelo de ML quando ele estiver pronto.

## 1. Gerar os dados (rodar sempre que a base mudar)

```bash
python build_churn_data.py
```

Lê `../../base_edited.parquet`, calcula o score de risco provisório e escreve
`clientes_risco.json`, consumido pelo app.

**Importante**: `risk_score` é uma regra provisória (não é o modelo de ML),
documentada em `DOCUMENTACAO_DADOS.md`. Quando o modelo treinado com
`flag_churn` estiver pronto, troque `compute_risk_score` pela saída do modelo
— o resto do pipeline (JSON, app) não muda.

## 2. Rodar localmente

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Passe o mouse ou clique numa barra do gráfico de ranking (ou selecione uma
  linha na tabela) para ver os detalhes do cliente — sem seleção, o card fica
  com "—".
- Use os filtros de nome, TPV e score de risco para restringir o Top 10
  exibido.
- No card, "Preparar e-mail para o vendedor" gera um link `mailto:`
  pré-preenchido (não envia sozinho — abre o cliente de e-mail do vendedor).
  Para envio automático real, seria necessário integrar com a API/SMTP de
  e-mail da empresa.

## 3. Deploy (link compartilhável)

Via [Streamlit Community Cloud](https://share.streamlit.io):

1. Repositório já está no GitHub (privado, recomendado, já que os dados vêm
   de uma base interna anonimizada).
2. Em share.streamlit.io → **New app** → selecionar este repo/branch →
   arquivo principal `streamlit_app.py` → **Deploy**.
3. Se o repo não aparecer na lista, autorize o GitHub App do Streamlit em
   [github.com/settings/installations](https://github.com/settings/installations)
   → Streamlit → Configure → adicionar o repo.
4. Em "Sharing" nas configurações do app, restrinja quem pode ver por e-mail
   (dados internos, mesmo anonimizados).

## Dados de contato

A base já está anonimizada (Documento, Nome_fantasia e Vendedor viram
`cnpj_/cpf_NNN`, `cliente_NNN`, `colaborador_NNN`) e não tem telefone/e-mail
reais do cliente nem do vendedor. Por isso o campo de e-mail do vendedor é
digitado manualmente no app — em produção, viria do CRM.
