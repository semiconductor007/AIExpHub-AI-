"""Local, backend-only AI configuration. Reading it never contacts a provider."""

from dataclasses import dataclass, field
from functools import lru_cache
import os
from pathlib import Path

from dotenv import dotenv_values
from fastapi import HTTPException

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False
    api_key: str = field(default="", repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = ""
    timeout: int = 60
    max_tokens: int = 3000
    max_experiments: int = 10
    max_input_bytes: int = 32768
    error: str = ""

    def require_ready(self) -> None:
        if self.error:
            raise HTTPException(503, self.error)
        if not self.enabled:
            raise HTTPException(503, "AI 总结尚未启用，请在 backend/.env 配置后重启后端。")
        if not self.api_key or not self.model:
            raise HTTPException(503, "请在 backend/.env 填写 DeepSeek API Key 和模型 ID 后重启后端。")


def read_settings(path: Path = ENV_PATH) -> AISettings:
    try:
        # No expansion of other environment variables into values or prompts.
        values = {**dotenv_values(path, interpolate=False, encoding="utf-8-sig"), **os.environ}
        enabled = (values.get("AI_SUMMARY_ENABLED") or "false").strip().lower()
        if enabled not in {"true", "false"}:
            raise ValueError("AI_SUMMARY_ENABLED 应为 true 或 false")
        base = (values.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        if base != "https://api.deepseek.com":
            raise ValueError("第一版仅支持官方地址 https://api.deepseek.com")

        def number(key: str, default: int, low: int, high: int) -> int:
            try:
                result = int(values.get(key) or default)
            except (TypeError, ValueError):
                raise ValueError(f"{key} 必须为整数") from None
            if not low <= result <= high:
                raise ValueError(f"{key} 必须在 {low} 到 {high} 之间")
            return result

        return AISettings(
            enabled=enabled == "true", api_key=(values.get("DEEPSEEK_API_KEY") or "").strip(),
            base_url=base, model=(values.get("DEEPSEEK_MODEL") or "").strip(),
            timeout=number("AI_SUMMARY_TIMEOUT_SECONDS", 60, 5, 120),
            max_tokens=number("AI_SUMMARY_MAX_OUTPUT_TOKENS", 3000, 512, 8000),
            max_experiments=number("AI_SUMMARY_MAX_EXPERIMENTS", 10, 2, 10),
            max_input_bytes=number("AI_SUMMARY_MAX_INPUT_BYTES", 32768, 4096, 131072),
        )
    except OSError:
        return AISettings(error="无法读取 backend/.env，请检查本地文件权限。")
    except ValueError as exc:
        return AISettings(error=str(exc))


@lru_cache(maxsize=1)
def get_ai_settings() -> AISettings:
    return read_settings()
