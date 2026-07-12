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

A interface foi simplificada para duas áreas:

```text
1. Arquivos da execução
2. Resultado da execução
```

Ela permite:

```text
selecionar a planilha .xlsx
selecionar a pasta principal de saída
executar a conversão sem congelar a janela
acompanhar as etapas concluídas
visualizar o status final
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

A barra de processamento também foi removida. O andamento é informado pelo
texto de status e pela relação de etapas.

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
python -m pytest tests/test_gui_simplified_layout.py -v
```
