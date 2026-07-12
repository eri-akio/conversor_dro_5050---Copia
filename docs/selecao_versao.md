# Seleção automática de instrução e XSD

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo principal:** `src/services/version_resolver.py`  
**Etapa:** 4.1 — Seleção automática pela `dataBase`

---

## 1. Regra principal

A instrução e o XSD são selecionados exclusivamente pela `dataBase`
normalizada do cabeçalho.

O sistema não:

- testa o XML nos dois XSDs para escolher o que aceitar;
- permite que a interface substitua silenciosamente a versão;
- usa a data do arquivo Excel;
- usa a data atual do computador;
- usa o nome do arquivo como versão.

---

## 2. Matriz implementada

| Perfil | Data-base inicial | Data-base final | Instrução | XSD | Situação |
|---|---:|---:|---|---|---|
| `DRO_2020_12` | `2020-12` | `2024-12` | `12/2020` | `12/2020` | Confirmada |
| `DRO_2025_06` | `2025-06` | `2026-06` | `12/2020` | `06/2025` | Confirmada |
| `DRO_2026_12_PRESUMIDA` | `2026-12` | sem final | `12/2026` | `06/2025` disponível | Conflito documental |

Os intervalos são comparados com o objeto `YearMonth`, não com texto.

---

## 3. Fontes físicas selecionadas

### Instrução 12/2020

```text
assets/regulatory/instrucoes_preenchimento_2020_12.pdf
```

### Instrução 12/2026

```text
assets/regulatory/instrucoes_preenchimento_2026_12.pdf
```

### XSD 12/2020

```text
schemas/dro_5050_2020_12.xsd
```

### XSD 06/2025

```text
schemas/dro_5050_2025_06.xsd
```

A aplicação verifica se os arquivos selecionados existem. Arquivo
regulatório ausente gera `FALHA TÉCNICA`.

---

## 4. Perfil confirmado

Para `dataBase = 2026-06`:

```text
perfil: DRO_2025_06
instrução: 12/2020
XSD: 06/2025
situação: CONFIRMADA
bloqueia APTO: não
```

A seleção confirmada não significa que os dados já estejam aptos. Ela
apenas confirma a combinação documental usada nas próximas etapas.

---

## 5. Perfil novo presumido

Para `dataBase >= 2026-12`:

```text
perfil: DRO_2026_12_PRESUMIDA
instrução: 12/2026
XSD disponível: 06/2025
situação: CONFLITO_DOCUMENTAL
bloqueia APTO: sim
```

O XSD 06/2025 não contém todos os campos e blocos apresentados nas
instruções 12/2026.

O serviço retorna:

```text
VER-001 — ERRO IMPEDITIVO
```

A execução poderá continuar para diagnóstico, desde que os arquivos
físicos existam, mas o resultado final não poderá ser `APTO`.

---

## 6. Objetos criados

### `YearMonth`

Representa ano e mês de maneira ordenável:

```python
YearMonth(2025, 6) < YearMonth(2026, 12)
```

### `RegulatoryVersion`

Contém:

```text
código do perfil
início e fim da vigência
versão e caminho da instrução
versão e caminho do XSD
perfil de leiaute
situação documental
conflitos
bloqueio de aptidão
```

### `VersionSelectionResult`

Informa:

```text
perfil selecionado
ocorrências
is_resolved
is_confirmed
blocks_apt
has_technical_failure
can_continue_diagnostic
```

---

## 7. Códigos desta etapa

| Código | Gravidade | Significado |
|---|---|---|
| `VER-DATA-001` | ERRO IMPEDITIVO | Data-base anterior a `2020-12` |
| `VER-DATA-002` | ERRO IMPEDITIVO | Mês diferente de `06` ou `12` |
| `VER-DATA-003` | ERRO IMPEDITIVO | Formato não normalizado |
| `VER-SEL-001` | ERRO IMPEDITIVO | Nenhum perfil aplicável |
| `VER-ARQ-001` | FALHA TÉCNICA | Instrução ou XSD ausente |
| `VER-001` | ERRO IMPEDITIVO | Conflito da versão 12/2026 |
| `VER-INFO-001` | INFORMAÇÃO | Seleção automática confirmada |

---

## 8. Seleção manual

A seleção manual não foi implementada nesta etapa.

Quando for adicionada à interface, deverá:

- ser excepcional;
- registrar a versão automática esperada;
- registrar a versão escolhida;
- exigir justificativa;
- emitir aviso;
- nunca eliminar o bloqueio causado por incompatibilidade documental.

---

## 9. Exemplo de uso

```python
from src.services.version_resolver import resolve_version

resultado = resolve_version("2026-06")

perfil = resultado.profile

print(perfil.code)
print(perfil.instruction_path)
print(perfil.xsd_path)
print(resultado.blocks_apt)
```

---

## 10. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

---

## 11. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente o versionamento:

```powershell
python -m pytest tests/test_version_resolver.py -v
```

---

## 12. Estado

```text
Etapa 4.1 — Seleção automática de versão: CONCLUÍDA
Próxima etapa: 5.1 — Criar os normalizadores reutilizáveis de datas,
valores, domínios e identificadores da Base
```
