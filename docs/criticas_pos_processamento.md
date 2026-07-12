# Críticas oficiais de pós-processamento

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.12  
**Fonte oficial:** `assets/regulatory/criticas_pos_processamento_5050.xlsx`

## 1. Objetivo

Integrar e executar as 26 críticas oficiais de pós-processamento
fornecidas ao projeto.

O catálogo preserva:

```text
código
tipo
descrição
campos avaliados
observações
escopo
dependência
provedor técnico
arquivo de origem
```

A fonte não informa uma data de início individual para essas regras.
Por isso, nenhuma vigência foi inventada.

## 2. Classes de execução

As críticas foram classificadas em:

```text
LOCAL
EVENTOS CONSOLIDADOS
HISTÓRICO DA DATA-BASE ANTERIOR
```

### Locais

Podem ser executadas com os dados da remessa atual.

### Eventos consolidados

Dependem do bloco consolidado calculado de forma determinística.

### Históricas

Dependem do Documento 5050 da data-base imediatamente anterior.

## 3. Reutilização das validações existentes

As seguintes críticas reutilizam diretamente os resultados financeiros
da etapa 5.6:

```text
DRO000011
DRO000012
DRO000013
DRO000014
DRO000015
DRO000023
DRO000024
```

Também são reutilizadas:

```text
DRO000010 ← BASE-CONT-DATA-001
DRO000021 ← BASE-REL-CAT-001
```

Assim, a mesma regra não é implementada em dois lugares com fórmulas
diferentes.

## 4. Regras locais adicionais

Foram implementadas diretamente no integrador:

```text
DRO000003
DRO000004
DRO000005
DRO000009
DRO000032
```

### `DRO000003`

Para evento com:

```text
dataOcorrencia > 2021-01-01
tipoAvaliacao = I
```

exige ao menos um detalhamento de probabilidade resolvido.

### `DRO000004`

Para avaliação individual com probabilidade `PR`, reprova quando:

```text
totalProvisao = 0
```

### `DRO000005`

Para avaliação individual com probabilidade `PO` ou `RE`, reprova
quando:

```text
valorRisco = 0
```

### `DRO000009`

Aplica exatamente o campo indicado na crítica:

```text
min(dataContabilizacao) > 2021-01-01
```

Nesse contexto, `categoriaNivel2` deve estar preenchida.

### `DRO000032`

Para `categoriaNivel1` igual a `1` ou `2`, reprova quando:

```text
totalProvisao > 0
```

## 5. Eventos consolidados

As críticas:

```text
DRO000001
DRO000002
DRO000018
DRO000019
```

são executáveis quando o serviço recebe objetos
`FinalConsolidatedEvent`.

Sem bloco consolidado calculado, o resultado é:

```text
REGRA NÃO EXECUTADA
```

Nenhum valor consolidado é criado artificialmente.

Para as médias:

```text
perda bruta / quantidade de eventos
```

uma quantidade zero com valor acumulado diferente de zero deixa a
regra como `REGRA NÃO EXECUTADA`, pois a divisão é indefinida.

## 6. Dependência histórica

Permanecem não executadas sem a data-base anterior:

```text
DRO000016
DRO000017
DRO000022
DRO000026
DRO000027
DRO000028
DRO000029
DRO000030
```

O sistema não presume o conteúdo do documento anterior.

## 7. Inconsistência e esclarecimento

O tipo oficial controla a gravidade de uma ocorrência:

```text
Inconsistência  → ERRO
Esclarecimento  → AVISO
```

Uma falha de esclarecimento é registrada, mas não bloqueia sozinha a
aptidão.

Uma regra não executada, inclusive de esclarecimento, bloqueia a
conclusão `APTO`, pois não foi verificada.

## 8. Resultado consolidado

Uma crítica pode gerar diversas evidências.

O status final segue:

```text
REPROVADA
REGRA NÃO EXECUTADA
APROVADA
NÃO APLICÁVEL
```

`PostProcessingValidationResult` disponibiliza:

```text
rule_count
evidence_count
status_counts
failed_rules
blocking_failed_rules
warning_failed_rules
not_executed_rules
is_locally_valid
is_fully_verified
blocks_apt
```

## 9. Integração com o documento

O resultado é enviado ao `DocumentBuilder`.

Ocorrências possíveis:

```text
DOC-POS-ERR-001
DOC-POS-AVISO-001
DOC-POS-NE-001
```

Elas não impedem a geração de um XML de diagnóstico, mas erros e
regras não executadas bloqueiam a classificação final como `APTO`.

## 10. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 11. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_post_processing.py -v
```

## 12. Próxima etapa

```text
5.13 — Gerar relatório XLSX da execução
```
