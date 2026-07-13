# Conversor XLSX → XML DRO 5050

Aplicação em Python 3.13 para ler uma planilha Excel, normalizar os dados,
validar as regras do Documento 5050, gerar XML, validar XSD e produzir
relatórios.

> Situação atual: **Etapa 6.1 — interface desktop simplificada com
> Tkinter/ttk**.

## Interface gráfica

Abra a aplicação com:

```powershell
python main.py
```

Também é possível usar:

```powershell
python main.py --gui
python -m src.gui
```

A interface foi simplificada para um único formulário:

```text
Conversor XLSX → XML DRO 5050
Planilha Excel
Pasta de saída
Status
Converter | Abrir XML | Abrir relatório XLSX | Abrir pasta
```

Ela permite:

```text
selecionar a planilha .xlsx
selecionar a pasta principal de saída
executar a conversão sem congelar a janela
acompanhar Aguardando, Processando..., Concluído ou Falha técnica
abrir XML e relatório XLSX
```

A pasta sugerida é:

```text
Downloads\Conversor_DRO_5050
```

Ela recebe diretamente, sem subpastas:

```text
DRO_5050_AAAA-MM.xml
Relatorio_DRO_5050_AAAA-MM.xlsx
```

A versão regulatória continua sendo selecionada automaticamente pela
`dataBase`, mas o quadro de cabeçalho e versão não é mais exibido na tela.

A área de mensagens, as seções numeradas e as barras de rolagem foram
removidas. O resumo regulatório da execução iniciada pela interface é
apresentado no terminal, sem expor os caminhos dos artefatos.

## Processamento em segundo plano

A conversão é executada em uma thread de trabalho.

A janela recebe eventos por uma fila e permanece responsiva durante:

```text
leitura do Excel
normalização
validações
geração do XML
validação XSD
geração dos relatórios
```

## Status finais

```text
APTO PARA ENVIO
NÃO APTO PARA ENVIO
FALHA TÉCNICA
```

Uma regra não executada nunca é considerada aprovada.

## Modo terminal

O modo terminal continua disponível quando o caminho do Excel é informado:

```powershell
python main.py "D:\dados\DRO_5050.xlsx"
```

Sua saída é uma tabela única com `Etapa`, `Situação` e `Mensagem`, na ordem
registrada pelo serviço de conversão, seguida pelo status final.

Pastas personalizadas:

```powershell
python main.py "D:\dados\DRO_5050.xlsx" `
  --output-dir "D:\saidas"
```

## Instalação

```powershell
python -m pip install -r requirements.txt
```

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Teste específico da simplificação:

```powershell
python -m pytest tests/test_terminal_presenter.py `
  tests/test_gui_simplified_layout.py -v
```
