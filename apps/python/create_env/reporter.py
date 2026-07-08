from __future__ import annotations

from .database import ConfigContext, FieldDef, PromptFields, validate_non_empty


def validate_positive_int(value: str) -> tuple[bool, str | None]:
    if not value.isdigit():
        return False, "Value must be numeric."
    if int(value) > 0:
        return True, None
    return False, "Value must be greater than zero."


REPORT_OUT_DIR_FIELD = FieldDef(
    key="REPORT_OUT_DIR",
    label="Report output directory",
    description="Directory where generated report files are stored.",
    validator=validate_non_empty,
)

REPORT_FIELDS = [
    FieldDef(
        key="REPORT_API_BATCH_SIZE",
        label="Report API batch size",
        description="Batch size used by report queries against PrivX APIs.",
        validator=validate_positive_int,
    ),
]

REPORTER_OUTPUT_ORDER = [
    "REPORT_API_BATCH_SIZE",
    "REPORT_OUT_DIR",
]


def collect_reporter_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    context: ConfigContext,
) -> dict[str, str]:
    print("\nConfigure report output directory (always read from the environment):")
    values = prompt_fields([REPORT_OUT_DIR_FIELD], defaults)

    if context.is_db_configured:
        return values

    print("\nConfigure report values:")
    values.update(prompt_fields(REPORT_FIELDS, defaults))
    return values
