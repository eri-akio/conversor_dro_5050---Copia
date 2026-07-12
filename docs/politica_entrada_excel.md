# Política de entrada Excel

## 1. Objetivo

Este documento define o comportamento do Conversor DRO 5050 para fórmulas,
números e valores monetários lidos de arquivos `.xlsx`. A política é
conservadora: nenhum valor inválido é convertido silenciosamente em zero e o
projeto não calcula fórmulas do Excel.

## 2. Leitura das fórmulas

O arquivo deve ser aberto duas vezes com `openpyxl`:

```python
load_workbook(data_only=False)
load_workbook(data_only=True)
```

A primeira leitura identifica e preserva a fórmula original. A segunda obtém
o último resultado calculado e armazenado no arquivo pelo Excel ou por outro
aplicativo compatível.

O projeto não implementa um motor de cálculo de fórmulas. Quando uma fórmula
não possuir resultado armazenado, a conversão deve produzir erro impeditivo:

```text
A célula contém fórmula, mas não possui resultado calculado armazenado.
Abra a planilha no Excel, recalcule e salve antes da conversão.
```

## 3. Campos de identificação

Fórmulas são proibidas nos campos abaixo, mesmo quando existir resultado
armazenado:

```text
idEvento
idEventoAgregador
idBacen
codigoEventoOrigem
codSistemaOrigem
codigoSistema
codigoConta
codigoConglomerado
cnpj
contaBalAnaliticoDebito
contaBalAnaliticoCredito
contaCosifDebito
contaCosifCredito
```

Resultado: erro impeditivo. A proibição evita perda de zeros à esquerda,
alteração de códigos e dependência indireta de cálculo.

## 4. Campos monetários

Fórmulas são permitidas somente nos campos monetários conhecidos pelo modelo
quando todas as condições forem atendidas:

- existir resultado calculado armazenado;
- o resultado ser numérico e finito;
- a conversão para `Decimal` preservar o valor disponível;
- o valor respeitar a escala máxima de duas casas decimais;
- a parte inteira respeitar o limite configurado para o campo.

Para toda fórmula aceita, registrar fórmula original, resultado utilizado,
aba, linha, coluna e aviso de utilização do resultado armazenado.

## 5. Campos de data

Fórmulas são permitidas nos campos de data somente quando existir resultado
armazenado que possa ser validado pelo normalizador de datas. Fórmula sem
resultado ou com resultado inválido é erro impeditivo.

## 6. Demais campos

Por política conservadora, fórmulas em campos que não sejam monetários nem de
data são proibidas. Uma nova exceção só pode ser incluída após documentação e
testes específicos.

## 7. Representação monetária

Toda conversão financeira utiliza `Decimal`. `float` nunca é utilizado como
resultado normalizado nem para arredondamento financeiro.

Formatos textuais aceitos:

| Entrada | Normalização |
|---|---:|
| `1427` | `1427.00` |
| `1427,98` | `1427.98` |
| `1427.98` | `1427.98` |
| `1.427,98` | `1427.98` |
| `1,427.98` | `1427.98` |
| `1.552.165,46` | `1552165.46` |
| `-210,00` | `-210.00` |
| `+210,00` | `210.00` |
| `0` | `0.00` |
| `0,00` | `0.00` |
| `(210,00)` | `-210.00` |
| `R$ 1.427,98` | `1427.98` |

Também são aceitos números inteiros, decimais e `Decimal` nativos quando
respeitarem precisão, escala e finitude.

## 8. Símbolo monetário

Somente o prefixo `R$` é aceito. Ele deve aparecer uma única vez no início,
seguido opcionalmente por espaços. A remoção deve gerar aviso com a regra:

```text
REMOCAO_SIMBOLO_BRL
```

Outros códigos ou símbolos monetários são rejeitados. Também são rejeitados
símbolos repetidos, símbolos no meio ou no fim do valor e combinações de `R$`
com parênteses contábeis.

## 9. Parênteses contábeis

Um único par externo de parênteses representa valor negativo:

```text
(210,00) -> -210.00
```

O formato é aceito somente quando não existe outro sinal, símbolo monetário,
par adicional ou texto fora dos parênteses. A conversão deve registrar:

```text
CONVERSAO_PARENTESES_CONTABEIS
```

## 10. Valores ambíguos

Os textos abaixo são ambíguos e devem ser rejeitados:

```text
1.234
1,234
```

Mensagem: `Separador monetário ambíguo`.

A restrição não se aplica a células numéricas nativas do Excel, pois o tipo
interno elimina a ambiguidade textual.

## 11. Notação científica e precisão

Texto em notação científica, como `1.23E+5`, é rejeitado.

Número nativo do Excel somente é aceito quando sua representação disponível
possui no máximo 15 dígitos significativos e a conversão por `Decimal(str())`
mantém escala válida. Valores com risco de precisão geram erro específico e
nunca são arredondados silenciosamente.

## 12. Escala monetária

Valores com mais de duas casas decimais são rejeitados:

```text
100,123
```

Mensagem: `Quantidade de casas decimais superior à permitida`.

O sistema não arredonda sem regra regulatória ou configuração explícita.

## 13. Valores inválidos

Exemplos rejeitados:

```text
1.222,111,11
1,2,3
--100
+-100
R$R$100
ABC
USD 100
€ 100
```

## 14. Registro da normalização

Toda transformação não trivial deve permitir rastrear:

```text
aba
linha
coluna
valor_original
valor_normalizado
regra_aplicada
status
mensagem
```

Fórmulas aceitas também registram o texto da fórmula e o resultado armazenado
utilizado. Valor inválido permanece inválido; nunca é substituído por `0.00`
para permitir a geração do XML.

