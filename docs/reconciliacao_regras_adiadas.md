# Reconciliação de regras adiadas

## Objetivo

Separar uma decisão provisória por linha de uma regra definitivamente não
executada. O estado provisório adotado pelo projeto é:

```text
ADIADA
```

Uma regra adiada não é aprovada nem reprovada na etapa por linha. Ela deve ser
reavaliada no escopo correto e reconciliada antes da composição do status
local.

## Regras transferidas para o evento

```text
DRO001312 — probabilidade obrigatória para evento individual
DRO001314 — soma dos valores de risco maior que zero
DRO001452 — contabilização em evento exclusivamente de risco
```

As três regras dependem do conjunto completo de linhas do mesmo `idEvento` e
possuem implementação definitiva no validador de consistência do evento.

Não são regras adiadas:

```text
DRO001241
BASE-EXCL-DOM-001
```

Essas ocorrências representam conflitos documentais ainda não resolvidos e
permanecem como `REGRA NÃO EXECUTADA`.

## Chave e precedência

A reconciliação utiliza a chave:

```text
(codigo_regra, idEvento)
```

Quando houver mais de uma evidência definitiva, a precedência conservadora é:

```text
REPROVADA
REGRA NÃO EXECUTADA
APROVADA
NÃO APLICÁVEL
```

Ausência de evidência definitiva produz `REGRA NÃO EXECUTADA` e bloqueia o
status local. Uma reprovação definitiva também bloqueia. Aprovação e não
aplicabilidade concluem a reconciliação sem manter a pendência provisória.

## Rastreabilidade

Cada registro preserva:

```text
codigo_regra
origem
escopo
id_evento
linha_excel
status_provisorio
motivo
dependencia
etapa_execucao
resultado_definitivo
mensagem_definitiva
```

O relatório Excel mantém a ocorrência `ADIADA` e informa nas colunas
`Escopo` e `Resultado Definitivo` como a regra foi encerrada.

