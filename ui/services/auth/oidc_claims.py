from __future__ import annotations

from typing import Any

import jwt


def extract_id_token_exp(id_token: str | None) -> int | None:
    """Return ``exp`` claim from an ID token without signature verification."""
    if not id_token:
        return None

    try:
        claims: dict[str, Any] = jwt.decode(
            id_token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except Exception:
        return None

    exp = claims.get("exp")
    if isinstance(exp, int) and exp > 0:
        return exp
    if isinstance(exp, float) and exp > 0:
        return int(exp)
    return None
