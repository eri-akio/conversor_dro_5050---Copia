# Validação do XML com o XSD selecionado

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.10  
**Arquivos principais:**

```text
src/validators/xsd_validator.py
src/services/xsd_validation_service.py
src/domain/xsd_validation.py
```

## 1. Objetivo

Validar o XML gerado com o XSD selecionado automaticamente pela
`dataBase`.

O sistema não tenta todos os esquemas para descobrir qual aceita o
arquivo.

```text
dataBase
   ↓
RegulatoryVersion
   ↓
profile.xsd_path
   ↓
validação
```

## 2. XSD usado por perfil

```text
DRO_2020_12            → dro_5050_2020_12.xsd
DRO_2025_06            → dro_5050_2025_06.xsd
DRO_2026_12_PRESUMIDA  → dro_5050_2025_06.xsd
                          com bloqueio documental
```

O perfil 12/2026 continua apenas diagnóstico porque o XSD compatível
com as novas instruções não foi fornecido.

## 3. Estados da validação

```text
VÁLIDO
INVÁLIDO
FALHA TÉCNICA
```

`VÁLIDO` significa somente que a estrutura atende ao XSD selecionado.

Não significa automaticamente `APTO PARA ENVIO`, pois ainda podem
existir:

- erros de etapas anteriores;
- regras não executadas;
- conflito documental da versão;
- críticas regulatórias posteriores.

## 4. Informações dos erros

Cada erro do `lxml` é preservado com:

```text
mensagem
linha
coluna
XPath
arquivo
nível
domínio
tipo técnico
XSD utilizado
```

Exemplo:

```text
XSD-VAL-001
linha 104
/documento/eventosConsolidados
Missing child element(s). Expected is ( eventoConsolidado ).
```

## 5. XML de diagnóstico da planilha de testes

A entrada de testes não possui cálculo produtivo de eventos
consolidados.

O XML contém:

```xml
<eventosConsolidados/>
```

O XSD exige ao menos um:

```xml
<eventoConsolidado />
```

Portanto, o resultado correto é:

```text
XML bem-formado: SIM
XSD: INVÁLIDO
Resultado: NÃO APTO
```

Nenhum evento consolidado fictício é criado para fazer o arquivo
passar.

## 6. Reclassificação do nome

Um XML inicialmente candidato pode falhar no XSD.

Nesse caso:

```text
DRO_5050_AAAA-MM.xml
```

é reclassificado como:

```text
DRO_5050_AAAA-MM_NAO_APTO.xml
```

Se o nome já existir:

```text
DRO_5050_AAAA-MM_NAO_APTO_001.xml
```

A gravação é exclusiva e nenhum arquivo existente é sobrescrito.

Um XML que já foi gerado como diagnóstico permanece com seu nome
`NAO_APTO`.

## 7. Segurança de leitura

O parser XML é configurado com:

```text
resolve_entities=False
no_network=True
load_dtd=False
recover=False
huge_tree=False
```

O validador não acessa recursos de rede e não tenta recuperar XML
malformado.

## 8. Falhas técnicas

| Código | Situação |
|---|---|
| `XSD-XML-001` | XML inexistente |
| `XSD-XML-002` | XML malformado |
| `XSD-XML-003` | XML não pôde ser lido |
| `XSD-SCHEMA-001` | XSD selecionado inexistente |
| `XSD-SCHEMA-002` | XSD malformado |
| `XSD-SCHEMA-003` | XSD não pôde ser lido |
| `XSD-SCHEMA-004` | XSD não pôde ser compilado |
| `XSD-SCHEMA-005` | Falha técnica na compilação |
| `XSD-VAL-TECH-001` | Falha técnica no mecanismo de validação |
| `XSD-GEN-001` | Nenhum XML gerado para validar |
| `XSD-WRITE-001` | Falha ao reclassificar como não apto |
| `XSD-WRITE-002` | Nenhum nome livre para reclassificação |

Erros de conformidade com o esquema usam:

```text
XSD-VAL-001 — ERRO IMPEDITIVO
```

## 9. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 10. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_xsd_validation.py -v
```

## 11. Próxima etapa

```text
5.11 — Integrar e executar as críticas de pré-processamento
```
