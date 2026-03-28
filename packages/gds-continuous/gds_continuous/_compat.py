"""Optional dependency guards."""


def require_scipy() -> None:
    """Raise ImportError with install instructions if scipy is absent."""
    try:
        import scipy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "scipy is required for ODE integration. "
            "Install with: uv add gds-continuous[scipy]"
        ) from exc
