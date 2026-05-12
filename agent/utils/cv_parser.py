"""services/cv_parser.py — Extract plain text from a PDF CV."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def parse_cv(path: str | Path) -> str:
    """
    Extract text from a PDF file.
    Tries pdfplumber first (better layout), falls back to pypdf.
    """
    path = Path(path)
    if not path.exists():
        log.warning("CV file not found: %s", path)
        return ""

    # Strategy 1: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if text:
            log.info("CV parsed with pdfplumber (%d chars)", len(text))
            return text
    except ImportError:
        log.debug("pdfplumber not installed, trying pypdf")
    except Exception as exc:
        log.warning("pdfplumber failed: %s", exc)

    # Strategy 2: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        log.info("CV parsed with pypdf (%d chars)", len(text))
        return text
    except ImportError:
        log.error("Neither pdfplumber nor pypdf is installed. Run: pip install pdfplumber")
    except Exception as exc:
        log.error("pypdf failed: %s", exc)

    return ""
