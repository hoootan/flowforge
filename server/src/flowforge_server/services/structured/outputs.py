"""Structured output generation using Pydantic models.

Provides type-safe JSON output generation with validation
using the instructor library with LiteLLM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Type, TypeVar

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from flowforge_server.services.ai import AIService

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Error during structured output generation."""

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        partial_response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.validation_errors = validation_errors or []
        self.partial_response = partial_response


class StructuredOutputService:
    """
    Service for generating type-safe structured outputs using Pydantic.

    Integrates with LiteLLM via the instructor library for reliable
    structured output generation with automatic retries on validation failures.
    """

    def __init__(self, ai_service: AIService | None = None) -> None:
        """
        Initialize the structured output service.

        Args:
            ai_service: Optional AI service for non-instructor fallback
        """
        self.ai_service = ai_service
        self._instructor_client: Any = None

    def _get_instructor_client(self) -> Any:
        """Get or create instructor-patched LiteLLM client."""
        if self._instructor_client is None:
            try:
                import instructor
                import litellm

                self._instructor_client = instructor.from_litellm(litellm.acompletion)
            except ImportError as e:
                raise ImportError(
                    "instructor package required for structured outputs. "
                    "Install with: pip install instructor"
                ) from e
        return self._instructor_client

    async def generate(
        self,
        model: str,
        response_model: Type[T],
        messages: list[dict[str, str]],
        max_retries: int = 3,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> T:
        """
        Generate a structured output conforming to a Pydantic model.

        Args:
            model: LLM model to use
            response_model: Pydantic model class defining the output schema
            messages: Chat messages
            max_retries: Retries on validation failure
            temperature: Sampling temperature

        Returns:
            Instance of response_model with validated data

        Raises:
            StructuredOutputError: If generation fails after all retries
        """
        client = self._get_instructor_client()

        try:
            result = await client.chat.completions.create(
                model=model,
                response_model=response_model,
                messages=messages,
                max_retries=max_retries,
                temperature=temperature,
                **kwargs,
            )
            return result
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise StructuredOutputError(
                f"Failed to generate valid {response_model.__name__}",
                validation_errors=errors,
            ) from e
        except Exception as e:
            raise StructuredOutputError(
                f"Structured output generation failed: {str(e)}"
            ) from e

    async def generate_stream(
        self,
        model: str,
        response_model: Type[T],
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """
        Stream partial structured outputs as they're generated.

        Yields progressively more complete instances of response_model.
        Useful for showing incremental progress in UIs.

        Args:
            model: LLM model to use
            response_model: Pydantic model class defining the output schema
            messages: Chat messages
            temperature: Sampling temperature

        Yields:
            Partial instances of response_model
        """
        client = self._get_instructor_client()

        try:
            async for partial in await client.chat.completions.create_partial(
                model=model,
                response_model=response_model,
                messages=messages,
                temperature=temperature,
                stream=True,
                **kwargs,
            ):
                yield partial
        except Exception as e:
            raise StructuredOutputError(
                f"Streaming structured output failed: {str(e)}"
            ) from e

    async def generate_with_fallback(
        self,
        model: str,
        response_model: Type[T],
        messages: list[dict[str, str]],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> T:
        """
        Generate structured output with JSON mode fallback.

        First tries instructor, then falls back to JSON mode with manual parsing.

        Args:
            model: LLM model to use
            response_model: Pydantic model class
            messages: Chat messages
            max_retries: Retries on failure

        Returns:
            Instance of response_model
        """
        try:
            return await self.generate(
                model=model,
                response_model=response_model,
                messages=messages,
                max_retries=max_retries,
                **kwargs,
            )
        except Exception:
            # Fallback to JSON mode with manual parsing
            return await self._generate_with_json_mode(
                model=model,
                response_model=response_model,
                messages=messages,
                max_retries=max_retries,
                **kwargs,
            )

    async def _generate_with_json_mode(
        self,
        model: str,
        response_model: Type[T],
        messages: list[dict[str, str]],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> T:
        """Fallback generation using JSON mode and manual parsing."""
        import json

        import litellm

        # Add schema to system message
        schema = response_model.model_json_schema()
        schema_prompt = (
            f"\n\nYou must respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )

        # Modify messages to include schema
        modified_messages = list(messages)
        if modified_messages and modified_messages[0]["role"] == "system":
            modified_messages[0] = {
                "role": "system",
                "content": modified_messages[0]["content"] + schema_prompt,
            }
        else:
            modified_messages.insert(0, {"role": "system", "content": schema_prompt})

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=modified_messages,
                    response_format={"type": "json_object"},
                    **kwargs,
                )

                content = response.choices[0].message.content
                data = json.loads(content)
                return response_model.model_validate(data)

            except ValidationError as e:
                last_error = e
                # Add error feedback for retry
                errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
                modified_messages.append({
                    "role": "assistant",
                    "content": content,
                })
                modified_messages.append({
                    "role": "user",
                    "content": (
                        f"The response had validation errors:\n"
                        f"{chr(10).join(f'- {e}' for e in errors)}\n"
                        f"Please fix these errors and try again."
                    ),
                })
            except json.JSONDecodeError as e:
                last_error = e
                continue

        raise StructuredOutputError(
            f"Failed to generate valid {response_model.__name__} after {max_retries} attempts",
            validation_errors=[str(last_error)] if last_error else [],
        )


def pydantic_to_tool_schema(model: Type[BaseModel]) -> dict[str, Any]:
    """
    Convert a Pydantic model to an OpenAI tool schema.

    Useful for using Pydantic models as tool output definitions.

    Args:
        model: Pydantic model class

    Returns:
        Tool schema dict
    """
    schema = model.model_json_schema()

    return {
        "type": "function",
        "function": {
            "name": model.__name__,
            "description": model.__doc__ or f"Generate a {model.__name__}",
            "parameters": schema,
        },
    }


def validate_against_model(
    data: dict[str, Any],
    model: Type[T],
) -> tuple[T | None, list[str]]:
    """
    Validate data against a Pydantic model.

    Args:
        data: Data to validate
        model: Pydantic model class

    Returns:
        Tuple of (validated_instance or None, list of errors)
    """
    try:
        instance = model.model_validate(data)
        return instance, []
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return None, errors
