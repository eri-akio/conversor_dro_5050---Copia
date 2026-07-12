"""Serviços responsáveis por coordenar o fluxo da aplicação."""

from src.services.conversion_service import (
    ConversionService,
    convert_excel,
)
from src.services.final_status_service import (
    FinalStatusService,
    consolidate_final_status,
)
from src.services.event_classification_service import (
    EventClassificationService,
    classify_events,
)
from src.services.consolidated_event_calculator import (
    ConsolidatedEventCalculator,
    calculate_consolidated_events,
    resolve_semester_period,
)
from src.services.reporting_service import (
    ReportingService,
    ReportingServiceError,
    generate_reports,
)
from src.services.version_resolver import (
    VERSION_PROFILES,
    VersionResolver,
    VersionSelectionIssue,
    VersionSelectionResult,
    resolve_version,
)
from src.services.xsd_validation_service import (
    XsdValidationError,
    XsdValidationService,
    validate_generated_xml,
)
from src.services.xml_generation_service import (
    XmlGenerationError,
    XmlGenerationService,
    generate_xml,
)

__all__ = [
    "ConversionService",
    "ConsolidatedEventCalculator",
    "EventClassificationService",
    "FinalStatusService",
    "ReportingService",
    "ReportingServiceError",
    "VERSION_PROFILES",
    "VersionResolver",
    "VersionSelectionIssue",
    "VersionSelectionResult",
    "XsdValidationError",
    "XsdValidationService",
    "XmlGenerationError",
    "XmlGenerationService",
    "consolidate_final_status",
    "classify_events",
    "calculate_consolidated_events",
    "convert_excel",
    "generate_reports",
    "generate_xml",
    "validate_generated_xml",
    "resolve_version",
    "resolve_semester_period",
]
