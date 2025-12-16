import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_template(template_name: str, context: dict) -> str:
    tpl = env.get_template(template_name)
    return tpl.render(**context)


def generate_structured_metadata(info: dict, category: str | None = None, platform: str = "generic", style: str | None = None) -> dict:
    """Generate a structured metadata dict using a local template + lightweight heuristics.

    This function is CPU-friendly and deterministic for demo purposes.
    """
    ctx = {
        "width": info.get("width"),
        "height": info.get("height"),
        "format": info.get("format", "unknown"),
        "mode": info.get("mode", "RGB"),
        "category": category or "Product",
        "platform": platform,
        "style": style or "stylish",
    }

    title = f"{ctx['style'].capitalize()} {ctx['category']} — {ctx['format']}"
    description = render_template("metadata_prompt.j2", ctx)

    bullets = [
        f"{ctx['style'].capitalize()} design perfect for everyday use.",
        f"Made from quality {ctx['format'].lower()} materials for lasting performance.",
        f"Dimensions: {ctx['width']}x{ctx['height']} px · Color mode: {ctx['mode']}",
    ]

    tags = [ctx['category'].lower(), ctx['style'], ctx['format'].lower()]
    attributes = {"width": ctx['width'], "height": ctx['height'], "format": ctx['format'], "color_mode": ctx['mode']}

    return {"title": title, "bullets": bullets, "description": description, "tags": tags, "attributes": attributes}
