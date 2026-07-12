# Fontes regulatórias versionadas

Esta pasta contém cópias dos arquivos oficiais fornecidos ao projeto,
com nomes internos estáveis para uso pelo código.

```text
instrucoes_preenchimento_2020_12.pdf
instrucoes_preenchimento_2026_12.pdf
```

Os arquivos não foram alterados. Somente os nomes internos foram
padronizados.

Os XSDs permanecem em:

```text
schemas/dro_5050_2020_12.xsd
schemas/dro_5050_2025_06.xsd
```

A seleção é feita pela `dataBase`, nunca por tentativa de validar o
mesmo XML contra vários XSDs.


## Críticas de pré-processamento

```text
criticas_pre_processamento_5050.xlsx
```

Cópia preservada do arquivo oficial fornecido ao projeto. O catálogo Python da
etapa 5.11 foi transcrito dessa fonte e mantém as 34 regras, o tipo `E`, a base
confrontada e a vigência `jun/21`.

## Críticas de pós-processamento

```text
criticas_pos_processamento_5050.xlsx
```

Cópia preservada do arquivo oficial fornecido ao projeto. O catálogo Python da
etapa 5.12 mantém as 26 regras, os tipos `Inconsistência` e `Esclarecimento`,
os campos avaliados e as observações da fonte.

