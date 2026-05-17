import sys

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    thinking_budget: int = 8192  # 0 = disabled; gemini-2.5-flash max 24576
    rate_limit_max: int = 10     # requests per window per IP
    rate_limit_window: float = 60.0  # seconds

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


try:
    settings = Settings()
except Exception as exc:
    print(f"[FATAL] Yapılandırma hatası: {exc}", file=sys.stderr)
    print("[FATAL] GEMINI_API_KEY environment variable'ı set edilmemiş.", file=sys.stderr)
    sys.exit(1)
