import io
from dataclasses import dataclass

import fitz
from PIL import Image


@dataclass
class ExtractedPDF:
    text: str
    page_texts: list[str]
    page_images: list[bytes]


def extract_text_and_pages(pdf_bytes: bytes) -> ExtractedPDF:
    """
    Extract selectable PDF text and render every page.

    Both representations are returned because utility invoices frequently
    contain tables where plain text extraction loses the relationship between
    a label and its value.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    page_texts = [page.get_text("text") for page in doc]
    text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts).strip()

    page_images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        page_images.append(pix.tobytes("jpeg"))

    return ExtractedPDF(
        text=text,
        page_texts=page_texts,
        page_images=page_images,
    )


def render_first_page(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))
