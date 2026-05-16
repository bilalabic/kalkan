"""Stage 5: log-odds fusion -> final risk score (no LLM)."""


def fuse(flags: list[dict]) -> tuple[float, str]:
    """Returns (risk_score 0-1, risk_level)."""
    raise NotImplementedError
