from __future__ import annotations

from .ask_selects import CA_CERT_MODE_DEFAULT, CA_CERT_MODE_OPTIONS
from .database import AskSelect, FieldDef, PromptFields, validate_non_empty, validate_port


PRIVX_FIELDS = [
    FieldDef(
        key="PRIVX_HOSTNAME",
        label="PrivX hostname",
        description="Hostname of the PrivX server.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="PRIVX_PORT",
        label="PrivX port",
        description="HTTPS port used for PrivX API/UI access.",
        validator=validate_port,
    ),
    FieldDef(
        key="PRIVX_API_OAUTH_CLIENT_ID",
        label="PrivX API OAuth client id",
        description="OAuth client id for external PrivX API access.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="PRIVX_API_OAUTH_CLIENT_SECRET",
        label="PrivX API OAuth client secret",
        description="OAuth client secret for external PrivX API access.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="PRIVX_API_CLIENT_ID",
        label="PrivX API client id",
        description="PrivX API client id used by the Reporter sync/reporting integrations.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="PRIVX_API_CLIENT_SECRET",
        label="PrivX API client secret",
        description="PrivX API client secret used by the Reporter sync/reporting integrations.",
        validator=validate_non_empty,
    ),
]

PRIVX_OPTIONAL_FIELDS = [
    FieldDef(
        key="PRIVX_CA_CERT",
        label="PrivX CA certificate (PEM content)",
        description="Optional TLS trust anchor certificate. Leave empty to skip custom CA trust.",
        validator=validate_non_empty,
    ),
]

PRIVX_OUTPUT_ORDER = [
    "PRIVX_HOSTNAME",
    "PRIVX_PORT",
    "PRIVX_API_OAUTH_CLIENT_ID",
    "PRIVX_API_OAUTH_CLIENT_SECRET",
    "PRIVX_API_CLIENT_ID",
    "PRIVX_API_CLIENT_SECRET",
    "PRIVX_CA_CERT",
]

PRIVX_DEFAULT_OVERRIDES = {
    "PRIVX_HOSTNAME": "",
    "PRIVX_CA_CERT": "",
}


def collect_privx_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    ask_select: AskSelect,
) -> dict[str, str]:
    print("\nConfigure PrivX values:")
    values = prompt_fields(PRIVX_FIELDS, defaults)

    print("\nPrivX CA certificate (TLS Trust Anchor): choose whether to set it now or leave it empty.")
    print('Find the certificate in PrivX at "administration -> deployment -> API clients"')
    ca_cert_mode = ask_select(
        "How should PRIVX_CA_CERT be handled?",
        options=CA_CERT_MODE_OPTIONS,
        default_value=CA_CERT_MODE_DEFAULT,
    )

    if ca_cert_mode == "set":
        values.update(prompt_fields(PRIVX_OPTIONAL_FIELDS, defaults))

    return values
