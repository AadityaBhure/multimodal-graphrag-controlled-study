"""Text-only PDF ingestion; no OCR."""
import re
from pathlib import Path

import pymupdf


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        with pymupdf.open(pdf_path) as doc:
            text = normalize_text("\n\n".join(page.get_text("text") for page in doc))
        if not text:
            raise RuntimeError("No extractable text")
        return text
    except Exception as exc:
        raise RuntimeError(f"PDF parsing failed for {pdf_path.name}: {exc}") from exc
