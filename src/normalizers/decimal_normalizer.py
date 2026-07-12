"""Normalizador monetário baseado exclusivamente em ``Decimal``.

Exemplos aceitos:

- ``1.427,98``;
- ``1427,98``;
- ``1427.98``;
- ``1.552.165,46``;
- números negativos.

Valores com separadores ambíguos não são adivinhados.
"""

from __future__ import annotations

from decimal import (
    Decimal,
    InvalidOperation,
)
import math
import re
from typing import Any

from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
    valid_result,
)
from src.normalizers.null_normalizer import is_null_candidate


RULE_CODE = "NORM-DECIMAL-001"
BRL_SYMBOL_RULE_CODE = "REMOCAO_SIMBOLO_BRL"
ACCOUNTING_PARENTHESES_RULE_CODE = (
    "CONVERSAO_PARENTESES_CONTABEIS"
)
_NUMBER_TEXT_PATTERN = re.compile(
    r"^[+-]?[0-9][0-9.,]*$"
)


def normalize_decimal(
    value: Any,
    *,
    decimal_places: int = 2,
    max_integer_digits: int = 16,
    allow_negative: bool = True,
) -> NormalizationResult[Decimal]:
    """Normaliza valores sem usar ``float`` como resultado."""

    if decimal_places < 0:
        raise ValueError(
            "decimal_places não pode ser negativo."
        )

    if max_integer_digits < 1:
        raise ValueError(
            "max_integer_digits deve ser maior que zero."
        )

    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-NULO-001",
            issue_message=(
                "O valor representa ausência e não contém um número."
            ),
        )

    parsed_value: Decimal | None
    parse_issue: tuple[str, str] | None = None
    applied_rule_code = RULE_CODE

    if isinstance(value, bool):
        parsed_value = None
        parse_issue = (
            "DEC-TIPO-001",
            "Valor booleano não é aceito como valor monetário.",
        )

    elif isinstance(value, Decimal):
        parsed_value = value

    elif isinstance(value, int):
        parsed_value = Decimal(value)
        if _significant_digit_count(parsed_value) > 15:
            parsed_value = None
            parse_issue = (
                "DEC-PRECISAO-001",
                "O número nativo do Excel possui risco de perda "
                "de precisão.",
            )

    elif isinstance(value, float):
        if not math.isfinite(value):
            parsed_value = None
            parse_issue = (
                "DEC-FINITO-001",
                "O valor numérico precisa ser finito.",
            )
        else:
            parsed_value = Decimal(str(value))
            if _significant_digit_count(parsed_value) > 15:
                parsed_value = None
                parse_issue = (
                    "DEC-PRECISAO-001",
                    "O número nativo do Excel possui risco de perda "
                    "de precisão.",
                )

    elif isinstance(value, str):
        prepared, applied_rule_code, parse_issue = (
            _prepare_decimal_text(value)
        )
        if parse_issue is None:
            assert prepared is not None
            parsed_value, parse_issue = _parse_decimal_text(
                prepared,
                decimal_places=decimal_places,
            )
        else:
            parsed_value = None

    else:
        parsed_value = None
        parse_issue = (
            "DEC-TIPO-001",
            "Tipo de valor não suportado para normalização monetária.",
        )

    if parse_issue is not None:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code=parse_issue[0],
            issue_message=parse_issue[1],
        )

    assert parsed_value is not None

    if not parsed_value.is_finite():
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-FINITO-001",
            issue_message="O valor numérico precisa ser finito.",
        )

    quantum = Decimal(1).scaleb(-decimal_places)

    try:
        quantized = parsed_value.quantize(quantum)
    except InvalidOperation:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-FMT-001",
            issue_message=(
                "Não foi possível representar o valor com a escala "
                "monetária configurada."
            ),
        )

    if parsed_value != quantized:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-ESCALA-001",
            issue_message=(
                f"O valor possui mais de {decimal_places} casas "
                "decimais significativas."
            ),
        )

    if quantized == 0:
        quantized = abs(quantized)

    if not allow_negative and quantized < 0:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-SINAL-001",
            issue_message=(
                "O campo não permite valor negativo nesta regra."
            ),
        )

    serialized = format(
        quantized,
        f".{decimal_places}f",
    )
    integer_part = (
        serialized
        .lstrip("-")
        .split(".", maxsplit=1)[0]
        .lstrip("0")
    )
    integer_digits = len(integer_part or "0")

    if integer_digits > max_integer_digits:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DEC-TAMANHO-001",
            issue_message=(
                "A parte inteira ultrapassa o limite de "
                f"{max_integer_digits} dígitos."
            ),
            serialized_value=serialized,
        )

    return valid_result(
        original_value=value,
        normalized_value=quantized,
        serialized_value=serialized,
        rule_code=applied_rule_code,
        changed=_decimal_was_changed(
            original_value=value,
            serialized_value=serialized,
        ),
    )


def _prepare_decimal_text(
    value: str,
) -> tuple[
    str | None,
    str,
    tuple[str, str] | None,
]:
    text = value.strip()

    if re.search(r"\d[eE][+-]?\d", text):
        return (
            None,
            RULE_CODE,
            (
                "DEC-CIENTIFICA-001",
                "Notação científica textual não é aceita para "
                "campos monetários.",
            ),
        )

    if "R$" in text:
        if text.count("R$") != 1 or not text.startswith("R$"):
            return (
                None,
                RULE_CODE,
                (
                    "DEC-SIMBOLO-001",
                    "O símbolo monetário deve ser um único prefixo R$.",
                ),
            )

        text = text[2:].strip()
        if not text or "(" in text or ")" in text:
            return (
                None,
                RULE_CODE,
                (
                    "DEC-SIMBOLO-001",
                    "R$ não pode ser combinado com parênteses ou valor "
                    "vazio.",
                ),
            )
        return text, BRL_SYMBOL_RULE_CODE, None

    if "(" in text or ")" in text:
        valid_parentheses = (
            text.startswith("(")
            and text.endswith(")")
            and text.count("(") == 1
            and text.count(")") == 1
        )
        if not valid_parentheses:
            return (
                None,
                RULE_CODE,
                (
                    "DEC-PARENTESES-001",
                    "Os parênteses contábeis estão em formato inválido.",
                ),
            )

        inner = text[1:-1].strip()
        if not inner or inner[0] in {"+", "-"}:
            return (
                None,
                RULE_CODE,
                (
                    "DEC-PARENTESES-001",
                    "Parênteses contábeis não podem conter outro sinal.",
                ),
            )
        return (
            f"-{inner}",
            ACCOUNTING_PARENTHESES_RULE_CODE,
            None,
        )

    return text, RULE_CODE, None


def _significant_digit_count(value: Decimal) -> int:
    normalized = value.normalize()
    return len(normalized.as_tuple().digits)


def serialize_decimal(
    value: Decimal,
    *,
    decimal_places: int = 2,
) -> str:
    """Serializa um ``Decimal`` já validado."""

    quantum = Decimal(1).scaleb(-decimal_places)
    quantized = value.quantize(quantum)

    if quantized == 0:
        quantized = abs(quantized)

    return format(
        quantized,
        f".{decimal_places}f",
    )


def _parse_decimal_text(
    value: str,
    *,
    decimal_places: int,
) -> tuple[
    Decimal | None,
    tuple[str, str] | None,
]:
    text = value.strip()

    if not _NUMBER_TEXT_PATTERN.fullmatch(text):
        return (
            None,
            (
                "DEC-FMT-001",
                "O valor contém caracteres ou separadores inválidos.",
            ),
        )

    sign = ""

    if text[0] in {"+", "-"}:
        sign = text[0]
        unsigned = text[1:]
    else:
        unsigned = text

    if not unsigned:
        return (
            None,
            (
                "DEC-FMT-001",
                "O valor não contém dígitos.",
            ),
        )

    has_dot = "." in unsigned
    has_comma = "," in unsigned

    if has_dot and has_comma:
        decimal_separator = (
            "."
            if unsigned.rfind(".") > unsigned.rfind(",")
            else ","
        )
        thousands_separator = (
            ","
            if decimal_separator == "."
            else "."
        )

        if unsigned.count(decimal_separator) != 1:
            return (
                None,
                (
                    "DEC-AMB-001",
                    "Não foi possível determinar o separador decimal.",
                ),
            )

        integer_text, fraction_text = unsigned.rsplit(
            decimal_separator,
            maxsplit=1,
        )

        if not fraction_text.isdigit():
            return (
                None,
                (
                    "DEC-FMT-001",
                    "A parte decimal contém caracteres inválidos.",
                ),
            )

        if len(fraction_text) > decimal_places:
            return (
                None,
                (
                    "DEC-ESCALA-001",
                    f"O valor possui mais de {decimal_places} "
                    "casas decimais."
                ),
            )

        if not 1 <= len(fraction_text) <= decimal_places:
            return (
                None,
                (
                    "DEC-FMT-001",
                    "A parte decimal está vazia ou incompleta.",
                ),
            )

        if thousands_separator in integer_text:
            if not _valid_thousands_groups(
                integer_text,
                thousands_separator,
            ):
                return (
                    None,
                    (
                        "DEC-AMB-001",
                        "Os agrupamentos de milhar são ambíguos.",
                    ),
                )

            integer_digits = integer_text.replace(
                thousands_separator,
                "",
            )
        else:
            integer_digits = integer_text

        if not integer_digits.isdigit():
            return (
                None,
                (
                    "DEC-FMT-001",
                    "A parte inteira contém caracteres inválidos.",
                ),
            )

        canonical = (
            f"{sign}{integer_digits}.{fraction_text}"
        )

    elif has_dot or has_comma:
        separator = "." if has_dot else ","
        separator_count = unsigned.count(separator)

        if separator_count == 1:
            integer_text, right_text = unsigned.split(
                separator,
                maxsplit=1,
            )

            if (
                not integer_text.isdigit()
                or not right_text.isdigit()
            ):
                return (
                    None,
                    (
                        "DEC-FMT-001",
                        "O número possui separador em posição inválida.",
                    ),
                )

            if 1 <= len(right_text) <= decimal_places:
                canonical = (
                    f"{sign}{integer_text}.{right_text}"
                )

            elif len(right_text) == 3:
                if len(integer_text) >= 3:
                    return (
                        None,
                        (
                            "DEC-ESCALA-001",
                            f"O valor possui mais de {decimal_places} "
                            "casas decimais.",
                        ),
                    )
                return (
                    None,
                    (
                        "DEC-AMB-001",
                        "Um único separador seguido de três dígitos "
                        "pode representar milhar ou decimal."
                    ),
                )

            else:
                return (
                    None,
                    (
                        "DEC-FMT-001",
                        "Quantidade de dígitos após o separador "
                        "não é suportada."
                    ),
                )

        else:
            if not _valid_thousands_groups(
                unsigned,
                separator,
            ):
                return (
                    None,
                    (
                        "DEC-AMB-001",
                        "Os separadores repetidos não formam "
                        "grupos inequívocos de milhar."
                    ),
                )

            canonical = (
                f"{sign}{unsigned.replace(separator, '')}"
            )

    else:
        canonical = f"{sign}{unsigned}"

    try:
        return Decimal(canonical), None
    except InvalidOperation:
        return (
            None,
            (
                "DEC-FMT-001",
                "O valor não pôde ser convertido para Decimal.",
            ),
        )


def _valid_thousands_groups(
    value: str,
    separator: str,
) -> bool:
    groups = value.split(separator)

    if not groups:
        return False

    if (
        not groups[0].isdigit()
        or not 1 <= len(groups[0]) <= 3
    ):
        return False

    return all(
        group.isdigit() and len(group) == 3
        for group in groups[1:]
    )


def _decimal_was_changed(
    *,
    original_value: Any,
    serialized_value: str,
) -> bool:
    if isinstance(original_value, str):
        return original_value.strip() != serialized_value

    return True
