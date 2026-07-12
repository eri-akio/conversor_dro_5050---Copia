# Matriz de versões — Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `docs/matriz_versoes.md`  
**Finalidade:** selecionar automaticamente as instruções, o XSD, os campos, os domínios e as regras aplicáveis a partir do campo `dataBase` da aba `Cabecalho`.

---

## 1. Fontes oficiais utilizadas

A matriz foi construída exclusivamente com os arquivos fornecidos ao projeto:

1. `DRO - Demonstrativo de Risco Operacional - Instruções de Preenchimento12_2020.pdf`
2. `DRO - Demonstrativo de Risco Operacional - Instrucões de Preenchimento 12_2026.pdf`
3. `Esquema de validação válido a partir da data-base 122020.xsd`
4. `Esquema de validação válido a partir da data-base 062025.xsd`
5. `DRO - Modelo XML do Documento 5050.pdf`
6. `DRO - Modelo XML do Documento 5050 - Exemplo.xml`
7. `criticas_pre_processamento_5050(1).xlsx`
8. `criticas_pos_processamento_5050(1).xlsx`

### 1.1. Ordem de precedência

Quando houver divergência entre as fontes, o sistema deverá aplicar a seguinte ordem:

1. **XSD**, para estrutura, tipos, formatos e cardinalidades;
2. **instruções de preenchimento**, para regras de negócio e obrigatoriedades condicionais;
3. **críticas de pré-processamento**;
4. **críticas de pós-processamento**;
5. **modelo PDF e XML de exemplo**, somente como referência.

Uma divergência não deve ser resolvida silenciosamente. Ela deverá ser registrada no relatório e em `docs/conflitos_documentais.md`.

---

## 2. Regras gerais da `dataBase`

O campo `dataBase` é informado na aba `Cabecalho` e controla toda a seleção de versão.

### 2.1. Formato

Formato obrigatório:

```text
AAAA-MM
```

Exemplos válidos:

```text
2020-12
2025-06
2026-12
```

### 2.2. Meses permitidos

O Documento 5050 é semestral. Portanto, os meses aceitos são:

```text
06
12
```

Exemplos inválidos:

```text
2025-01
2026-07
```

### 2.3. Limite inicial

A primeira data-base prevista pelos arquivos fornecidos é:

```text
2020-12
```

Uma data-base anterior deverá gerar erro impeditivo.

---

## 3. Matriz principal de seleção

| Código interno | Data-base inicial | Data-base final | Instrução aplicável | XSD aplicável | Perfil do leiaute | Situação | Pode resultar em APTO? |
|---|---:|---:|---|---|---|---|---|
| `DRO_2020_12` | `2020-12` | `2024-12` | Instruções 12/2020 | XSD 12/2020 | Legado original | Confirmada | Sim |
| `DRO_2025_06` | `2025-06` | `2026-06` | Instruções 12/2020 | XSD 06/2025 | Legado com alteração COSIF | Confirmada | Sim |
| `DRO_2026_12_PRESUMIDA` | `2026-12` | sem data final definida | Instruções 12/2026 | XSD 06/2025, por ser o mais recente fornecido | Novo presumido | Conflito documental | Não, enquanto o conflito não for resolvido |

### 3.1. Interpretação dos intervalos

Como as remessas são semestrais:

- a versão iniciada em `2020-12` permanece aplicável até `2024-12`;
- o XSD iniciado em `2025-06` passa a ser usado em `2025-06`;
- as instruções iniciadas em `2026-12` passam a ser usadas em `2026-12`;
- a última data-base anterior às instruções 12/2026 é `2026-06`.

---

## 4. Perfil `DRO_2020_12`

### 4.1. Vigência

```text
2020-12 até 2024-12
```

### 4.2. Fontes selecionadas

```text
Instruções: 12/2020
XSD:        12/2020
```

### 4.3. Estrutura esperada

O documento utiliza:

1. `eventosIndividualizados`;
2. `eventosConsolidados`;
3. `sistemasOrigem`;
4. `contasSubtitulosInternos`.

### 4.4. Domínios principais

| Campo | Domínio ou formato |
|---|---|
| `codigoDocumento` | `5050` |
| `tipoRemessa` | `I` ou `S` |
| `opcaoPorProvisaoAcumulada` | `S` ou `N` |
| `tipoAvaliacao` | `I`, `M` ou `NA` |
| `naturezaContingencia` | `TRI`, `TRA`, `CIV` ou `NA` |
| `probabilidade` | `PR`, `PO` ou `RE` |
| `fonteRecuperacao` | `S`, `O` ou `NA` |
| `contaCosifDebito` | 8 dígitos |
| `contaCosifCredito` | 8 dígitos |
| `idEvento` | alfanumérico, de 1 a 40 caracteres |
| `codigoEventoOrigem` | alfanumérico, de 1 a 73 caracteres |

### 4.5. Unicidade do `idEvento`

O XSD 12/2020 contém uma chave de unicidade para `idEvento`.

Mesmo assim, a aplicação também deverá validar a unicidade antes de construir o XML, para produzir uma mensagem compreensível com as linhas do Excel envolvidas.

---

## 5. Perfil `DRO_2025_06`

### 5.1. Vigência

```text
2025-06 até 2026-06
```

### 5.2. Fontes selecionadas

```text
Instruções: 12/2020
XSD:        06/2025
```

### 5.3. Alterações confirmadas no XSD 06/2025

A comparação direta dos dois XSDs fornecidos identificou duas alterações.

#### Alteração 1 — conta COSIF

No XSD 12/2020:

```text
8 dígitos
```

No XSD 06/2025:

```text
8 ou 10 dígitos
```

Aplicável a:

```text
contaCosifDebito
contaCosifCredito
```

#### Alteração 2 — chave XSD do `idEvento`

O XSD 06/2025 remove a declaração `xs:key` que verificava a unicidade do `idEvento`.

Essa remoção não torna IDs repetidos permitidos. A unicidade continua sendo exigida pelas instruções e pelas críticas de pré-processamento.

Portanto, o sistema deverá continuar executando uma validação local de unicidade.

### 5.4. Estrutura esperada

A estrutura permanece com os quatro blocos do leiaute anterior:

1. `eventosIndividualizados`;
2. `eventosConsolidados`;
3. `sistemasOrigem`;
4. `contasSubtitulosInternos`.

### 5.5. Campos não disponíveis nessa versão

Os seguintes campos e blocos das instruções 12/2026 ainda não devem ser gerados:

```text
idEventoAgregador
tipoAvaliacao = IE
tipoAvaliacao = ME
naturezaContingencia = OUT
novos campos de detalhamento do consolidado
eventosIndividualizadosExcluidos
dataExclusao
motivoExclusao
```

---

## 6. Perfil `DRO_2026_12_PRESUMIDA`

### 6.1. Vigência

```text
2026-12 em diante
```

### 6.2. Fontes selecionadas

```text
Instruções: 12/2026
XSD disponível mais recente: 06/2025
```

### 6.3. Motivo da classificação “novo presumido”

As instruções 12/2026 alteram o leiaute e as regras de negócio, mas o XSD 06/2025 fornecido não contém essas alterações.

O perfil é chamado de **novo presumido** porque:

- a instrução nova possui vigência a partir de `2026-12`;
- não foi fornecido um XSD posterior compatível com todos os campos da instrução nova;
- o XSD 06/2025 é o mais recente disponível, mas ainda representa majoritariamente o leiaute anterior.

### 6.4. Alterações previstas pelas instruções 12/2026

| Área | Alteração |
|---|---|
| Avaliação | inclusão de `IE` e `ME` em `tipoAvaliacao` |
| Natureza | inclusão de `OUT` em `naturezaContingencia` |
| Agregação | inclusão de `idEventoAgregador` |
| Consolidado | inclusão de campos de provisão por natureza |
| Consolidado | inclusão de totais de recuperação |
| Saídas | inclusão de `eventosIndividualizadosExcluidos` |
| Saídas | inclusão de `dataExclusao` |
| Saídas | inclusão de `motivoExclusao` |
| COSIF | previsão de códigos com 8 ou 10 dígitos |

### 6.5. Conflito com o XSD 06/2025

O XSD 06/2025 não declara, entre outros:

```text
idEventoAgregador
IE
ME
OUT
provisaoTotalCIV
provisaoTotalTRA
provisaoTotalTRI_CONST
provisaoTotalTRI_OUTROS
provisaoTotalOUTROS
recuperacaoTotalConsol
recuperacaoSemestreConsol
eventosIndividualizadosExcluidos
dataExclusao
motivoExclusao
```

Se esses campos forem incluídos no XML, a validação pelo XSD 06/2025 falhará.

Se esses campos forem omitidos somente para o XML passar no XSD, o arquivo poderá deixar de atender às instruções 12/2026.

### 6.6. Decisão obrigatória do sistema

Para `dataBase >= 2026-12`, enquanto não houver XSD compatível:

```text
versao = DRO_2026_12_PRESUMIDA
status_versao = CONFLITO_DOCUMENTAL
bloqueia_apto = SIM
```

O sistema poderá gerar um XML para diagnóstico, mas o resultado final deverá ser:

```text
NÃO APTO PARA ENVIO
```

Motivo sugerido:

```text
VER-001 — As instruções 12/2026 exigem campos ou blocos não previstos no XSD 06/2025 fornecido.
```

O sistema nunca deverá eliminar dados da instrução nova ou inventar dados apenas para fazer o XML passar no XSD antigo.

---

## 7. Conflitos de nomenclatura identificados

### 7.1. Campo socioambiental

Foram encontradas referências diferentes:

```text
ligadoRiscoSocioAmbiental
ligadoRSAC
```

O XSD fornecido utiliza:

```text
ligadoRiscoSocioAmbiental
```

A planilha de entrada possui:

```text
ligacaoRiscoSocioambiental
```

Decisão provisória:

```text
Excel: ligacaoRiscoSocioambiental
XML nas versões confirmadas: ligadoRiscoSocioAmbiental
```

Para a versão 12/2026, a divergência deverá permanecer registrada até existir um XSD compatível que confirme o nome definitivo.

### 7.2. Opção por provisão acumulada

O nome confirmado pelos XSDs é:

```text
opcaoPorProvisaoAcumulada
```

Eventuais variações tipográficas no PDF não devem alterar o nome gerado no XML.

### 7.3. Código do evento de origem

O nome confirmado pelos XSDs é:

```text
codigoEventoOrigem
```

Variações encontradas somente em representações ilustrativas não devem substituir o nome definido no XSD.

---

## 8. Algoritmo de seleção

O futuro `version_resolver.py` deverá seguir esta ordem:

```text
1. Ler Cabecalho.dataBase.
2. Normalizar para AAAA-MM.
3. Rejeitar valor vazio ou inválido.
4. Rejeitar mês diferente de 06 ou 12.
5. Rejeitar data anterior a 2020-12.
6. Localizar o intervalo na matriz.
7. Selecionar instrução, XSD, domínios, campos e críticas.
8. Registrar a versão selecionada no relatório.
9. Bloquear APTO quando a versão estiver marcada com conflito documental.
```

Pseudocódigo:

```python
if data_base < "2020-12":
    erro("VER-DATA-001")

if mes not in {"06", "12"}:
    erro("VER-DATA-002")

if "2020-12" <= data_base < "2025-06":
    return "DRO_2020_12"

if "2025-06" <= data_base < "2026-12":
    return "DRO_2025_06"

return "DRO_2026_12_PRESUMIDA"
```

Na implementação real, as comparações deverão usar ano e mês estruturados, e não simples texto.

---

## 9. Seleção manual de versão

A seleção manual será permitida apenas como exceção técnica.

Quando utilizada, o relatório deverá registrar:

```text
AVISO: a versão regulatória foi selecionada manualmente.
dataBase informada: ...
versão automática esperada: ...
versão manual utilizada: ...
responsável: ...
justificativa: ...
```

A seleção manual não poderá transformar uma versão incompatível em aprovada.

---

## 10. Códigos internos de validação da versão

| Código | Gravidade | Descrição |
|---|---|---|
| `VER-DATA-001` | ERRO IMPEDITIVO | `dataBase` anterior a `2020-12` |
| `VER-DATA-002` | ERRO IMPEDITIVO | mês da `dataBase` diferente de `06` ou `12` |
| `VER-DATA-003` | ERRO IMPEDITIVO | formato da `dataBase` inválido |
| `VER-SEL-001` | ERRO IMPEDITIVO | não foi possível localizar versão aplicável |
| `VER-MAN-001` | AVISO | versão selecionada manualmente |
| `VER-001` | ERRO IMPEDITIVO | instrução 12/2026 incompatível com o XSD 06/2025 fornecido |

---

## 11. Casos mínimos de teste da matriz

| Entrada `dataBase` | Resultado esperado |
|---|---|
| `2020-12` | `DRO_2020_12` |
| `2021-06` | `DRO_2020_12` |
| `2024-12` | `DRO_2020_12` |
| `2025-06` | `DRO_2025_06` |
| `2025-12` | `DRO_2025_06` |
| `2026-06` | `DRO_2025_06` |
| `2026-12` | `DRO_2026_12_PRESUMIDA` e bloqueio de APTO |
| `2027-06` | `DRO_2026_12_PRESUMIDA` e bloqueio de APTO |
| `2020-06` | erro `VER-DATA-001` |
| `2025-01` | erro `VER-DATA-002` |
| `06/2025` | normalizar para `2025-06`, caso seja uma data válida |
| `2025/06` | normalizar para `2025-06`, caso seja uma data válida |
| vazio | erro `VER-DATA-003` |

---

## 12. Resultado esperado para a planilha atual de testes

Para uma planilha cujo cabeçalho informe:

```text
dataBase = 2026-06
```

a seleção deverá ser:

```text
codigo_versao = DRO_2025_06
instrucao = 12/2020
xsd = Esquema de validação válido a partir da data-base 062025.xsd
status_versao = CONFIRMADA
bloqueia_apto = NÃO
```

Isso não significa que o documento esteja automaticamente apto. Significa apenas que a combinação de instrução e XSD aplicável foi identificada sem conflito de vigência.

---

## 13. Critério para futura atualização

Quando for fornecido um XSD compatível com as instruções 12/2026:

1. adicionar o arquivo à pasta `schemas/`;
2. comparar o novo XSD com o XSD 06/2025;
3. atualizar esta matriz;
4. substituir o perfil `DRO_2026_12_PRESUMIDA` por uma versão confirmada;
5. registrar os novos campos e domínios;
6. remover o bloqueio `VER-001` somente após testes;
7. criar casos de XML válido e inválido para a nova versão.

---

## 14. Estado desta etapa

```text
Etapa 1.1 — Matriz de versões: CONCLUÍDA
Próxima etapa: 1.2 — Matriz Excel → XML
```
