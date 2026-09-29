import io
from dataclasses import dataclass

import fitz
from PIL import Image, ImageOps


@dataclass
class ExtractedPDF:
    text: str
    page_texts: list[str]
    page_images: list[bytes]


def _image_to_jpeg(image_bytes: bytes) -> bytes:
    """Normalize a JPG/PNG invoice image into JPEG bytes for the multimodal model."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        elif image.mode == "L":
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()


def extract_text_and_pages(file_bytes: bytes, file_type: str = "pdf") -> ExtractedPDF:
    """
    Extract invoice text and page images from a PDF or image document.

    PDFs retain both selectable text and rendered page images. JPG/JPEG/PNG
    documents have no text extraction step, so the normalized image is passed
    directly to the visual extraction model.
    """
    file_type = (file_type or "pdf").lower().lstrip(".")

    if file_type in {"jpg", "jpeg", "png"}:
        jpeg_bytes = _image_to_jpeg(file_bytes)
        return ExtractedPDF(
            text="",
            page_texts=[""],
            page_images=[jpeg_bytes],
        )

    if file_type != "pdf":
        raise ValueError(f"Unsupported invoice document type: {file_type}")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
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


def render_first_page(file_bytes: bytes, file_type: str = "pdf"):
    """Return the first invoice page/image for the UI preview."""
    file_type = (file_type or "pdf").lower().lstrip(".")

    if file_type in {"jpg", "jpeg", "png"}:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            return image.convert("RGB")

    if file_type != "pdf":
        raise ValueError(f"Unsupported invoice document type: {file_type}")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if not doc.page_count:
            raise ValueError("The PDF contains no pages.")
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png"))).copy()
    finally:
        doc.close()
