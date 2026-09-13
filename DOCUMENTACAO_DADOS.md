# Documentação — pipeline de dados do Radar de Churn

Este documento explica, em detalhe, o que o script [`build_churn_data.py`](build_churn_data.py)
faz com a base `base_edited.parquet`: o que é lido, o que é calculado/manipulado,
e como o resultado (`clientes_risco.json`) alimenta os dois protótipos de
dashboard (Streamlit e Quarto/Plotly). O objetivo é que qualquer pessoa consiga
reproduzir, auditar ou adaptar o pipeline sem precisar reler o código linha a linha.

## 1. Visão geral

```
base_edited.parquet  →  build_churn_data.py  →  clientes_risco.json  →  streamlit_app.py
                                                                      →  clientes_risco.qmd
```

`build_churn_data.py` é a **única** peça do pipeline que toca na base bruta.
Os dois dashboards nunca leem o `.parquet` diretamente — eles só leem o JSON
já processado. Isso significa que qualquer ajuste em "o que é calculado" ou
"quais colunas existem na base" se resolve **em um único lugar**.

Rodar o pipeline:

```bash
python build_churn_data.py
```

Isso sobrescreve `clientes_risco.json`. É preciso rodar de novo sempre que a
base `.parquet` for atualizada (não há atualização automática).

## 2. Escopo dos dados (o que entra no cálculo)

1. Lê `base_edited.parquet` (176.514 linhas × 107 colunas na versão usada
   neste protótipo — uma linha por cliente por mês de referência).
2. Filtra para o **mês de referência mais recente** (`data_referencia.max()`)
   e remove duplicatas de `Documento` (`drop_duplicates`).
3. Dentro desse mês, filtra só os clientes com `status_ba_m0 == "Ativo"` —
   só faz sentido prever churn de quem ainda está ativo. No snapshot usado,
   isso reduziu 5.069 cadastros para **1.560 clientes ativos**.
4. Dentro desses 1.560, calcula o score de risco (seção 3) e pega os **10
   com maior score** (`TOP_N = 10` no topo do arquivo — dá pra mudar esse
   número livremente).

Nenhuma outra filtragem é aplicada (nenhum corte por cidade, segmento, etc.).

## 3. O que foi calculado (não veio pronto da base)

### 3.1 Score de risco provisório — `compute_risk_score()`

**Isto não é um modelo de Machine Learning.** É uma regra de negócio simples,
criada só para ter *algum* ranking e validar o dashboard enquanto o modelo de
verdade (treinado com a coluna `flag_churn`, que já existe na base) não fica
pronto. Fórmula:

```
score = 0.5 × percentil(dias_sem_transacionar) + 0.5 × percentil(queda_tpv_pct)
```

- **`dias_sem_transacionar`**: já vem pronta na base. Valores nulos são
  preenchidos com a mediana antes do cálculo (`fillna(median)`).
- **`queda_tpv_pct`**: **calculada**, não existe na base. É
  `(média(tpv_m1, tpv_m2, tpv_m3) - tpv_m0) / média(tpv_m1, tpv_m2, tpv_m3)`,
  limitada entre 0 e 1 (`clip`). Ou seja: o quanto o TPV do mês atual caiu em
  relação à média dos 3 meses anteriores. Quando a média dos 3 meses é 0 ou
  o cliente não tem TPV suficiente, o valor vira 0 (sem penalização).
- Os dois componentes são convertidos em **percentil** (`rank(pct=True)`,
  de 0 a 1) *dentro do grupo de clientes ativos* antes de somar — isso evita
  que a escala bruta de "dias sem transacionar" (0 a ~200) domine a escala de
  "queda percentual" (0 a 1).
- O resultado final é multiplicado por 100 e arredondado a 1 casa decimal
  (score de 0 a 100).

**Por que essas duas variáveis e esse peso 50/50**: são as duas variáveis
mais diretamente ligadas a churn iminente que já existiam prontas ou eram
fáceis de derivar, e o peso igual foi uma escolha arbitrária de bom senso
(não foi calibrado/validado contra `flag_churn`) — é exatamente por isso que
é "provisório".

### 3.2 Queda de TPV para exibição — `queda_pct` (dentro de `main()`)

É o mesmo cálculo do item anterior, mas **sem o `clip(0, 1)`** e já em
percentual (× 100), guardado por cliente no campo `queda_tpv_pct` do JSON —
usado só para mostrar no card ("Queda de TPV: +100.0%"), não entra de novo no
score.

### 3.3 TPV YTD (histórico mensal do ano) — `build_ytd_series()`

Não é um cálculo, é uma **reformatação**: filtra todas as linhas daquele
`Documento` no ano do mês de referência (`data_referencia.dt.year == ano`) e
monta uma lista `[{mes: "2026-01", tpv: 1234.5}, ...]` a partir da coluna
`tpv_m0` de cada linha mensal. É isso que vira o gráfico de linha "TPV mensal
(YTD)" nos dois dashboards.

### 3.4 Canais de venda já utilizados — `build_channel_info()`

**Correção de um problema real da coluna `canais_venda`**: ela não é uma
categoria simples — vem como string com múltiplos canais concatenados por
`"|"` (ex.: `"FRANQUIA|LINKABC|TAPONPHONE"`, um valor por linha/mês). Contar
os valores distintos da coluna diretamente superestima o número de canais
(cada combinação vira uma "categoria" separada). O que o script faz:

1. Pega todo o histórico daquele `Documento` (todas as linhas/meses).
2. Faz `.split("|")` em cada valor de `canais_venda` e junta tudo num `set`
   (união de canais individuais, sem repetição).
3. Retorna a lista ordenada + a contagem (`n_canais`).

Esse é o número que aparece como "Canais já utilizados (N)" no card.

### 3.5 Tempo de casa — `tenure_anos` (dentro de `main()`)

`(mês_de_referência - Data_credenciamento).days / 365`. Aproximação simples
em anos (não considera anos bissextos nem meses exatos).

### 3.6 Benchmark da carteira — `media_tpv_ativos_m0`

Média de `tpv_m0` entre **todos** os 1.560 clientes ativos (não só o Top 10).
Usado como linha de referência pontilhada no gráfico de TPV de cada cliente
("média da carteira ativa").

## 4. Colunas da base usadas (mapa de dependência)

Se qualquer uma destas colunas for renomeada, removida ou mudar de tipo numa
nova versão de `base_edited.parquet`, o `build_churn_data.py` provavelmente
vai quebrar (ou silenciosamente produzir números errados) nesse ponto
específico:

| Coluna na base               | Onde é usada                          | Para quê |
|-------------------------------|----------------------------------------|----------|
| `data_referencia`              | `load_base`, `main`                    | Identificar o mês mais recente e a série YTD |
| `Documento`                    | `main`, `build_ytd_series`, `build_channel_info` | Chave única do cliente |
| `Nome_fantasia`                | `main`                                 | Nome exibido |
| `status_ba_m0`                 | `main`                                 | Filtrar só clientes ativos |
| `dias_sem_transacionar`        | `compute_risk_score`, `main`           | Componente do score + exibição |
| `tpv_m0`, `tpv_m1`, `tpv_m2`, `tpv_m3` | `compute_risk_score`, `main`, `build_ytd_series` | Componente do score, queda %, série YTD |
| `Cidade`, `UF`                 | `main`                                 | Exibição |
| `Vendedor`                     | `main`                                 | Exibição + destinatário do e-mail |
| `mcc`                          | `main`                                 | Segmento exibido |
| `Rota_atual`                   | `main`                                 | Rota exibida (⚠️ é a coluna *derivada* `Rota_atual`, não `Rota` bruta — ver `Dicionario_Carteira_V2.md`) |
| `Tipo_contrato`                | `main`                                 | Exibição |
| `Cadastro_RAV`                 | `main`                                 | Exibição |
| `Data_credenciamento`          | `main`                                 | Tempo de casa |
| `qtd_stonecodes`, `qtd_stonecodes_ativos` | `main`                    | Exibição (hoje não aparecem nos dashboards, ficam só no JSON) |
| `canais_venda`                 | `build_channel_info`                   | Canais distintos usados (string `"A\|B\|C"`) |

## 5. Schema do `clientes_risco.json`

```jsonc
{
  "gerado_em": "2026-09-13 19:04",       // timestamp da geração
  "mes_referencia": "2026-07",
  "ano_ytd": 2026,
  "total_clientes_ativos": 1560,
  "media_tpv_ativos_m0": 28172.43,
  "metodologia": "texto explicando o score provisório",
  "clientes": [
    {
      "rank": 1,
      "documento": "cnpj_2891",
      "nome_fantasia": "cliente_6740",
      "risk_score": 99.9,
      "cidade": "PARNAIBA", "uf": "PI",
      "vendedor": "colaborador_237",
      "mcc": "Alimentação",
      "rota": "Parnaíba Centro",
      "tipo_contrato": null,
      "cadastro_rav": "Automatica",
      "dias_sem_transacionar": 85,
      "tempo_casa_anos": 0.2,
      "tpv_m0": 0.0, "tpv_m1": 1234.5, "tpv_m2": 980.0, "tpv_m3": 1500.0,
      "queda_tpv_pct": 100.0,
      "qtd_stonecodes": 1, "qtd_stonecodes_ativos": 0,
      "n_canais_historico": 1,
      "canais_historico": ["INBOUND"],
      "tpv_ytd": [{"mes": "2026-01", "tpv": 1200.0}, ...]
    },
    ...
  ]
}
```

Os dois dashboards (`streamlit_app.py` e `clientes_risco.qmd`) só dependem
**desse schema** — não da base original. Enquanto o JSON continuar com essas
mesmas chaves, os dashboards funcionam sem nenhuma alteração.

## 6. Como trocar a regra provisória pelo modelo de ML de verdade

Quando o modelo de churn (treinado com `flag_churn`) estiver pronto:

1. Abra `build_churn_data.py`.
2. Troque só o conteúdo da função `compute_risk_score(snap)`:
   - Hoje ela recebe o DataFrame dos clientes ativos do mês e devolve uma
     `pd.Series` de 0 a 100 (o score).
   - No lugar da regra, monte a mesma matriz de features `X` usada no
     treino do modelo (a partir das colunas de `snap`), rode
     `model.predict_proba(X)[:, 1]` (probabilidade de churn) e devolva
     `(prob * 100).round(1)` — mantendo o range 0–100 para não precisar
     mexer em mais nada.
3. **Não precisa mudar mais nada**: `main()` já pega o resultado dessa
   função, ordena decrescente e pega o Top 10; o JSON, o Streamlit e o
   Quarto continuam iguais.
4. Atualize o texto de `payload["metodologia"]` (e o aviso `callout-note`
   equivalente no `.qmd` e no `st.expander` do Streamlit) pra descrever o
   modelo de verdade em vez da regra provisória — hoje esse texto está
   *hardcoded* em três lugares (script, `.qmd`, `streamlit_app.py`) porque o
   protótipo não tinha necessidade de centralizar isso ainda.
5. Rode `python build_churn_data.py` de novo. Os dashboards não precisam ser
   re-renderizados/reiniciados para "aprender" a mudança — o Streamlit já lê
   o JSON novo ao atualizar a página (limpe o cache com `C` no app ou
   reinicie o processo, já que `load_data()` usa `@st.cache_data`); o Quarto
   precisa de `quarto render clientes_risco.qmd` de novo, pois o JSON é
   embutido no HTML estático no momento do render.

## 7. Como adaptar se a base mudar (colunas renomeadas/novas/removidas)

- **Coluna renomeada**: procure o nome antigo na tabela da seção 4 e troque
  pelo novo em todos os pontos listados na coluna "Onde é usada" — são
  sempre referências diretas tipo `row.Nome_fantasia` ou `snap["tpv_m0"]`,
  não há nenhuma centralização de nomes de coluna hoje (script pequeno o
  suficiente para não precisar disso).
- **Coluna removida** (ex.: pararam de calcular `qtd_stonecodes_ativos`):
  remova a linha correspondente no dicionário `clientes.append({...})` em
  `main()`. Se essa chave for usada nos dashboards (não é o caso hoje,
  `qtd_stonecodes*` só fica no JSON sem uso visual), também remova onde for
  referenciada em `streamlit_app.py` / `clientes_risco.qmd`.
- **Coluna nova que você quer expor no card** (ex.: telefone/e-mail reais,
  se um dia a base deixar de vir anonimizada): adicione o campo em
  `clientes.append({...})` (seção `main()`), e depois exiba nos dois
  dashboards (um `st.markdown(...)` a mais no Streamlit; um `<div>` a mais
  no template JS de `updateClientCard` no `.qmd`).
- **`canais_venda` mudar de formato** (deixar de ser `"A|B|C"`): ajuste só
  `build_channel_info()` — é a única função que interpreta esse formato.
- **`status_ba_m0` mudar os valores possíveis** (deixar de ser
  `"Ativo"/"Inativo"`): ajuste o filtro em `main()`
  (`snap.status_ba_m0 == "Ativo"`).
- **Estrutura de meses mudar** (ex.: parar de ter `tpv_m1/m2/m3` e passar a
  ter uma tabela separada de histórico): o componente mais afetado seria
  `compute_risk_score` (que usa `tpv_m1/m2/m3` como "baseline") e
  `build_ytd_series` (que hoje monta a série a partir de uma linha por mês
  na própria base, não de `tpv_m1/m2/m3`).

## 8. Limitações conhecidas do protótipo

- **Score não calibrado**: é uma regra, não foi validada estatisticamente
  contra quem realmente deu churn (`flag_churn`). Serve só para o protótipo
  visual, não para decisão de negócio real.
- **Dados de contato**: a base já vem anonimizada (`Documento`,
  `Nome_fantasia`, `Vendedor` viram `cnpj_/cpf_NNN`, `cliente_NNN`,
  `colaborador_NNN`) e não tem telefone/e-mail reais — por isso o e-mail do
  vendedor é digitado manualmente no dashboard em vez de vir preenchido.
- **Top 10 fixo por execução**: os filtros do dashboard (nome, TPV, score)
  filtram dentro desses 10 já carregados — eles não buscam outros clientes
  fora do Top 10. Para ver mais que 10, aumente `TOP_N` em
  `build_churn_data.py` e rode o script de novo.
