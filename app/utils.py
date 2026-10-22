from slugify import slugify as _slugify


def slugify(text: str) -> str:
    return _slugify(text, max_length=200)