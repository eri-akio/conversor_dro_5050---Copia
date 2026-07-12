# Normalização e validação dos campos do cabeçalho

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo principal:** `src/normalizers/header_normalizer.py`  
**Etapa:** 3.3 — Normalização e validação da aba `Cabecalho`

---

## 1. Objetivo

Transformar o cabeçalho bruto em um objeto tipado e validado:

```text
DocumentHeader
```

A normalização preserva:

- valor original;
- valor normalizado;
- célula de origem;
- regra aplicada;
- indicação de alteração;
- erro encontrado.

Nenhuma correção é silenciosa.

---

## 2. Modelo normalizado

Arquivo:

```text
src/domain/document_header.py
```

Campos:

```text
codigo_documento
data_base
codigo_conglomerado
cnpj
tipo_remessa
opcao_por_provisao_acumulada
```

O método:

```python
header.as_xml_attributes()
```

retorna os nomes exatos esperados no elemento XML `documento`.

---

## 3. Candidatos a nulo

Arquivo:

```text
src/normalizers/null_normalizer.py
```

Valores tratados como candidatos a ausência:

```text
vazio
None
NaN
NULL
N/A
-
*
```

`NA` não é tratado automaticamente como nulo, porque pode ser domínio
válido em outros campos do Documento 5050.

No cabeçalho, `NA` continua inválido para os domínios existentes, mas
será rejeitado pela regra específica do campo, não pela regra de nulo.

---

## 4. Regras por campo

### `codigoDocumento`

Resultado obrigatório:

```text
5050
```

Quando a coluna ou a célula não existe, o leitor da etapa 3.2 aplica o
valor fixo oficial. A normalização confirma o resultado.

### `dataBase`

Entradas aceitas:

```text
2026-06
06/2026
30/06/2026
2026-06-30
2026-06-30 12:30:00
data ou data/hora nativa do Excel
```

Saída:

```text
2026-06
```

Validações:

- mês igual a `06` ou `12`;
- data não anterior a `2020-12`.

Números sem tipo de data não são interpretados como serial do Excel,
pois isso seria ambíguo. Células de data reais são normalmente
devolvidas pelo `openpyxl` como `date` ou `datetime`.

### `codigoConglomerado`

Formato local:

```text
C + 7 dígitos
```

Exemplo:

```text
C0099999
```

O sistema remove apenas espaços externos. Ele não transforma `c` em
`C`, não inventa prefixo e não completa dígitos.

A existência do código no UNICAD será uma regra externa e permanece
não executada sem a base correspondente.

### `cnpj`

O Documento 5050 utiliza a raiz de 8 dígitos.

Exemplos:

```text
12.345.678  → 12345678
12345678    → 12345678
```

Um CNPJ completo de 14 dígitos não é reduzido automaticamente para
oito dígitos, pois isso alteraria o dado informado sem regra explícita.

### `tipoRemessa`

Valores permitidos:

```text
I
S
```

São removidos espaços externos e o código é convertido para
maiúsculas.

### `opcaoPorProvisaoAcumulada`

Valores permitidos:

```text
S
N
```

São removidos espaços externos e o código é convertido para
maiúsculas.

---

## 5. Códigos de erro

| Código | Descrição |
|---|---|
| `CAB-NULO-001` | Campo obrigatório contém candidato a ausência |
| `CAB-NORM-002` | Fórmula não pode ser normalizada com segurança |
| `CAB-DOC-001` | Código diferente de `5050` |
| `CAB-DATA-001` | Formato ou data-base inválida |
| `CAB-DATA-002` | Mês diferente de `06` ou `12` |
| `CAB-DATA-003` | Data-base anterior a `2020-12` |
| `CAB-CONG-001` | Código de conglomerado fora do padrão |
| `CAB-CNPJ-001` | Raiz do CNPJ diferente de 8 dígitos |
| `CAB-REM-001` | Tipo de remessa fora de `I/S` |
| `CAB-PROV-001` | Opção de provisão fora de `S/N` |

Todos esses erros são impeditivos nesta etapa.

---

## 6. Rastreabilidade

Cada campo gera um `HeaderFieldTransformation`.

Exemplo:

```text
campo: cnpj
original: 12.345.678
normalizado: 12345678
regra: NORM-CAB-CNPJ-001
alterado: sim
```

Esses registros serão reutilizados no relatório Excel final.

---

## 7. Validações ainda não executadas

Esta etapa não confirma:

- existência de `codigoConglomerado` no UNICAD;
- existência institucional associada ao CNPJ;
- compatibilidade histórica do cabeçalho;
- versão regulatória completa;
- críticas de pré e pós-processamento.

A seleção automática de instrução e XSD será a próxima etapa.

---

## 8. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

---

## 9. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente os normalizadores do cabeçalho:

```powershell
python -m pytest tests/test_null_normalizer.py tests/test_header_normalizer.py -v
```

---

## 10. Estado

```text
Etapa 3.3 — Normalização e validação do cabeçalho: CONCLUÍDA
Próxima etapa: 4.1 — Selecionar automaticamente a versão pela dataBase
```
