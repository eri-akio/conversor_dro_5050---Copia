# Testes de integração do pipeline DRO 5050

## Objetivo

A camada em `tests/integration/` verifica o encadeamento real entre os
componentes do conversor sem depender de uma planilha binária mantida
manualmente. As massas são criadas em diretórios temporários com `openpyxl`
e não deixam arquivos no projeto.

O escopo coberto é:

```text
Excel -> leitura -> normalização -> domínio -> agrupamento
      -> classificação -> consolidação -> XML -> XSD -> relatório Excel
```

## Organização

| Arquivo | Responsabilidade |
| --- | --- |
| `workbook_factory.py` | Cria as quatro abas obrigatórias, valores tipados, referências e fórmulas com ou sem resultado em cache. |
| `test_excel_to_domain.py` | Verifica datas, decimais, rastreabilidade de linhas, formatos monetários, domínios inválidos e política de fórmulas. |
| `test_grouping_and_consolidation.py` | Verifica agrupamento, conflito de atributos, roteamento exclusivo, semestre e reconciliação de regras adiadas. |
| `test_xml_xsd_pipeline.py` | Verifica blocos individualizado e consolidado, aliases XML, serialização monetária, versão do esquema e rejeição de XML inválido. |
| `test_full_conversion_pipeline.py` | Verifica o serviço público completo, referências ausentes, falha técnica, status separados e artefatos de saída. |

## Cenários regulatórios e técnicos

- evento individualizado e evento consolidado na mesma remessa;
- várias contabilizações preservadas com suas linhas de origem;
- conflito entre atributos do mesmo `idEvento` sem escolha arbitrária;
- consolidação total e consolidação restrita ao semestre da `dataBase`;
- sistema de origem e conta interna não cadastrados;
- valor monetário nativo, brasileiro, agrupado e com símbolo `R$`;
- escala monetária excessiva, data impossível e código fora do domínio;
- fórmula monetária com resultado salvo no arquivo;
- fórmula sem resultado salvo e fórmula proibida em identificador;
- alias regulatório `ligadoRiscoSocioAmbiental` no XML;
- XML válido para o XSD selecionado pela `dataBase`;
- XML deliberadamente inválido por ausência de atributo obrigatório;
- validações externa e histórica mantidas como `NAO_EXECUTADO` quando suas
  dependências não estão disponíveis;
- falha de leitura classificada como falha técnica;
- saída plana contendo somente XML e relatório Excel, sem `logs` e sem TXT.

## Critérios de segurança dos testes

- cada teste usa `tmp_path`, portanto não altera planilhas do usuário;
- os números são gravados como números e as datas como datas do Excel;
- identificadores e contas são gravados como texto para preservar zeros e
  precisão;
- fórmulas são gravadas como fórmulas reais no pacote XLSX;
- quando o cenário exige cache, o valor calculado é injetado no XML interno
  da planilha para reproduzir um arquivo salvo por uma aplicação de Excel;
- nenhum teste recalcula fórmulas nem presume que `openpyxl` seja um motor de
  cálculo.

## Execução

Somente a camada de integração:

```powershell
python -m pytest tests/integration -q
```

Regressão completa:

```powershell
python -m pytest -q
```

Na conclusão desta etapa, o resultado de referência foi de **423 testes
aprovados**, dos quais **22 são testes de integração programáticos**.

