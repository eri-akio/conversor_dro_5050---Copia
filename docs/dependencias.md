# Dependências do projeto — Conversor DRO 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `docs/dependencias.md`  
**Etapa:** 2.2 — Definição e instalação das dependências

---

## 1. Versão do Python

O projeto foi definido para:

```text
Python 3.13.x
```

A versão de referência do ambiente do projeto é:

```text
Python 3.13.14
```

O verificador aceita qualquer correção da série 3.13, mas informa a
versão efetivamente encontrada.

Para consultar a versão instalada:

```powershell
python --version
```

---

## 2. Dependências de produção

Estas bibliotecas são necessárias para executar a aplicação.

| Biblioteca | Versão | Finalidade |
|---|---:|---|
| `openpyxl` | `3.1.5` | Ler o Excel de entrada preservando linhas, fórmulas e formatos |
| `lxml` | `6.1.1` | Construir XML e validar o documento contra o XSD |
| `defusedxml` | `0.7.1` | Adicionar proteção contra ataques e expansões XML maliciosas |
| `artifact_tool_v2` | `2.8.4` | Gerar, formatar e inspecionar o relatório `.xlsx` |

### 2.1. Por que não usar `pandas`

O projeto não precisa de `pandas` nesta etapa.

A leitura será feita diretamente com `openpyxl`, porque isso permite:

- preservar os valores originais das células;
- preservar números de linha;
- tratar códigos como texto;
- evitar conversões automáticas para `float`;
- controlar melhor fórmulas, datas e zeros à esquerda.

Os valores monetários serão tratados com `Decimal`, que pertence à
biblioteca padrão do Python e não precisa ser instalado.

### 2.2. Por que usar `lxml`

`xml.etree.ElementTree`, da biblioteca padrão, consegue criar XML, mas
o projeto precisa validar o arquivo contra esquemas XSD.

O `lxml` oferece suporte a:

- XML Schema;
- XPath;
- mensagens detalhadas de validação;
- construção de árvores XML.

### 2.3. Por que usar `defusedxml`

Arquivos `.xlsx` são pacotes que contêm documentos XML internamente.

A biblioteca será instalada como proteção adicional para leitura de
XML potencialmente malformado ou malicioso. Sua presença não substitui:

- limite de tamanho do arquivo;
- controle de extensão;
- tratamento de arquivo corrompido;
- validação do conteúdo.

### 2.4. Por que usar `artifact_tool_v2`

Os relatórios Excel precisam de formatação, tabelas, fórmulas, congelamento de
painéis e inspeção automática de erros. O `artifact_tool_v2` é utilizado
somente na camada de relatórios; a leitura da planilha de entrada continua com
`openpyxl`.

---

## 3. Dependência de desenvolvimento

| Biblioteca | Versão | Finalidade |
|---|---:|---|
| `pytest` | `9.0.2` | Executar testes unitários e de integração |

O `pytest` não será necessário para o usuário final executar a aplicação,
mas será utilizado durante o desenvolvimento e a homologação.

---

## 4. Bibliotecas que não precisam de instalação

Estas bibliotecas pertencem à instalação padrão do Python:

```text
tkinter
tkinter.ttk
pathlib
decimal
datetime
dataclasses
logging
threading
queue
re
json
zipfile
importlib
unittest
```

O `tkinter` normalmente acompanha a instalação oficial do Python para
Windows. Ele deverá ser verificado separadamente.

---

## 5. Criar o ambiente virtual

No terminal do VS Code, dentro da pasta do projeto:

```powershell
python -m venv .venv
```

Ativar no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ativar no Prompt de Comando:

```cmd
.venv\Scripts\activate.bat
```

Após a ativação, o terminal normalmente mostrará:

```text
(.venv)
```

---

## 6. Atualizar o instalador de pacotes

```powershell
python -m pip install --upgrade pip
```

---

## 7. Instalar as dependências

### 7.1. Instalação para desenvolvimento

Esta é a opção recomendada durante a criação do projeto:

```powershell
python -m pip install -r requirements-dev.txt
```

Esse comando instala:

```text
openpyxl
lxml
defusedxml
artifact_tool_v2
pytest
```

### 7.2. Instalação somente para executar a aplicação

```powershell
python -m pip install -r requirements.txt
```

Essa opção não instala o `pytest`.

---

## 8. Conferir a instalação

```powershell
python main.py
```

Também é possível consultar diretamente:

```powershell
python -m pip show openpyxl
python -m pip show lxml
python -m pip show defusedxml
python -m pip show artifact_tool_v2
python -m pip show pytest
```

Para conferir o Tkinter:

```powershell
python -m tkinter
```

Esse comando deve abrir uma pequena janela de teste.

---

## 9. Executar os testes

```powershell
python -m pytest -v
```

O comando antigo com `unittest` continua disponível:

```powershell
python -m unittest discover -s tests -v
```

---

## 10. Solução de problemas

### PowerShell bloqueou a ativação

Use temporariamente o Prompt de Comando:

```cmd
.venv\Scripts\activate.bat
```

Ou execute os comandos utilizando diretamente o Python do ambiente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -v
```

### `python` não foi reconhecido

Teste:

```powershell
py --version
```

Se funcionar, substitua `python` por `py` nos comandos de criação do
ambiente virtual.

### Erro ao instalar `lxml`

Primeiro atualize o `pip`:

```powershell
python -m pip install --upgrade pip
```

Depois tente novamente:

```powershell
python -m pip install -r requirements-dev.txt
```

### Tkinter não foi encontrado

Reinstale o Python pelo instalador oficial para Windows e confirme que
os componentes Tcl/Tk estão selecionados.

---

## 11. Dependências futuras não instaladas agora

Estas bibliotecas poderão ser avaliadas em etapas futuras:

| Biblioteca | Possível uso | Motivo para não instalar agora |
|---|---|---|
| `pyinstaller` | Gerar executável Windows | Será usado somente no empacotamento |
| `pytest-cov` | Relatório de cobertura | Ainda não é necessário |
| `ruff` | Formatação e análise estática | Será avaliado quando houver mais código |
| `mypy` | Verificação de tipos | Será avaliado após os modelos de domínio |

Não serão adicionadas dependências sem necessidade concreta.

---

## 12. Estado da etapa

```text
Etapa 5.14 — Dependências revisadas para o serviço completo
Próxima etapa: 6.1 — Interface desktop com Tkinter/ttk
```
