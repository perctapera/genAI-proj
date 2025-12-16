import json
import logging

logger = logging.getLogger(__name__)

try:
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except Exception:
    validate = None
    ValidationError = Exception
    JSONSCHEMA_AVAILABLE = False


METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "bullets": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "attributes": {"type": "object"},
    },
    "required": ["title", "bullets", "description"],
    "additionalProperties": True,
}


def is_valid_metadata(obj: dict) -> (bool, str | None):
    if JSONSCHEMA_AVAILABLE:
        try:
            validate(instance=obj, schema=METADATA_SCHEMA)
            return True, None
        except ValidationError as e:
            return False, str(e)
    # Basic fallback validation (ensure required keys exist)
    required = METADATA_SCHEMA.get('required', [])
    for k in required:
        if k not in obj:
            return False, f"missing required property: {k}"
    if not isinstance(obj.get('title', ''), str):
        return False, 'title must be a string'
    if not isinstance(obj.get('bullets', []), list):
        return False, 'bullets must be a list'
    return True, None


async def repair_with_openai(openai_module, invalid_text: str) -> str | None:
    """Ask OpenAI to repair the invalid JSON to conform to METADATA_SCHEMA.

    `openai_module` should be the imported openai package (older api) so we can call ChatCompletion.
    Returns repaired JSON string or None on failure.
    """
    if openai_module is None:
        return None
    try:
        prompt = (
            "The user provided the following (possibly invalid) JSON for an ecommerce product listing metadata:\n"
            f"{invalid_text}\n\n"
            "Please return a single valid JSON object that conforms to this schema:\n"
            f"{json.dumps(METADATA_SCHEMA, indent=2)}\n"
            "Return ONLY the JSON object, no explanation."
        )
        res = openai_module.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant that fixes JSON to match the requested schema."}, {"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=400,
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.exception("repair_with_openai failed: %s", e)
        return None