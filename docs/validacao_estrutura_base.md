# Validação estrutural da aba `Base`

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo principal:** `src/validators/base_structure_validator.py`  
**Etapa:** 5.2 — Estrutura e colunas da aba `Base`

---

## 1. Objetivo

Confirmar que a aba `Base` possui as colunas necessárias para o perfil
regulatório selecionado.

Esta etapa não valida o conteúdo das células.

Ainda não são avaliados:

- campos obrigatórios por linha;
- domínios;
- datas e valores;
- conflitos entre linhas do mesmo evento;
- probabilidades;
- contabilizações;
- totais;
- críticas regulatórias.

---

## 2. Grupos de colunas

### Metadado

```text
Source.Name
```

Essa coluna pertence ao contrato da entrada, mas não será enviada ao
XML.

### Identificação e atributos do evento

```text
idEvento
categoriaNivel1
categoriaNivel2
tipoAvaliacao
unidadeNegocio
dataDescoberta
dataOcorrencia
totalPerdaEfetiva
totalProvisao
totalRecuperado
valorTotalRisco
naturezaContingencia
codSistemaOrigem
codigoEventoOrigem
descricaoEvento
riscoAssociado
ligacaoRiscoSocioambiental
ligadoRiscoCibernetico
negocioDescontinuado
idBacen
```

### Probabilidades

```text
probabilidadePerda
valorRisco
```

### Contabilizações

```text
dataContabilizacao
contaBalAnaliticoDebito
contaBalAnaliticoCredito
contaCosifDebito
contaCosifCredito
valorPerdaEfetiva
valorProvisao
valorRecuperacao
fonteRecuperacao
```

### Campos introduzidos nas instruções 12/2026

```text
idEventoAgregador
dataExclusao
motivoExclusao
```

---

## 3. Contrato por versão

### Perfis confirmados até `2026-06`

Para:

```text
DRO_2020_12
DRO_2025_06
```

são obrigatórias as 32 colunas do leiaute confirmado.

As três colunas de 12/2026 podem estar presentes, mas são opcionais na
estrutura das versões anteriores.

Quando estiverem presentes, o sistema registra:

```text
BASE-INFO-001
```

Isso não autoriza sua inclusão no XML antigo.

### Perfil `DRO_2026_12_PRESUMIDA`

Para a estrutura de entrada são esperadas as 35 colunas.

Os campos continuam condicionais no nível de célula. Exigir a coluna
não significa exigir valor em todas as linhas.

O perfil permanece impedido de gerar resultado `APTO` porque o XSD
06/2025 fornecido não suporta integralmente as instruções 12/2026.

---

## 4. Ordem das colunas

A ordem física das colunas não é obrigatória.

O sistema identifica as colunas pelo nome exato. Portanto, esta ordem
é aceita:

```text
idEvento | Source.Name | categoriaNivel1
```

desde que todas as colunas obrigatórias existam.

---

## 5. Colunas adicionais

Colunas sem mapeamento não impedem a validação estrutural.

Elas produzem:

```text
BASE-AVISO-001
```

e são ignoradas nesta etapa.

Nenhuma coluna adicional será enviada ao XML sem mapeamento definido.

---

## 6. Grafias conhecidas

O sistema reconhece algumas grafias que podem indicar erro, mas não as
corrige silenciosamente:

| Encontrada | Esperada |
|---|---|
| `ligadoRiscoSocioambiental` | `ligacaoRiscoSocioambiental` |
| `ligadoRiscoSocioAmbiental` | `ligacaoRiscoSocioambiental` |
| `idEventoAgreagdor` | `idEventoAgregador` |

A ocorrência gera:

```text
BASE-EST-003
```

Caso a coluna canônica esteja ausente e seja obrigatória, também será
gerado `BASE-EST-002`.

---

## 7. Códigos da etapa

| Código | Gravidade | Situação |
|---|---|---|
| `BASE-EST-001` | ERRO IMPEDITIVO | Aba Base sem linhas de dados |
| `BASE-EST-002` | ERRO IMPEDITIVO | Coluna obrigatória ausente |
| `BASE-EST-003` | AVISO | Alias conhecido encontrado |
| `BASE-AVISO-001` | AVISO | Coluna adicional sem mapeamento |
| `BASE-INFO-001` | INFORMAÇÃO | Colunas 12/2026 presentes em perfil anterior |
| `BASE-INFO-002` | INFORMAÇÃO | `Source.Name` reconhecida como metadado |

---

## 8. Exemplo de uso

```python
from src.readers.excel_reader import read_excel
from src.services.version_resolver import resolve_version
from src.validators.base_structure_validator import (
    validate_base_structure,
)

excel = read_excel(
    r"D:\Documentos\DRO_5050_planilha.xlsx"
)

selecao = resolve_version("2026-06")
perfil = selecao.profile

assert perfil is not None

resultado = validate_base_structure(
    excel,
    perfil,
)

print(resultado.is_valid)
print(resultado.missing_columns)
print(resultado.extra_columns)
```

---

## 9. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

O terminal apresentará:

- perfil regulatório;
- quantidade de linhas da Base;
- quantidade de colunas;
- colunas obrigatórias;
- colunas ausentes;
- colunas adicionais;
- avisos e informações.

---

## 10. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_base_structure_validator.py -v
```

---

## 11. Estado

```text
Etapa 5.2 — Estrutura e colunas da Base: CONCLUÍDA
Próxima etapa: 5.3 — Ler e normalizar cada linha da aba Base
```
