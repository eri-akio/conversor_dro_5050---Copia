# Leitor principal do Excel

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `src/readers/excel_reader.py`  
**Etapa:** 3.1 — Leitor principal do Excel

---

## 1. Responsabilidade

O leitor executa somente tarefas técnicas de abertura e extração.

Ele:

- aceita arquivo `.xlsx`;
- verifica se o arquivo existe;
- rejeita arquivo temporário `~$...xlsx`;
- detecta arquivo inválido ou corrompido;
- confirma as quatro abas obrigatórias;
- lê somente as abas produtivas;
- informa as abas adicionais;
- preserva linhas, fórmulas e formatação básica;
- ignora linhas completamente vazias;
- fecha o arquivo mesmo quando há erro.

Ele ainda não:

- normaliza datas;
- converte valores monetários;
- valida domínios BACEN;
- agrupa eventos;
- calcula totais;
- gera XML;
- executa críticas regulatórias.

---

## 2. Abas obrigatórias

```text
Base
Cabecalho
Sistemas_Origem
Contas_Internas
```

Abas adicionais são permitidas e ficam registradas em:

```python
resultado.additional_sheet_names
```

Assim, a planilha atual de testes pode possuir abas auxiliares sem que
o sistema dependa delas.

---

## 3. Objetos retornados

### `RawCell`

Preserva:

```text
nome da coluna
coordenada, como A2
valor bruto
tipo do Excel
formato numérico
indicação de fórmula
```

### `RawRow`

Preserva:

```text
número original da linha
células organizadas pelo nome da coluna
```

Exemplo:

```python
linha.get_value("idEvento")
linha.get_cell("dataOcorrencia").number_format
```

### `RawSheet`

Preserva:

```text
nome da aba
cabeçalhos
linhas
quantidade de linhas vazias ignoradas
quantidade de fórmulas
```

### `ExcelReadResult`

Contém:

```text
caminho do arquivo
tamanho do arquivo
quatro abas lidas
abas adicionais
total de linhas
total de fórmulas
```

---

## 4. Por que preservar fórmulas

O leitor usa:

```python
data_only=False
```

Portanto, uma célula com fórmula é mantida como fórmula, em vez de
retornar silenciosamente um valor armazenado anteriormente pelo Excel.

Isso permite que uma etapa posterior decida se fórmulas são:

- permitidas;
- proibidas;
- aceitas somente com valor calculado;
- registradas como inconsistência.

O leitor não toma essa decisão regulatória.

---

## 5. Cabeçalhos

A primeira linha de cada aba é tratada como cabeçalho.

O leitor rejeita:

- cabeçalho vazio;
- coluna sem nome;
- cabeçalho que não seja texto;
- nomes duplicados, inclusive com diferença apenas de maiúsculas.

Exemplo inválido:

```text
idEvento | categoriaNivel1 | idEvento
```

Isso é necessário porque um dicionário Python perderia uma das colunas
duplicadas.

A conferência de todas as colunas esperadas será feita por um validador
estrutural específico em etapa posterior.

---

## 6. Linhas vazias

Uma linha é ignorada somente quando todas as células possuem valor
físico `None`.

Valores como estes não são descartados pelo leitor:

```text
""
-
*
N/A
NULL
0
```

Eles serão analisados pelo normalizador de nulos posteriormente.

---

## 7. Erros conhecidos

| Código | Significado |
|---|---|
| `XLSX-READ-001` | Caminho vazio, inexistente ou não é arquivo |
| `XLSX-READ-002` | Extensão diferente de `.xlsx` |
| `XLSX-READ-003` | Falta de permissão |
| `XLSX-READ-004` | Arquivo inválido ou corrompido |
| `XLSX-READ-005` | Erro do sistema operacional |
| `XLSX-READ-006` | Arquivo temporário do Excel |
| `XLSX-EST-001` | Aba obrigatória ausente |
| `XLSX-EST-004` | Cabeçalho duplicado |
| `XLSX-EST-005` | Cabeçalho vazio ou inválido |

Esses erros representam falha técnica ou estrutural e impedem a
continuidade da leitura.

---

## 8. Exemplo de uso no código

```python
from src.readers.excel_reader import read_excel

resultado = read_excel(
    r"D:\Documentos\DRO_5050_planilha.xlsx"
)

base = resultado.get_sheet("Base")

print(base.headers)
print(base.row_count)

primeira_linha = base.rows[0]
print(primeira_linha.row_number)
print(primeira_linha.get_value("idEvento"))
```

---

## 9. Como executar pelo terminal

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

Sem arquivo, o programa continua verificando apenas o ambiente:

```powershell
python main.py
```

---

## 10. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente o leitor:

```powershell
python -m pytest tests/test_excel_reader.py -v
```

---

## 11. Estado

```text
Etapa 3.1 — Leitor principal do Excel: CONCLUÍDA
Próxima etapa: 3.2 — Criar o leitor e a validação inicial da aba Cabecalho
```
