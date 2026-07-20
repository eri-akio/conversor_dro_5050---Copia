# Leitura e validação das tabelas de sistemas e contas internas

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.7  
**Arquivos principais:**

```text
src/readers/reference_tables_reader.py
src/validators/reference_tables_validator.py
src/domain/reference_tables.py
```

## 1. Objetivo

Ler e validar sistemas e contas internas a partir de uma das duas origens:

```text
formato legado: Sistemas_Origem + Contas_Internas
formato atual: colunas embutidas na Base
```

Essas abas alimentam os blocos XML:

```text
sistemasOrigem/sistema
contasSubtitulosInternos/conta
```

Também são verificadas as referências utilizadas nos eventos e nas
contabilizações.

## 2. Estrutura esperada

### Referências embutidas na `Base`

```text
codSistemaOrigem
nomeSistemaOrigem
contaBalAnaliticoDebito
nomeContaBalAnaliticoDebito
contaBalAnaliticoCredito
nomeContaBalAnaliticoCredito
```

Os aliases `nomeSistema` e `nomeConta` do modelo operacional são aceitos
somente quando a posição deixa claro o campo de destino. Internamente eles
são convertidos para nomes únicos antes da criação de `RawRow`.

### Abas legadas

### `Sistemas_Origem`

```text
codigoSistema
nomeSistema
```

### `Contas_Internas`

```text
codigoConta
nomeConta
```

Os dois blocos devem possuir ao menos um registro, pois os XSDs fornecidos
exigem um ou mais elementos `sistema` e `conta`.

Colunas adicionais geram aviso e não são enviadas ao XML.

## 3. Regras de formato

### `codigoSistema`

Pelo XSD:

```text
alfanumérico
1 a 10 caracteres
```

O valor é tratado como texto e não é convertido para maiúsculas.

### `nomeSistema`

Pelo XSD:

```text
1 a 70 caracteres
somente A-Z, a-z, 0-9 e espaço
```

### `codigoConta`

Pelo XSD:

```text
1 a 24 dígitos
```

O valor deve permanecer textual para preservar zeros à esquerda.

### `nomeConta`

Pelo XSD:

```text
1 a 70 caracteres
somente A-Z, a-z, 0-9 e espaço
```

Os nomes não são truncados, transliterados nem têm acentos removidos de forma
automática.

## 4. Unicidade

São executadas:

```text
DRO001102 — unicidade de codigoSistema
DRO001101 — unicidade de codigoConta
```

Nas abas legadas, código repetido é erro, mesmo quando o nome também é igual.

Na `Base`, a repetição do mesmo par código e nome é esperada e é deduplicada.
O mesmo código associado a nomes diferentes continua sendo erro.

Quando o mesmo código possui nomes diferentes, o sistema não escolhe um deles.

## 5. Referências usadas pela Base

Após o agrupamento dos eventos são executadas:

```text
DRO001321 — codSistemaOrigem deve possuir nome único e válido
DRO001401 — contaBalAnaliticoDebito deve possuir nome único e válido
DRO001402 — contaBalAnaliticoCredito deve possuir nome único e válido
```

A regra de sistema é avaliada uma vez por evento lógico.

As regras de conta são avaliadas em cada contabilização preservada.

## 6. Cadastro duplicado ou inválido

Quando o código utilizado existe, mas aparece duplicado ou com nome inválido,
a referência fica:

```text
REGRA NÃO EXECUTADA
```

A regra de unicidade ou formato da tabela continua reprovada. Isso evita tratar
um cadastro ambíguo como válido.

## 7. Códigos não utilizados

Códigos válidos e únicos que não aparecem no documento atual são listados como
informação:

```text
TBL-SIS-INFO-001
TBL-CONTA-INFO-001
```

Eles não bloqueiam o processamento, pois as fontes fornecidas não definem uma
crítica impeditiva para cadastro excedente.

## 8. Fórmulas

Fórmulas em código ou nome geram:

```text
TBL-FORMULA-001 — ERRO
```

O programa não usa o valor armazenado em cache pelo Excel como se fosse um
resultado calculado e confiável.

## 9. Conflitos documentais registrados

```text
CONF-025 — tamanho de codigoSistema
CONF-026 — caracteres permitidos nos nomes
CONF-027 — seletor xs:key não aponta para os elementos reais
```

A decisão aplicada segue a precedência do projeto:

```text
XSD > instruções > críticas > exemplos
```

## 10. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 11. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_reference_tables.py -v
```

## 12. Próxima etapa

```text
5.8 — Construir os objetos finais do documento para geração do XML
```
