# Agrupamento e consistência dos eventos

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.5 — Agrupar por `idEvento`

## 1. Objetivo

Uma linha da planilha não equivale necessariamente a um evento. Nesta etapa,
todas as linhas com o mesmo `idEvento` são reunidas em um único
`GroupedEvent`.

O agrupamento não escolhe valores conflitantes. Quando duas linhas possuem
valores diferentes para um atributo do evento, o campo permanece sem valor
resolvido e é registrado:

```text
MAP-EVT-001 — ERRO IMPEDITIVO
```

## 2. Atributos comparados

São comparados entre as linhas do mesmo evento:

```text
categorias
tipoAvaliacao
unidadeNegocio
datas do evento
totais
naturezaContingencia
sistema e código de origem
descrição
riscos associados
indicadores socioambiental e cibernético
negocioDescontinuado
idBacen
campos de exclusão da versão 12/2026
```

Uma célula vazia em uma linha e preenchida em outra não cria conflito. Um
conflito existe somente quando há mais de um valor normalizado distinto.

## 3. Probabilidades

As probabilidades são agrupadas pela combinação lógica:

```text
idEvento + probabilidadePerda
```

A repetição do mesmo código com o mesmo `valorRisco` produz um único registro,
preservando todas as linhas de origem.

A repetição com valores diferentes gera:

```text
MAP-PROB-001 — ERRO IMPEDITIVO
```

O sistema não soma probabilidades repetidas e não escolhe um valor.

## 4. Contabilizações

Cada linha com dados contábeis gera um `GroupedAccounting` independente.

As contabilizações não são deduplicadas nesta etapa. São preservados:

```text
linha do Excel
dataContabilizacao
contas internas
contas COSIF
valorPerdaEfetiva
valorProvisao
valorRecuperacao
fonteRecuperacao
```

## 5. Regras executadas no evento

### `DRO001103`

Confirma que o futuro XML terá um único elemento de evento para cada
`idEvento`, mesmo que a entrada possua várias linhas.

### `DRO001311`

Quando `valorTotalRisco` é informado, verifica:

```text
valorTotalRisco = totalProvisao + soma dos valorRisco únicos
```

### `DRO001312`

Para ocorrência a partir de 01/01/2021 e `tipoAvaliacao = I`, exige ao menos
uma probabilidade completa.

O código `IE` da instrução 12/2026 permanece como `REGRA NÃO EXECUTADA` nesta
crítica, pois a crítica fornecida menciona explicitamente apenas `I`.

### `DRO001314`

No contexto definido pela crítica, exige soma de `valorRisco` maior que zero.

### `DRO001452`

Quando o evento contém apenas valores em risco, proíbe a presença do bloco de
contabilizações.

## 6. Resultado da etapa

O sistema produz:

```text
EventGroupingResult
EventsValidationResult
```

Eles informam quantidade de eventos, linhas sem agrupamento, conflitos,
probabilidades, contabilizações e resultados das regras.

## 7. Limites

Esta etapa ainda não:

- compara totais do evento com a soma das contabilizações;
- calcula saldos cronológicos;
- valida sistemas e contas contra as abas auxiliares;
- calcula eventos consolidados;
- gera XML.

## 8. Execução

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 9. Testes

```powershell
python -m pytest tests/test_event_grouping.py -v
```

## 10. Próxima etapa

```text
5.6 — Validar totais, contabilizações e saldos do evento
```
