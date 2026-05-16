"""Stage 1: raw input -> structured text + metadata."""


async def extract(text: str | None, image_bytes: bytes | None) -> dict:
    raise NotImplementedError
