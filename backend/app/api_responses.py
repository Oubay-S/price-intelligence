"""
api_responses.py
================
Single source of truth for the API's error envelope and the reusable
``responses=`` dictionaries that get attached to every router endpoint.

Every error response from the backend has the shape::

    {
        "error": {
            "code":    "<machine-readable string>",
            "message": "<human-readable summary>",
            "details": [...]   # optional, only for validation errors
        }
    }

The ``ErrorEnvelope`` Pydantic model below documents this contract for
Swagger so the frontend can rely on it. The ``ERR_*`` constants are the
ready-made ``responses=`` dicts — pass them straight to FastAPI route
decorators::

    @router.get("/{product_id}", responses={**ERR_404, **ERR_500})
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """One field-level error inside the envelope's ``details`` list."""

    loc: list[str | int] = Field(
        default_factory=list,
        description="Path to the offending field, e.g. ['body', 'email'].",
    )
    msg: str = Field(..., description="Human-readable validation message.")
    type: str = Field(..., description="Pydantic error code, e.g. 'value_error'.")


class ErrorBody(BaseModel):
    code: str = Field(
        ...,
        description="Machine-readable error code, e.g. 'not_found' / 'validation_error'.",
    )
    message: str = Field(..., description="Human-readable summary suitable for end users.")
    details: list[ErrorDetail] | None = Field(
        default=None,
        description="Field-level breakdown for validation errors.",
    )


class ErrorEnvelope(BaseModel):
    error: ErrorBody


# ---------------------------------------------------------------------------
# Reusable Swagger response dicts. Each constant is a single-key mapping you
# can spread into a route's ``responses=`` arg with ``**ERR_404``.
# ---------------------------------------------------------------------------

def _envelope(code: str, message: str, *, details: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = [
            {"loc": ["body", "field"], "msg": "value is not a valid X", "type": "value_error"},
        ]
    return {"error": body}


ERR_400: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ErrorEnvelope,
        "description": "Bad request — malformed input outside Pydantic validation.",
        "content": {
            "application/json": {
                "example": _envelope("bad_request", "At least one product_id is required"),
            }
        },
    }
}

ERR_401: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorEnvelope,
        "description": "Authentication failed: missing, invalid, or expired credentials.",
        "content": {
            "application/json": {
                "example": _envelope("unauthorized", "Could not validate credentials"),
            }
        },
    }
}

ERR_403: dict[int | str, dict[str, Any]] = {
    403: {
        "model": ErrorEnvelope,
        "description": "Authenticated but not authorised for this resource.",
        "content": {
            "application/json": {
                "example": _envelope("forbidden", "Admin only"),
            }
        },
    }
}

ERR_404: dict[int | str, dict[str, Any]] = {
    404: {
        "model": ErrorEnvelope,
        "description": "Resource not found.",
        "content": {
            "application/json": {
                "example": _envelope("not_found", "Product 'abc...' not found"),
            }
        },
    }
}

ERR_409: dict[int | str, dict[str, Any]] = {
    409: {
        "model": ErrorEnvelope,
        "description": "Conflict — resource already exists or violates a unique constraint.",
        "content": {
            "application/json": {
                "example": _envelope("conflict", "Email already registered"),
            }
        },
    }
}

ERR_422: dict[int | str, dict[str, Any]] = {
    422: {
        "model": ErrorEnvelope,
        "description": "Request payload failed validation.",
        "content": {
            "application/json": {
                "example": _envelope(
                    "validation_error",
                    "Request payload failed validation",
                    details=True,
                ),
            }
        },
    }
}

ERR_429: dict[int | str, dict[str, Any]] = {
    429: {
        "model": ErrorEnvelope,
        "description": "Rate limit exceeded — back off and retry later.",
        "content": {
            "application/json": {
                "example": _envelope("rate_limited", "10 per 1 minute"),
            }
        },
    }
}

ERR_500: dict[int | str, dict[str, Any]] = {
    500: {
        "model": ErrorEnvelope,
        "description": "Unhandled server error.",
        "content": {
            "application/json": {
                "example": _envelope("internal_error", "An unexpected error occurred"),
            }
        },
    }
}

ERR_502: dict[int | str, dict[str, Any]] = {
    502: {
        "model": ErrorEnvelope,
        "description": "Upstream service (BigQuery, Redis) returned an error.",
        "content": {
            "application/json": {
                "example": _envelope("upstream_error", "BigQuery error: <details>"),
            }
        },
    }
}
