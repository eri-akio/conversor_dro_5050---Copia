# Relatório XLSX da execução

**Projeto:** Conversor XLSX → XML DRO 5050

## Saídas

Cada conversão produz somente:

```text
DRO_5050_AAAA-MM.xml
Relatorio_DRO_5050_AAAA-MM.xlsx
```

Não são criados relatório TXT, arquivo LOG nem pasta `logs`.

Quando um nome já existe, o sistema usa os sufixos `_001`, `_002` e assim
por diante, sem sobrescrever arquivos anteriores.

## Relatório Excel

O arquivo contém duas abas:

```text
Resumo
Ocorrencias
```

### Resumo

Apresenta indicadores do processamento, contagens das ocorrências e as
decisões independentes:

```text
Status local
Status XSD
Validações externas ou históricas
Resultado geral
Aptidão para envio
```

O status local possui somente `APROVADO` e `REPROVADO`. Pendências de UNICAD,
COSIF, histórico, remessa anterior ou outra fonte ficam no status consolidado
das validações externas ou históricas.

O resultado geral usa a precedência `FALHA TÉCNICA > REPROVADO > PENDENTE >
APROVADO`. Somente o resultado geral `APROVADO` produz a aptidão `APTO PARA
ENVIO`.

### Ocorrencias

Apresenta estas 12 colunas:

```text
Etapa
Linha
idEvento
Coluna
Valor Original
Valor Normalizado
Regra
Descrição da Regra
Origem
Gravidade
Status
Mensagem
```

`Gravidade` corresponde a `record.severity`, com valores como `ERRO
IMPEDITIVO`, `ERRO`, `AVISO` e `INFORMAÇÃO`. `Status` corresponde a
`record.status`, com resultados de execução como `APROVADA`, `REPROVADA`,
`PENDENTE` e `REGRA NÃO EXECUTADA`.

As contagens da aba `Resumo` são gravadas como números calculados em Python,
sem depender do recálculo de fórmulas pelo Excel.

## Execução

```powershell
python main.py "D:\dados\DRO_5050.xlsx" `
  --output-dir "D:\saidas"
```
