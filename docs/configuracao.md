# Configuração central do projeto

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo principal:** `src/config.py`  
**Etapa:** 2.3 — Configuração central de caminhos e nomes

---

## 1. Objetivo

Evitar que nomes de abas, pastas, XSDs e arquivos de saída fiquem
repetidos em vários módulos.

As demais partes do sistema deverão importar essas configurações:

```python
from src.config import REQUIRED_SHEETS, OUTPUT_DIR
```

Não deverão escrever novamente valores como:

```python
"Base"
"Cabecalho"
"output"
"5050"
```

em diferentes arquivos.

---

## 2. Raiz do projeto

A raiz é calculada automaticamente a partir do local de `src/config.py`:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

Isso evita caminhos fixos como:

```text
D:\Documentos\conversor_dro_5050
```

Assim, o projeto pode ser movido para outra pasta ou outro computador.

---

## 3. Diretórios centralizados

```text
assets/
config/
docs/
output/
schemas/
src/
tests/
```

As pastas de execução são:

```text
output/
```

Elas são recriadas automaticamente pelo método:

```python
ensure_runtime_directories()
```

---

## 4. Abas obrigatórias

```python
REQUIRED_SHEETS = (
    "Base",
    "Cabecalho",
    "Sistemas_Origem",
    "Contas_Internas",
)
```

A grafia é exata.

Abas adicionais serão permitidas, mas essas quatro deverão existir.

---

## 5. Identificação do documento

```python
DOCUMENT_CODE = "5050"
XML_VERSION = "1.0"
XML_ENCODING = "UTF-8"
```

`codigoDocumento` não deverá ser inventado nem alterado pela interface.

---

## 6. XSDs

Os arquivos oficiais foram copiados para nomes internos estáveis:

```text
schemas/dro_5050_2020_12.xsd
schemas/dro_5050_2025_06.xsd
```

Mapeamento inicial:

```python
XSD_PATH_BY_PROFILE = {
    "DRO_2020_12": XSD_2020_PATH,
    "DRO_2025_06": XSD_2025_PATH,
    "DRO_2026_12_PRESUMIDA": XSD_2025_PATH,
}
```

O perfil presumido não significa que o XSD 06/2025 seja suficiente
para validar as instruções 12/2026. O conflito continua registrado na
matriz de versões e em `conflitos_documentais.md`.

---

## 7. Nomes de saída

### XML apto

```text
DRO_5050_AAAA-MM.xml
```

Exemplo:

```text
DRO_5050_2026-06.xml
```

### XML não apto

```text
DRO_5050_AAAA-MM_NAO_APTO.xml
```

### Relatório Excel

```text
Relatorio_DRO_5050_AAAA-MM.xlsx
```

Nesta etapa somente os nomes foram definidos. O mecanismo para evitar
sobrescrita será implementado no módulo de utilitários de arquivos.

---

## 8. Exemplo de uso

```python
from src.config import (
    OUTPUT_DIR,
    build_xml_filename,
    ensure_runtime_directories,
)

ensure_runtime_directories()

nome = build_xml_filename(
    "2026-06",
    apt_for_submission=False,
)

caminho = OUTPUT_DIR / nome

print(caminho)
```

Resultado:

```text
.../output/DRO_5050_2026-06_NAO_APTO.xml
```

---

## 9. Validação básica de `dataBase`

Para nomes de arquivos, são aceitos:

```text
2025-06
2025-12
```

São recusados:

```text
2025-01
06/2025
2025/06
vazio
```

A normalização de formatos alternativos será feita posteriormente pelo
normalizador de datas. O módulo de configuração recebe apenas a forma
já normalizada.

---

## 10. Como executar

```powershell
python main.py
```

O programa verifica:

- diretórios;
- documentos da arquitetura;
- XSDs;
- nomes das abas;
- diretórios de saída;
- dependências.

---

## 11. Como testar

```powershell
python -m pytest -v
```

Para executar somente os testes desta etapa:

```powershell
python -m pytest tests/test_config.py -v
```

---

## 12. Estado

```text
Etapa 2.3 — Configuração central: CONCLUÍDA
Próxima etapa: 3.1 — Criar o leitor principal do Excel
```
