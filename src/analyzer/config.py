"""Configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

SUPPORTED_PROVIDERS = ("openai", "azure", "huggingface")


@dataclass
class Config:
    """Application configuration loaded from environment.

    Supported providers
    -------------------
    openai      — OpenAI API (default).  Requires OPENAI_API_KEY.
    azure       — Azure OpenAI.          Requires AZURE_OPENAI_API_KEY,
                                         AZURE_OPENAI_ENDPOINT, and
                                         AZURE_OPENAI_DEPLOYMENT.
    huggingface — HuggingFace Inference API (OpenAI-compatible endpoint).
                  Requires HF_TOKEN and HF_MODEL.
    """

    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096
    max_agent_iterations: int = 25

    # Azure-specific
    azure_endpoint: str = ""
    azure_api_version: str = "2024-02-01"
    azure_deployment: str = ""          # Azure deployment name (= model alias)

    # HuggingFace-specific
    hf_base_url: str = "https://api-inference.huggingface.co/v1"

    @classmethod
    def from_env(cls, env_file: str | None = None, provider: str | None = None) -> "Config":
        """Load configuration from environment variables and optional .env file."""
        if env_file:
            load_dotenv(env_file)
        else:
            for candidate in [Path.cwd() / ".env", Path.home() / ".env"]:
                if candidate.is_file():
                    load_dotenv(candidate)
                    break

        resolved_provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        if resolved_provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{resolved_provider}'. "
                f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}"
            )

        if resolved_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Set it as an environment variable or in a .env file."
                )
            return cls(
                provider="openai",
                api_key=api_key,
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                max_agent_iterations=int(os.getenv("MAX_AGENT_ITERATIONS", "25")),
            )

        if resolved_provider == "azure":
            api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
            if not api_key:
                raise ValueError("AZURE_OPENAI_API_KEY is not set.")
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT is not set.")
            if not deployment:
                raise ValueError("AZURE_OPENAI_DEPLOYMENT is not set.")
            return cls(
                provider="azure",
                api_key=api_key,
                model=deployment,
                azure_endpoint=endpoint,
                azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_deployment=deployment,
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                max_agent_iterations=int(os.getenv("MAX_AGENT_ITERATIONS", "25")),
            )

        # huggingface
        hf_token = os.getenv("HF_TOKEN", "")
        hf_model = os.getenv("HF_MODEL", "")
        if not hf_token:
            raise ValueError("HF_TOKEN is not set.")
        if not hf_model:
            raise ValueError(
                "HF_MODEL is not set. "
                "Set it to a model ID such as 'mistralai/Mistral-7B-Instruct-v0.3'."
            )
        return cls(
            provider="huggingface",
            api_key=hf_token,
            model=hf_model,
            hf_base_url=os.getenv(
                "HF_BASE_URL", "https://api-inference.huggingface.co/v1"
            ),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            max_agent_iterations=int(os.getenv("MAX_AGENT_ITERATIONS", "25")),
        )
