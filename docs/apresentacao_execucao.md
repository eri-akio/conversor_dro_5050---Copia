# Apresentação da execução no terminal e na interface

## Origem dos dados

O serviço de conversão continua sendo a única origem das etapas. Cada etapa
gera um `ConversionStageRecord`, armazenado em
`ConversionResult.stage_records`, com nome, situação, mensagem, horários e
detalhes.

Nenhum texto é lido de widget da interface e nenhuma decisão regulatória é
recalculada pela camada de apresentação.

## Terminal

`src/presenters/terminal.py` recebe os registros estruturados e imprime uma
tabela com:

```text
Etapa | Situação | Mensagem
```

Os registros mantêm a ordem produzida pelo serviço. Mensagens longas são
quebradas sem truncamento, registros visualmente idênticos não são repetidos e
o status final aparece por último.

A verificação de ambiente não imprime mais configurações, caminhos ou blocos
numerados quando é bem-sucedida. Uma falha anterior à conversão é apresentada
na mesma estrutura, como `FALHA TÉCNICA`.

No modo gráfico, o controller apresenta uma vez o resumo local, XSD, externo,
histórico, final e a mensagem da decisão. No modo CLI, `main.py` preserva a
tabela completa de etapas.

## Interface

A janela não possui seções numeradas, subtítulo, área `Mensagem`, `tk.Text` ou
barras de rolagem. Ela contém somente título, seleção do Excel, pasta de saída,
indicador de status e botões de conversão e abertura.

O indicador assume apenas `Aguardando`, `Processando...`, `Concluído` ou
`Falha técnica`. Os caminhos dos artefatos permanecem internos e habilitam
individualmente os botões de XML e relatório.

A execução permanece em uma thread de trabalho. A GUI consome a fila por
`after()` e todos os widgets continuam sendo atualizados apenas na thread
principal do Tkinter.

## Escopo preservado

Não foram alterados leitura, normalização, regras regulatórias, agrupamento,
consolidação, XML, XSD, relatórios ou cálculo do status final.

## Testes

```powershell
python -m pytest tests/test_terminal_presenter.py `
  tests/test_gui_simplified_layout.py `
  tests/test_gui_controller.py `
  tests/test_main_entrypoint.py -q

python -m pytest -q
```
