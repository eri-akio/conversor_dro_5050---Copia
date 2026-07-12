# Construção dos objetos finais do Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.8  
**Arquivos principais:**

```text
src/domain/document_model.py
src/builders/document_builder.py
```

## 1. Objetivo

Transformar os dados já normalizados, agrupados e validados em objetos
que representam os blocos do XML.

Esta etapa não escreve o XML em disco e não executa a validação XSD.

## 2. Objetos finais

```text
FinalDocument
FinalIndividualEvent
FinalProbability
FinalAccounting
FinalConsolidatedEvent
FinalSourceSystem
FinalInternalAccount
```

Os objetos utilizam `date`, `Decimal`, inteiros e textos normalizados.

Cada classe fornece:

```python
as_xml_attributes()
```

Esse método retorna os nomes exatos esperados no XSD.

## 3. Mapeamentos importantes

### Cabeçalho

O `DocumentHeader` da etapa 3.3 é reutilizado diretamente.

### Indicador socioambiental

Entrada:

```text
ligacaoRiscoSocioambiental
```

Atributo definido nos XSDs:

```text
ligadoRiscoSocioAmbiental
```

A grafia do XSD possui precedência.

### Probabilidade

Entrada:

```text
probabilidadePerda
```

Saída:

```text
probabilidade
```

### Contas internas

A aba `Contas_Internas` resulta no bloco XML:

```text
contasSubtitulosInternos
```

## 4. Tabelas auxiliares

O documento final inclui somente sistemas e contas efetivamente
utilizados pelos eventos e contabilizações.

Registros não utilizados permanecem registrados como informação na
etapa 5.7, mas não são enviados ao XML.

A ordem de primeira utilização é preservada.

## 5. Campos opcionais

Um atributo opcional somente é incluído em `as_xml_attributes()` quando
existe valor normalizado.

O sistema não envia:

```text
atributo=""
atributo="None"
```

Valores monetários iguais a zero continuam incluídos quando o campo foi
efetivamente informado.

## 6. Eventos excluídos e campos 12/2026

Os XSDs fornecidos não possuem estrutura compatível para:

```text
idEventoAgregador
dataExclusao
motivoExclusao
```

Esses valores são preservados em `UnsupportedProfileValue`.

Eles não são descartados silenciosamente e bloqueiam a geração de um
XML apto no perfil presumido de 12/2026.

## 7. Eventos consolidados

O XSD exige:

```text
1 a 8 eventos consolidados
```

Depois das validações, cada `idEvento` é classificado uma única vez. Os IDs
individualizados são entregues ao builder; os candidatos consolidados são
agrupados por categoria e produzem `FinalConsolidatedEvent` calculados com
`Decimal`. A aba `Base` é a única fonte.

Quando nenhum evento válido fica abaixo dos dois limiares:

```text
DOC-CONS-001 — ERRO IMPEDITIVO
```

O restante do documento é montado para diagnóstico, porém
`is_xml_ready` permanece falso.

Dados ausentes ou conflitantes geram `CONS-CALC-001`, sem classificação
arbitrária nem preenchimento com zero.

## 8. Regras não executadas

Resultados de linha que foram reavaliados no nível do evento deixam de
ser considerados pendentes.

Uma regra que permaneça não executada, como `DRO001241`, produz:

```text
DOC-REGRA-NE-001
```

Ela não impede a construção do objeto nem a serialização estrutural,
mas bloqueia a classificação final como `APTO`.

## 9. Estados do resultado

`DocumentBuildResult` informa:

```text
is_built
is_xml_ready
blocks_apt
blocking_xml_issues
apt_blocking_issues
```

Exemplo:

```python
resultado = build_final_document(...)

if resultado.is_built:
    documento = resultado.document

if not resultado.is_xml_ready:
    print("Documento somente para diagnóstico")
```

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
python -m pytest tests/test_document_builder.py -v
```

## 12. Próxima etapa

```text
5.9 — Gerar o XML a partir dos objetos finais
```
