"""Optional dependency guards."""


def require_sympy() -> None:
    """Raise ImportError with install instructions if sympy is absent."""
    try:
        import sympy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "sympy is required for symbolic operations. "
            "Install with: uv add gds-symbolic[sympy]"
        ) from exc
