import base64
import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from langchain.tools import tool

from app.core.config import settings


logger = logging.getLogger(__name__)


def _extract_parts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = payload.get("candidates", [])
    if not candidates:
        return []
    content = candidates[0].get("content", {})
    return content.get("parts", [])


def _resolve_output_dir(output_dir: str) -> Path:
    raw_dir = (output_dir or "").strip() or settings.GENERATED_IMAGES_DIR
    return Path(raw_dir).resolve()


def _encode_reference_image(reference_image_path: str) -> Dict[str, Any]:
    image_path = Path(reference_image_path).resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Reference image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return {"inline_data": {"mime_type": mime_type, "data": data}}


@tool
def generate_image_nano_banana(
    prompt: str,
    output_dir: str = "",
    filename_prefix: str = "nano_banana",
    reference_image_path: str = "",
) -> str:
    """
    Generate an image with Nano Banana (Gemini image model) and save it locally.

    Args:
        prompt: Instruction describing the image to create.
        output_dir: Directory to write image files. Defaults to settings.GENERATED_IMAGES_DIR.
        filename_prefix: Prefix for generated file names.
        reference_image_path: Optional local image path for image-to-image editing.

    Returns:
        JSON string with generated file paths and any text returned by the model.
    """
    if not prompt or not prompt.strip():
        return "Error: prompt is required."
    if not settings.GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY not configured."

    model_name = (settings.NANO_BANANA_MODEL or "").strip() or "gemini-2.5-flash-image"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    try:
        parts: List[Dict[str, Any]] = [{"text": prompt.strip()}]
        if reference_image_path.strip():
            parts.append(_encode_reference_image(reference_image_path.strip()))

        payload: Dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }

        response = requests.post(
            endpoint,
            params={"key": settings.GOOGLE_API_KEY},
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        out_dir = _resolve_output_dir(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        output_paths: List[str] = []
        text_parts: List[str] = []
        image_count = 0
        for part in _extract_parts(data):
            if "text" in part and str(part["text"]).strip():
                text_parts.append(str(part["text"]).strip())
                continue

            inline_data = part.get("inlineData") or part.get("inline_data")
            if not inline_data:
                continue

            encoded = inline_data.get("data", "")
            if not encoded:
                continue

            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png"
            ext = ".png"
            if mime_type == "image/jpeg":
                ext = ".jpg"
            elif mime_type == "image/webp":
                ext = ".webp"

            image_count += 1
            file_name = f"{filename_prefix}_{timestamp}_{image_count}{ext}"
            out_path = out_dir / file_name
            out_path.write_bytes(base64.b64decode(encoded))
            output_paths.append(str(out_path))

        if not output_paths:
            logger.warning("Nano Banana response did not contain image data: %s", data)
            return (
                "Error: No image data returned by model. "
                "Model response may have been text-only or blocked by safety filters."
            )

        result = {
            "ok": True,
            "model": model_name,
            "images": output_paths,
            "text": "\n".join(text_parts).strip(),
        }
        return json.dumps(result, indent=2)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text if e.response is not None else str(e)
        logger.error("Nano Banana HTTP error (%s): %s", status, body)
        return f"Error generating image (HTTP {status}): {body}"
    except Exception as e:
        logger.exception("Failed to generate image via Nano Banana")
        return f"Error generating image: {str(e)}"


def get_image_tools():
    return [generate_image_nano_banana]
