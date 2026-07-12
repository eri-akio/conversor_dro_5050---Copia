# Geração do XML do Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.9  
**Arquivos principais:**

```text
src/builders/xml_builder.py
src/services/xml_generation_service.py
src/domain/xml_generation.py
```

## 1. Objetivo

Transformar `FinalDocument` em um arquivo XML 1.0, codificado em UTF-8
e bem-formado.

Esta etapa ainda não valida o arquivo contra o XSD. A validação XSD
será executada na etapa 5.10.

## 2. Hierarquia gerada

```xml
<documento>
  <eventosIndividualizados>
    <evento>
      <probabilidadesPerdas>
        <probabilidadePerda />
      </probabilidadesPerdas>
      <contabilizacoes>
        <contabilizacao />
      </contabilizacoes>
    </evento>
  </eventosIndividualizados>

  <eventosConsolidados>
    <eventoConsolidado />
  </eventosConsolidados>

  <sistemasOrigem>
    <sistema />
  </sistemasOrigem>

  <contasSubtitulosInternos>
    <conta />
  </contasSubtitulosInternos>
</documento>
```

A ordem acompanha o modelo oficial e os blocos definidos nos XSDs.

## 3. Blocos opcionais do evento

`probabilidadesPerdas` somente é criado quando o evento possui ao menos
uma probabilidade.

`contabilizacoes` somente é criado quando o evento possui ao menos uma
contabilização.

Assim, o sistema não produz contêineres vazios em blocos opcionais.

## 4. XML candidato e XML de diagnóstico

O arquivo normal somente é usado quando:

```text
build_result.is_xml_ready = True
build_result.blocks_apt = False
```

Nome:

```text
DRO_5050_AAAA-MM.xml
```

Quando existem pendências ou impedimentos, o objeto ainda pode ser
serializado para diagnóstico:

```text
DRO_5050_AAAA-MM_NAO_APTO.xml
```

O sufixo `NAO_APTO` não é removido para fazer o arquivo parecer
aprovado.

## 5. Eventos consolidados

Quando a classificação da `Base` encontra candidatos válidos, o calculador
cria um `FinalConsolidatedEvent` por categoria, em ordem crescente, com os
sete atributos exigidos pelo XSD. O gerador XML apenas serializa esses objetos.

Quando todos os eventos válidos atingem os critérios de individualização, o
modo diagnóstico pode criar:

```xml
<eventosConsolidados/>
```

Isso mantém o XML bem-formado e evidencia a ausência do bloco
obrigatório. O arquivo continuará inválido no XSD, como esperado, e
será identificado como `NAO_APTO`.

Nenhum evento consolidado fictício é criado.

## 6. Escapamento XML

A biblioteca `lxml` trata automaticamente caracteres especiais.

Exemplo de valor:

```text
Falha & perda <teste>
```

No arquivo:

```xml
Falha &amp; perda &lt;teste&gt;
```

Ao ler o XML, o valor original é recuperado.

## 7. Campos não suportados

Os dados preservados em `UnsupportedProfileValue` não são inseridos em
tags ou atributos inexistentes.

Eles permanecem no resultado da montagem e nos relatórios futuros.

## 8. Não sobrescrever arquivos

O gerador utiliza criação exclusiva.

Quando o arquivo já existe:

```text
DRO_5050_2026-06_NAO_APTO.xml
```

é criado:

```text
DRO_5050_2026-06_NAO_APTO_001.xml
```

Em nova colisão:

```text
DRO_5050_2026-06_NAO_APTO_002.xml
```

O arquivo anterior nunca é substituído silenciosamente.

## 9. Resultado da geração

`XmlGenerationResult` informa:

```text
output_path
requested_filename
actual_filename
mode
bytes_written
collision_index
well_formed
element_counts
build_issue_codes
issues
```

Modos:

```text
CANDIDATO_A_VALIDACAO
DIAGNOSTICO_NAO_APTO
```

O modo candidato ainda não significa `APTO PARA ENVIO`, pois falta a
validação XSD e as demais etapas regulatórias.

## 10. Falhas técnicas

Códigos implementados:

| Código | Situação |
|---|---|
| `XML-BUILD-001` | Erro ao criar a árvore |
| `XML-BUILD-002` | Resultado não bem-formado |
| `XML-GEN-001` | Objeto final inexistente |
| `XML-WRITE-001` | Pasta de saída não pôde ser criada |
| `XML-WRITE-002` | Caminho de saída não é pasta |
| `XML-WRITE-003` | Erro ao gravar o arquivo |
| `XML-WRITE-004` | Não foi encontrado nome livre |

## 11. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

O XML será gravado em:

```text
output/
```

## 12. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_xml_generation.py -v
```

## 13. Próxima etapa

```text
5.10 — Validar o XML com o XSD selecionado
```
