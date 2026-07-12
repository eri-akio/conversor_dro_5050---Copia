# Leitura e normalização das linhas da aba `Base`

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.3 — Normalização linha a linha

## 1. Objetivo

Ler todas as linhas da aba `Base` e produzir uma representação
normalizada e rastreável, sem agrupar eventos nesta etapa.

Cada célula preserva:

```text
coluna
coordenada
valor original
valor normalizado
valor para o XML
status
regra aplicada
descrição extraída
erro
aplicabilidade ao perfil
```

## 2. Resultados

Cada campo gera um `NormalizedBaseField`.

Estados:

```text
VALID
ABSENT
INVALID
```

Cada linha gera um `NormalizedBaseRow`.

A ausência ainda não decide obrigatoriedade. Essa validação será
executada separadamente.

## 3. Dependências da versão

Até `2026-06`, `tipoAvaliacao` aceita `I`, `M` e `NA`, e
`naturezaContingencia` aceita `TRI`, `TRA`, `CIV` e `NA`.

No perfil presumido de `2026-12`, também são reconhecidos `IE`, `ME` e
`OUT`, mantendo o bloqueio documental já registrado.

COSIF usa 8 dígitos no XSD 12/2020 e 8 ou 10 dígitos no XSD 06/2025.

## 4. Campos futuros

Em versões anteriores, `idEventoAgregador`, `dataExclusao` e
`motivoExclusao` ficam marcados como não aplicáveis.

Quando preenchidos, são preservados para diagnóstico e geram
`BASE-LINHA-INFO-001`.

O código de `motivoExclusao` pode ser extraído, mas seu domínio não é
considerado validado. A ocorrência é `BASE-REGRA-NE-001`.

## 5. Fórmulas

Fórmulas são proibidas em identificadores e nos campos sem autorização
explícita. Fórmulas monetárias e de data são aceitas somente quando existe
resultado calculado armazenado e esse resultado é válido para o campo.

Fórmula sem resultado armazenado gera:

```text
BASE-NORM-FORMULA-SEM-RESULTADO-001 — ERRO
```

Fórmula aceita gera `BASE-NORM-FORMULA-AVISO-001` e preserva fórmula,
resultado utilizado, linha e coluna. A política completa está em
`docs/politica_entrada_excel.md`.

## 6. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 7. Como testar

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_text_normalizer.py tests/test_base_reader.py -v
```

## 8. Próxima etapa

```text
5.4 — Validar obrigatoriedades e relações entre os campos de cada linha
```
