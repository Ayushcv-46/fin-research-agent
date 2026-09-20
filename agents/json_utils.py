import json
import re
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def extract_json_str(text: str) -> str:
    """
    Extracts a JSON substring from text by stripping markdown code fences
    or finding the outermost matching curly braces.
    """
    cleaned = text.strip()

    # Strip markdown code blocks (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    # Match the outermost JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return match.group(0)

    return cleaned


def parse_and_validate_json(raw_text: str, schema_cls: Type[T]) -> T:
    """
    Extracts and parses a JSON string, then validates it against a Pydantic schema.
    Raises ValueError with context if parsing or validation fails.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError(
            f"Empty LLM response received while expecting JSON for {schema_cls.__name__}"
        )

    json_str = extract_json_str(raw_text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as err:
        raise ValueError(
            f"Failed to decode JSON for {schema_cls.__name__}: {err}. Raw content: {raw_text[:200]!r}"
        ) from err

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object (dict) for {schema_cls.__name__}, got {type(data).__name__}: {data!r}"
        )

    try:
        return schema_cls.model_validate(data)
    except ValidationError as err:
        raise ValueError(
            f"Schema validation failed for {schema_cls.__name__}: {err}. Data: {data!r}"
        ) from err


def invoke_json(llm, prompt: str, schema_cls: Type[T], max_retries: int = 1) -> T:
    """
    Invokes an LLM with a prompt and parses/validates the response into a Pydantic schema.
    Retries only on ValueError (invalid JSON or schema mismatch).
    API/network/timeout errors are not caught and propagate immediately.
    """
    current_prompt = prompt
    last_value_error = None

    for attempt in range(max_retries + 1):
        response = llm.invoke(current_prompt)
        text = response.content if hasattr(response, "content") else str(response)
        try:
            return parse_and_validate_json(text, schema_cls)
        except ValueError as err:
            last_value_error = err
            if attempt < max_retries:
                current_prompt = (
                    prompt
                    + "\n\nCRITICAL: Your previous response was invalid JSON or did not match the schema. "
                    "Return ONLY valid JSON matching the schema exactly, with no surrounding commentary or markdown."
                )

    raise RuntimeError(
        f"Failed to obtain valid JSON for {schema_cls.__name__} after {max_retries} retry: {last_value_error}"
    ) from last_value_error
