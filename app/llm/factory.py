from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings
from app.exceptions import AppError
from app.llm.config import LLMProvider


class LLMFactory:
    @staticmethod
    def create(
        provider: str | None = None,
        model: str | None = None,
        **kwargs: object,
    ) -> BaseChatModel:
        provider = provider or settings.llm_provider
        model = model or settings.llm_model

        match provider:
            case LLMProvider.OPENAI:
                api_key = settings.openai_api_key
                if not api_key:
                    raise AppError("OpenAI API key is not configured", code="LLM_CONFIG_ERROR")
                return ChatOpenAI(model=model, api_key=api_key, **kwargs)  # type: ignore[arg-type]

            case LLMProvider.ANTHROPIC:
                api_key = settings.anthropic_api_key
                if not api_key:
                    raise AppError("Anthropic API key is not configured", code="LLM_CONFIG_ERROR")
                return ChatAnthropic(model=model, api_key=api_key, **kwargs)  # type: ignore[arg-type]

            case _:
                raise AppError(f"Unknown LLM provider: '{provider}'", code="LLM_CONFIG_ERROR")
