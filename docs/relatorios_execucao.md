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

Apresenta resultado final, mensagem, indicadores do processamento, contagens
das ocorrências e os quatro diagnósticos independentes:

```text
Status local
Status XSD
Status externo
Status histórico
```

### Ocorrencias

Apresenta estas 19 colunas:

```text
Resultado Final
Etapa
Aba
Linha
idEvento
Coluna
Valor Original
Valor Normalizado
Regra
Descrição da Regra
Origem
Versão
Gravidade
Status
Sugestão
Mensagem
Dependência
Escopo
Resultado Definitivo
```

Para regras adiadas, `Status` preserva o valor `ADIADA` e `Resultado
Definitivo` apresenta a decisão produzida no nível do evento.

## Execução

```powershell
python main.py "D:\dados\DRO_5050.xlsx" `
  --output-dir "D:\saidas"
```
