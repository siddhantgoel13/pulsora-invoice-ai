import io
from dataclasses import dataclass

import fitz
from PIL import Image


@dataclass
class ExtractedPDF:
    text: str
    page_texts: list[str]


def extract_text_and_pages(pdf_bytes: bytes) -> ExtractedPDF:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts = [page.get_text("text") for page in doc]
    return ExtractedPDF(text="\n\n--- PAGE BREAK ---\n\n".join(page_texts), page_texts=page_texts)


def render_first_page(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))
