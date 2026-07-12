"""Configuração central de caminhos, nomes e padrões do projeto.

Este módulo concentra valores técnicos compartilhados pelas demais
partes da aplicação. Nenhum módulo deve repetir manualmente nomes de
abas, colunas, documentos regulatórios, XSDs ou padrões de saída.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


# ------------------------------------------------------------------
# Identificação geral
# ------------------------------------------------------------------

PROJECT_NAME = "Conversor XLSX para XML DRO 5050"
DOCUMENT_CODE = "5050"

XML_VERSION = "1.0"
XML_ENCODING = "UTF-8"

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------
# Diretórios
# ------------------------------------------------------------------

ASSETS_DIR = PROJECT_ROOT / "assets"
REGULATORY_ASSETS_DIR = ASSETS_DIR / "regulatory"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = PROJECT_ROOT / "output"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"

RUNTIME_DIRECTORIES: tuple[Path, ...] = (
    OUTPUT_DIR,
)

REQUIRED_PROJECT_DIRECTORIES: tuple[Path, ...] = (
    ASSETS_DIR,
    REGULATORY_ASSETS_DIR,
    CONFIG_DIR,
    DOCS_DIR,
    OUTPUT_DIR,
    SCHEMAS_DIR,
    SRC_DIR,
    SRC_DIR / "domain",
    SRC_DIR / "gui",
    SRC_DIR / "readers",
    SRC_DIR / "normalizers",
    SRC_DIR / "mappers",
    SRC_DIR / "builders",
    SRC_DIR / "validators",
    SRC_DIR / "reporters",
    SRC_DIR / "services",
    SRC_DIR / "utils",
    TESTS_DIR,
)


# ------------------------------------------------------------------
# Abas obrigatórias
# ------------------------------------------------------------------

SHEET_BASE = "Base"
SHEET_HEADER = "Cabecalho"
SHEET_SOURCE_SYSTEMS = "Sistemas_Origem"
SHEET_INTERNAL_ACCOUNTS = "Contas_Internas"

REQUIRED_SHEETS: tuple[str, ...] = (
    SHEET_BASE,
    SHEET_HEADER,
    SHEET_SOURCE_SYSTEMS,
    SHEET_INTERNAL_ACCOUNTS,
)


# ------------------------------------------------------------------
# Colunas da aba Cabecalho
# ------------------------------------------------------------------

HEADER_DOCUMENT_CODE_COLUMN = "codigoDocumento"
HEADER_DATA_BASE_COLUMN = "dataBase"
HEADER_CONGLOMERATE_CODE_COLUMN = "codigoConglomerado"
HEADER_CNPJ_COLUMN = "cnpj"
HEADER_SUBMISSION_TYPE_COLUMN = "tipoRemessa"
HEADER_ACCUMULATED_PROVISION_OPTION_COLUMN = (
    "opcaoPorProvisaoAcumulada"
)

REQUIRED_HEADER_COLUMNS: tuple[str, ...] = (
    HEADER_DATA_BASE_COLUMN,
    HEADER_CONGLOMERATE_CODE_COLUMN,
    HEADER_CNPJ_COLUMN,
    HEADER_SUBMISSION_TYPE_COLUMN,
    HEADER_ACCUMULATED_PROVISION_OPTION_COLUMN,
)

OPTIONAL_HEADER_COLUMNS: tuple[str, ...] = (
    HEADER_DOCUMENT_CODE_COLUMN,
)

RECOGNIZED_HEADER_COLUMNS: tuple[str, ...] = (
    HEADER_DOCUMENT_CODE_COLUMN,
    *REQUIRED_HEADER_COLUMNS,
)


# ------------------------------------------------------------------
# Colunas da aba Base
# ------------------------------------------------------------------

BASE_METADATA_COLUMNS: tuple[str, ...] = (
    "Source.Name",
)

BASE_EVENT_COLUMNS: tuple[str, ...] = (
    "idEvento",
    "categoriaNivel1",
    "categoriaNivel2",
    "tipoAvaliacao",
    "unidadeNegocio",
    "dataDescoberta",
    "dataOcorrencia",
    "totalPerdaEfetiva",
    "totalProvisao",
    "totalRecuperado",
    "valorTotalRisco",
    "naturezaContingencia",
    "codSistemaOrigem",
    "codigoEventoOrigem",
    "descricaoEvento",
    "riscoAssociado",
    "ligacaoRiscoSocioambiental",
    "ligadoRiscoCibernetico",
    "negocioDescontinuado",
    "idBacen",
)

BASE_PROBABILITY_COLUMNS: tuple[str, ...] = (
    "probabilidadePerda",
    "valorRisco",
)

BASE_ACCOUNTING_COLUMNS: tuple[str, ...] = (
    "dataContabilizacao",
    "contaBalAnaliticoDebito",
    "contaBalAnaliticoCredito",
    "contaCosifDebito",
    "contaCosifCredito",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
    "fonteRecuperacao",
)

BASE_FUTURE_COLUMNS: tuple[str, ...] = (
    "idEventoAgregador",
    "dataExclusao",
    "motivoExclusao",
)

BASE_CONFIRMED_REQUIRED_COLUMNS: tuple[str, ...] = (
    *BASE_METADATA_COLUMNS,
    *BASE_EVENT_COLUMNS,
    *BASE_PROBABILITY_COLUMNS,
    *BASE_ACCOUNTING_COLUMNS,
)

BASE_ALL_COLUMNS: tuple[str, ...] = (
    *BASE_CONFIRMED_REQUIRED_COLUMNS,
    *BASE_FUTURE_COLUMNS,
)

BASE_KNOWN_COLUMN_ALIASES: dict[str, str] = {
    "ligadoRiscoSocioambiental": (
        "ligacaoRiscoSocioambiental"
    ),
    "ligadoRiscoSocioAmbiental": (
        "ligacaoRiscoSocioambiental"
    ),
    "idEventoAgreagdor": "idEventoAgregador",
}


# ------------------------------------------------------------------
# Colunas das tabelas auxiliares
# ------------------------------------------------------------------

SOURCE_SYSTEM_CODE_COLUMN = "codigoSistema"
SOURCE_SYSTEM_NAME_COLUMN = "nomeSistema"

REQUIRED_SOURCE_SYSTEM_COLUMNS: tuple[str, ...] = (
    SOURCE_SYSTEM_CODE_COLUMN,
    SOURCE_SYSTEM_NAME_COLUMN,
)

INTERNAL_ACCOUNT_CODE_COLUMN = "codigoConta"
INTERNAL_ACCOUNT_NAME_COLUMN = "nomeConta"

REQUIRED_INTERNAL_ACCOUNT_COLUMNS: tuple[str, ...] = (
    INTERNAL_ACCOUNT_CODE_COLUMN,
    INTERNAL_ACCOUNT_NAME_COLUMN,
)


# ------------------------------------------------------------------
# Instruções oficiais
# ------------------------------------------------------------------

INSTRUCTION_2020_FILENAME = (
    "instrucoes_preenchimento_2020_12.pdf"
)
INSTRUCTION_2026_FILENAME = (
    "instrucoes_preenchimento_2026_12.pdf"
)

INSTRUCTION_2020_PATH = (
    REGULATORY_ASSETS_DIR / INSTRUCTION_2020_FILENAME
)
INSTRUCTION_2026_PATH = (
    REGULATORY_ASSETS_DIR / INSTRUCTION_2026_FILENAME
)


PRE_PROCESSING_CRITICS_FILENAME = (
    "criticas_pre_processamento_5050.xlsx"
)
PRE_PROCESSING_CRITICS_PATH = (
    REGULATORY_ASSETS_DIR
    / PRE_PROCESSING_CRITICS_FILENAME
)


POST_PROCESSING_CRITICS_FILENAME = (
    "criticas_pos_processamento_5050.xlsx"
)
POST_PROCESSING_CRITICS_PATH = (
    REGULATORY_ASSETS_DIR
    / POST_PROCESSING_CRITICS_FILENAME
)


# ------------------------------------------------------------------
# Esquemas XSD
# ------------------------------------------------------------------

XSD_2020_FILENAME = "dro_5050_2020_12.xsd"
XSD_2025_FILENAME = "dro_5050_2025_06.xsd"

XSD_2020_PATH = SCHEMAS_DIR / XSD_2020_FILENAME
XSD_2025_PATH = SCHEMAS_DIR / XSD_2025_FILENAME

XSD_PATH_BY_PROFILE: dict[str, Path] = {
    "DRO_2020_12": XSD_2020_PATH,
    "DRO_2025_06": XSD_2025_PATH,
    "DRO_2026_12_PRESUMIDA": XSD_2025_PATH,
}


# ------------------------------------------------------------------
# Documentação obrigatória
# ------------------------------------------------------------------

REQUIRED_DOCUMENT_PATHS: tuple[Path, ...] = (
    DOCS_DIR / "matriz_versoes.md",
    DOCS_DIR / "matriz_campos.md",
    DOCS_DIR / "matriz_criticas.md",
    DOCS_DIR / "conflitos_documentais.md",
    DOCS_DIR / "dependencias.md",
    DOCS_DIR / "configuracao.md",
    DOCS_DIR / "leitor_excel.md",
    DOCS_DIR / "leitor_cabecalho.md",
    DOCS_DIR / "normalizacao_cabecalho.md",
    DOCS_DIR / "selecao_versao.md",
    DOCS_DIR / "normalizadores_base.md",
    DOCS_DIR / "validacao_estrutura_base.md",
    DOCS_DIR / "normalizacao_linhas_base.md",
    DOCS_DIR / "validacao_linhas_base.md",
    DOCS_DIR / "agrupamento_eventos.md",
    DOCS_DIR / "validacao_financeira_eventos.md",
    DOCS_DIR / "validacao_tabelas_referencia.md",
    DOCS_DIR / "construcao_objetos_documento.md",
    DOCS_DIR / "geracao_xml.md",
    DOCS_DIR / "validacao_xsd.md",
    DOCS_DIR / "criticas_pre_processamento.md",
    DOCS_DIR / "criticas_pos_processamento.md",
    DOCS_DIR / "relatorios_execucao.md",
    DOCS_DIR / "servico_conversao.md",
    DOCS_DIR / "interface_desktop.md",
)

REQUIRED_STATIC_FILES: tuple[Path, ...] = (
    *REQUIRED_DOCUMENT_PATHS,
    INSTRUCTION_2020_PATH,
    INSTRUCTION_2026_PATH,
    PRE_PROCESSING_CRITICS_PATH,
    POST_PROCESSING_CRITICS_PATH,
    XSD_2020_PATH,
    XSD_2025_PATH,
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-dev.txt",
)


# ------------------------------------------------------------------
# Padrões de saída
# ------------------------------------------------------------------

XML_FILENAME_TEMPLATE = "DRO_5050_{data_base}.xml"
XML_NOT_APT_FILENAME_TEMPLATE = (
    "DRO_5050_{data_base}_NAO_APTO.xml"
)

REPORT_XLSX_FILENAME_TEMPLATE = (
    "Relatorio_DRO_5050_{data_base}.xlsx"
)
_DATA_BASE_PATTERN = re.compile(
    r"^\d{4}-(06|12)$"
)


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    """Visão consolidada das configurações principais."""

    project_name: str = PROJECT_NAME
    document_code: str = DOCUMENT_CODE
    xml_version: str = XML_VERSION
    xml_encoding: str = XML_ENCODING
    project_root: Path = PROJECT_ROOT
    output_dir: Path = OUTPUT_DIR
    schemas_dir: Path = SCHEMAS_DIR
    regulatory_assets_dir: Path = (
        REGULATORY_ASSETS_DIR
    )
    pre_processing_critics_path: Path = (
        PRE_PROCESSING_CRITICS_PATH
    )
    post_processing_critics_path: Path = (
        POST_PROCESSING_CRITICS_PATH
    )
    required_sheets: tuple[str, ...] = REQUIRED_SHEETS
    required_header_columns: tuple[str, ...] = (
        REQUIRED_HEADER_COLUMNS
    )
    base_confirmed_required_columns: tuple[str, ...] = (
        BASE_CONFIRMED_REQUIRED_COLUMNS
    )
    base_future_columns: tuple[str, ...] = (
        BASE_FUTURE_COLUMNS
    )
    required_source_system_columns: tuple[str, ...] = (
        REQUIRED_SOURCE_SYSTEM_COLUMNS
    )
    required_internal_account_columns: tuple[str, ...] = (
        REQUIRED_INTERNAL_ACCOUNT_COLUMNS
    )


SETTINGS = ProjectSettings()


def validate_data_base(data_base: str) -> str:
    """Valida a forma básica ``AAAA-06`` ou ``AAAA-12``."""

    normalized = str(data_base).strip()

    if not _DATA_BASE_PATTERN.fullmatch(normalized):
        raise ValueError(
            "dataBase inválida. Use AAAA-06 ou AAAA-12."
        )

    return normalized


def build_xml_filename(
    data_base: str,
    *,
    apt_for_submission: bool = True,
) -> str:
    """Monta o nome do arquivo XML."""

    normalized = validate_data_base(data_base)
    template = (
        XML_FILENAME_TEMPLATE
        if apt_for_submission
        else XML_NOT_APT_FILENAME_TEMPLATE
    )
    return template.format(data_base=normalized)


def build_report_xlsx_filename(
    data_base: str,
) -> str:
    """Monta o nome do relatório Excel."""

    normalized = validate_data_base(data_base)
    return REPORT_XLSX_FILENAME_TEMPLATE.format(
        data_base=normalized
    )


def ensure_runtime_directories() -> None:
    """Cria as pastas de saída que podem ser apagadas."""

    for directory in RUNTIME_DIRECTORIES:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def find_missing_project_paths() -> list[Path]:
    """Retorna diretórios ou arquivos obrigatórios ausentes."""

    missing: list[Path] = []

    for directory in REQUIRED_PROJECT_DIRECTORIES:
        if not directory.is_dir():
            missing.append(directory)

    for file_path in REQUIRED_STATIC_FILES:
        if not file_path.is_file():
            missing.append(file_path)

    return missing


def relative_to_project(path: Path) -> str:
    """Retorna caminho legível relativo à raiz."""

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
