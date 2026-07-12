# Serviço completo de conversão e status final

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.14

## 1. Objetivo

Concentrar o fluxo completo em um único serviço reutilizável:

```text
ConversionService
```

A interface de terminal e a futura interface Tkinter não executam mais as
regras diretamente. Elas apenas criam uma solicitação, chamam o serviço e
apresentam o resultado.

## 2. Fluxo consolidado

```text
Excel
  ↓
leitura das quatro abas produtivas
  ↓
leitura, validação e normalização do cabeçalho
  ↓
seleção automática da versão pela dataBase
  ↓
estrutura e normalização da Base
  ↓
validação por linha
  ↓
agrupamento por idEvento
  ↓
consistência e validação financeira
  ↓
classificação exclusiva por idEvento
  ↓
cálculo dos consolidados por categoria e semestre
  ↓
sistemas e contas internas
  ↓
pré-processamento
  ↓
pós-processamento
  ↓
objetos finais
  ↓
XML
  ↓
XSD selecionado
  ↓
status final
  ↓
relatório XLSX
```

Entre a validação dos eventos e as etapas financeiras, o serviço executa
`RECONCILIAÇÃO DE REGRAS ADIADAS`. Essa etapa liga decisões provisórias por
linha aos resultados definitivos por evento usando código da regra e
`idEvento`.

## 3. Entrada do serviço

A solicitação é representada por:

```python
ConversionRequest
```

Ela contém:

```text
input_path
output_dir
```

Não existe seleção manual de versão no serviço. O perfil regulatório continua
sendo determinado exclusivamente pela `dataBase`.

## 4. Resultado único

O retorno é:

```python
ConversionResult
```

Ele contém:

```text
execution_id
request
started_at
finished_at
decision
stage_records
issues
artifacts
stage_outputs
```

Os resultados intermediários podem ser consultados por etapa:

```python
xsd_result = result.output(
    ConversionStage.VALIDATE_XSD
)
```

## 5. Estados finais

A decisão é produzida somente por:

```python
FinalStatusService
```

Estados:

```text
APTO PARA ENVIO
NÃO APTO PARA ENVIO
FALHA TÉCNICA
```

A decisão também expõe separadamente:

```text
status_local     = APROVADO | REPROVADO | FALHA_TECNICA
status_xsd       = APROVADO | REPROVADO | NAO_EXECUTADO
status_externo   = APROVADO | REPROVADO | NAO_EXECUTADO | NAO_APLICAVEL
status_historico = APROVADO | REPROVADO | NAO_EXECUTADO | NAO_APLICAVEL
status_final     = APTO_PARA_ENVIO | NAO_APTO_PARA_ENVIO | FALHA_TECNICA
```

As regras `EXTERNA` do pré-processamento alimentam `status_externo`. As
regras `HISTÓRICO DA DATA-BASE ANTERIOR` do pós-processamento alimentam
`status_historico`. As demais validações permanecem no status local.

### APTO PARA ENVIO

Exige simultaneamente:

```text
perfil sem conflito impeditivo
linhas sem erro impeditivo
eventos sem conflito
validações financeiras aprovadas
sistemas e contas válidos
pré-processamento totalmente verificado
pós-processamento totalmente verificado
documento construído
XML gerado como candidato
XML válido no XSD selecionado
status externo aprovado ou não aplicável
status histórico aprovado ou não aplicável
```

Uma validação externa ou histórica não executada nunca é considerada
aprovada. Mesmo com status local e XSD aprovados, ela mantém o documento
como `NÃO APTO PARA ENVIO` e aparece separadamente na mensagem final.

### NÃO APTO PARA ENVIO

É usado quando a execução técnica terminou, mas existe:

```text
erro de dados
campo obrigatório ausente
conflito entre linhas do evento
crítica reprovada
regra não executada
conflito documental
XML diagnóstico
falha de conformidade com o XSD
```

### FALHA TÉCNICA

É usada quando a aplicação não consegue executar a validação:

```text
arquivo inexistente ou corrompido
aba obrigatória ausente
sem permissão de leitura ou escrita
XSD indisponível
erro inesperado
falha na geração dos relatórios
```

## 6. Etapas rastreadas

Cada etapa gera um:

```python
ConversionStageRecord
```

Situações:

```text
CONCLUÍDA
INTERROMPIDA — NÃO APTO
FALHA TÉCNICA
NÃO EXECUTADA
```

O registro contém início, fim, duração, mensagem e detalhes.

## 7. Interrupções antecipadas

Quando o fluxo para antes do XML por erro de dados, o resultado é
`NÃO APTO PARA ENVIO`.

Quando para por erro de leitura, permissão ou falha inesperada, o resultado é
`FALHA TÉCNICA`.

Nos dois casos, o serviço tenta gerar relatórios de diagnóstico. Quando ainda
não existe uma `dataBase` válida, usa somente no nome do arquivo:

```text
SEM_DATA_BASE
```

Exemplo:

```text
Relatorio_DRO_5050_SEM_DATA_BASE.xlsx
```

Isso é um rótulo técnico e não representa uma competência inventada.

## 8. Códigos de saída do terminal

```text
0 — execução concluída, APTO ou NÃO APTO
1 — ambiente do projeto inválido
2 — falha técnica durante a conversão
```

`NÃO APTO` usa código zero porque a aplicação concluiu corretamente a análise
e produziu um resultado regulatório negativo.

## 9. Artefatos

`ConversionArtifacts` reúne:

```text
xml_path
xlsx_path
```

Arquivos existentes continuam protegidos contra sobrescrita.

## 10. Uso em Python

```python
from src.services import convert_excel

resultado = convert_excel(
    r"D:\dados\DRO_5050.xlsx",
    output_dir=r"D:\dados\output",
)

print(resultado.status.value)
print(resultado.artifacts.xml_path)
```

## 11. Uso pelo terminal

```powershell
python main.py "D:\dados\DRO_5050.xlsx"
```

Pastas personalizadas:

```powershell
python main.py "D:\dados\DRO_5050.xlsx" `
  --output-dir "D:\saidas"
```

## 12. Testes

Todos os testes:

```powershell
python -m pytest -v
```

Somente o serviço completo:

```powershell
python -m pytest tests/test_conversion_service.py -v
```

Somente o status final:

```powershell
python -m pytest tests/test_final_status_service.py -v
```

## 13. Próxima etapa

```text
6.1 — Criar a interface desktop com Tkinter/ttk
```
