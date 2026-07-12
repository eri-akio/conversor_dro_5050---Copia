# Leitor e validação inicial da aba `Cabecalho`

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `src/readers/header_reader.py`  
**Etapa:** 3.2 — Leitor e validação inicial do cabeçalho

---

## 1. Objetivo

Extrair a única linha da aba `Cabecalho` e executar validações
estruturais mínimas antes de iniciar normalização, seleção de versão ou
geração do XML.

Nesta etapa, o sistema não tenta corrigir:

- datas;
- CNPJ;
- código do conglomerado;
- tipo de remessa;
- opção de provisão acumulada.

Esses tratamentos serão adicionados em etapas próprias.

---

## 2. Colunas do cabeçalho

### Obrigatórias no Excel

```text
dataBase
codigoConglomerado
cnpj
tipoRemessa
opcaoPorProvisaoAcumulada
```

### Opcional no Excel

```text
codigoDocumento
```

`codigoDocumento` é opcional na planilha porque seu valor oficial é
fixo:

```text
5050
```

Quando a coluna não existir ou sua célula estiver vazia, o sistema usa
o valor fixo e registra:

```text
CAB-INFO-001
```

Caso a planilha informe outro valor, ocorre erro impeditivo.

---

## 3. Quantidade de linhas

A aba deve possuir exatamente uma linha de dados.

| Situação | Código |
|---|---|
| Nenhuma linha | `XLSX-CAB-002` |
| Mais de uma linha | `XLSX-CAB-003` |

O sistema não escolhe arbitrariamente a primeira ou a última linha.

---

## 4. Ausência física versus nulo regulatório

Nesta etapa, é considerado fisicamente vazio apenas:

```text
None
""
texto com somente espaços
```

Valores como estes continuam preservados:

```text
-
*
NULL
N/A
NA
```

O normalizador de nulos decidirá posteriormente como cada valor deverá
ser tratado.

---

## 5. Fórmulas

O leitor principal preserva fórmulas usando:

```python
data_only=False
```

O `openpyxl` não calcula fórmulas. Por esse motivo, uma fórmula em
qualquer campo reconhecido do cabeçalho gera:

```text
CAB-VAL-002 — ERRO IMPEDITIVO
```

Isso é uma limitação técnica, não uma regra regulatória do BACEN.

---

## 6. Colunas adicionais

Colunas adicionais são permitidas.

Elas são registradas como:

```text
CAB-INFO-002 — INFORMAÇÃO
```

e não impedem o processamento inicial.

Nenhum campo adicional é enviado ao XML sem mapeamento oficial.

---

## 7. Objetos criados

### `HeaderFieldValue`

Preserva:

```text
nome do campo
valor original
valor resolvido
coordenada
presença de fórmula
origem: EXCEL ou FIXED_OFFICIAL
```

### `HeaderData`

Preserva:

```text
nome da aba
número da linha
campos reconhecidos
colunas adicionais
```

### `HeaderValidationIssue`

Registra:

```text
código
gravidade
mensagem
campo
coordenada
valor original
```

### `HeaderValidationResult`

Informa:

```text
is_valid
blocking_errors
warnings
information
```

---

## 8. Códigos desta etapa

| Código | Gravidade | Descrição |
|---|---|---|
| `XLSX-CAB-001` | ERRO IMPEDITIVO | Coluna obrigatória ausente |
| `XLSX-CAB-002` | ERRO IMPEDITIVO | Nenhuma linha de dados |
| `XLSX-CAB-003` | ERRO IMPEDITIVO | Mais de uma linha de dados |
| `CAB-VAL-001` | ERRO IMPEDITIVO | Campo obrigatório fisicamente vazio |
| `CAB-VAL-002` | ERRO IMPEDITIVO | Fórmula no cabeçalho |
| `CAB-VAL-003` | ERRO IMPEDITIVO | `codigoDocumento` diferente de `5050` |
| `CAB-INFO-001` | INFORMAÇÃO | Código `5050` aplicado pela regra fixa |
| `CAB-INFO-002` | INFORMAÇÃO | Colunas adicionais encontradas |

---

## 9. O que ainda não é validado

Ainda não são verificadas nesta etapa:

```text
dataBase no formato AAAA-MM
mês 06 ou 12
código de conglomerado C + 7 dígitos
existência do conglomerado no UNICAD
CNPJ com 8 dígitos
tipoRemessa I ou S
opcaoPorProvisaoAcumulada S ou N
seleção da instrução e do XSD
```

Isso evita misturar leitura, normalização e regra regulatória no mesmo
arquivo.

---

## 10. Exemplo de uso

```python
from src.readers.excel_reader import read_excel
from src.readers.header_reader import (
    read_header,
    validate_header_initial,
)

excel = read_excel(
    r"D:\Documentos\DRO_5050_planilha.xlsx"
)

cabecalho = read_header(excel)
validacao = validate_header_initial(cabecalho)

print(cabecalho.document_code)
print(cabecalho.get_value("dataBase"))
print(validacao.is_valid)
```

---

## 11. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

---

## 12. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_header_reader.py -v
```

---

## 13. Estado

```text
Etapa 3.2 — Leitor e validação inicial da aba Cabecalho: CONCLUÍDA
Próxima etapa: 3.3 — Normalizar e validar os campos do cabeçalho
```
