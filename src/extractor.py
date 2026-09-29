import io
from dataclasses import dataclass

import fitz
from PIL import Image


@dataclass
class ExtractedPDF:
    text: str
    page_texts: list[str]
    page_images: list[bytes]


def _normalise_image(image_bytes: bytes) -> bytes:
    """Convert an uploaded raster image into JPEG bytes for the vision model."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        # Preserve the visible invoice while normalising formats such as PNG.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        else:
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()


def _is_image_type(file_type: str | None) -> bool:
    if not file_type:
        return False
    value = file_type.lower().strip()
    return value in {
        "image/jpeg", "image/jpg", "image/png",
        ".jpg", ".jpeg", ".png", "jpg", "jpeg", "png",
    }


def extract_text_and_pages(document_bytes: bytes, file_type: str | None = None) -> ExtractedPDF:
    """
    Extract selectable text and rendered page images from an invoice.

    PDF input keeps the existing PyMuPDF text + page-rendering pipeline.
    JPG/JPEG/PNG input is normalised to one JPEG page image and sent to the
    same multimodal parser. Image inputs have no selectable text, so ``text``
    is intentionally empty and the vision model becomes the primary source.

    ``file_type`` is optional for backwards compatibility, so existing calls
    such as ``extract_text_and_pages(raw)`` continue to work.
    """
    if _is_image_type(file_type):
        image_bytes = _normalise_image(document_bytes)
        return ExtractedPDF(
            text="",
            page_texts=[""],
            page_images=[image_bytes],
        )

    # Default to PDF for backwards compatibility and the existing pipeline.
    doc = fitz.open(stream=document_bytes, filetype="pdf")
    try:
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
    finally:
        doc.close()


def render_first_page(document_bytes: bytes, file_type: str | None = None):
    """Render the first page/image for the Review section."""
    if _is_image_type(file_type):
        return Image.open(io.BytesIO(_normalise_image(document_bytes)))

    doc = fitz.open(stream=document_bytes, filetype="pdf")
    try:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png")))
    finally:
        doc.close()
