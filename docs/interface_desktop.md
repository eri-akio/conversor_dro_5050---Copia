# Interface desktop simplificada com Tkinter/ttk

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 6.1 — interface simplificada

## 1. Objetivo

Disponibilizar uma interface desktop simples para executar o serviço completo
de conversão sem repetir regras de negócio na camada visual.

A janela utiliza:

```text
Tkinter
ttk
threading
queue
```

Tkinter e ttk fazem parte da instalação padrão do Python no Windows.

## 2. Como abrir

Modo gráfico padrão:

```powershell
python main.py
```

Também é possível usar:

```powershell
python main.py --gui
python -m src.gui
```

Abrir a interface com uma planilha já selecionada:

```powershell
python main.py --gui "D:\dados\DRO_5050.xlsx"
```

O modo terminal continua disponível:

```powershell
python main.py "D:\dados\DRO_5050.xlsx"
```

## 3. Fluxo da interface

A tela possui somente duas áreas principais:

```text
1. Arquivos da execução
2. Resultado da execução
```

### Arquivos da execução

Permite selecionar:

```text
planilha Excel .xlsx
pasta principal de saída
```

A pasta inicial sugerida é:

```text
Downloads\Conversor_DRO_5050
```

Os arquivos são gravados diretamente nessa pasta, sem subpastas:

```text
arquivo XML
relatório XLSX
```

O botão principal inicia diretamente:

```text
leitura do Excel
seleção automática da versão
validações
geração do XML
validação XSD
relatórios
```

A versão regulatória continua sendo selecionada automaticamente pela
`dataBase`, dentro do serviço de conversão.

A interface não apresenta mais um quadro separado de cabeçalho e versão.

### Resultado da execução

Exibe:

```text
APTO PARA ENVIO
NÃO APTO PARA ENVIO
FALHA TÉCNICA
```

A aba `Etapas` mostra situação, duração e mensagem de cada fase.

A aba `Mensagens e motivos` mostra críticas, dependências e razões do status
final.

Quando os arquivos existem, ficam disponíveis botões para abrir:

```text
XML
relatório XLSX
```

## 4. Processamento sem congelar

A conversão é executada em uma thread de trabalho.

A janela principal não chama funções longas diretamente. O controlador envia
eventos por uma fila:

```text
INICIADO
CONCLUÍDO
FALHOU
REJEITADO
```

A janela consulta essa fila com `after`, mantendo a interface responsiva.

A barra visual de processamento foi removida. O acompanhamento continua sendo
feito pelo texto de status e pela lista de etapas concluídas.

Somente uma operação pode ser executada por vez.

## 5. Encerramento

Quando existe uma operação em andamento, a interface solicita confirmação
antes de fechar.

A thread é marcada como `daemon`; não existe cancelamento forçado no meio de
uma escrita de XML ou relatório.

## 6. Arquitetura

```text
src/gui/
    __init__.py
    __main__.py
    app.py
    controller.py
    header_preview_service.py
    models.py
    system_utils.py
```

O serviço de pré-visualização do cabeçalho permanece disponível como componente
interno e para testes, mas não é mais exibido na janela principal.

## 7. Testes

Todos os testes:

```powershell
python -m pytest -v
```

Testes da interface simplificada:

```powershell
python -m pytest tests/test_gui_simplified_layout.py -v
python -m pytest tests/test_gui_controller.py -v
python -m pytest tests/test_main_entrypoint.py -v
```
