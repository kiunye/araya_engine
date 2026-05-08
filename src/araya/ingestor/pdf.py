import uuid
import re
import logging
from pathlib import Path
from typing import Optional

from araya.ingestor.models import ResearchObject, SourceType, MultimodalElement

logger = logging.getLogger(__name__)


class PDFIngestor:
    def __init__(self):
        self._docling_available = False
        try:
            from docling.document_converter import DocumentConverter
            self._docling_available = True
            self._converter_cls = DocumentConverter
        except ImportError:
            logger.info("Docling not installed. PDF ingestion will use PyMuPDF fallback.")

    def ingest(self, file_path: str, metadata: Optional[dict] = None) -> ResearchObject:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self._docling_available:
            return self._ingest_docling(file_path, path, metadata)
        return self._ingest_fallback(file_path, path, metadata)

    def _ingest_docling(self, file_path: str, path: Path, metadata: Optional[dict]) -> ResearchObject:
        converter = self._converter_cls()
        result = converter.convert(file_path)

        content_md = result.document.export_to_markdown()

        elements = []
        for i, table in enumerate(result.document.tables):
            table_md = table.export_to_markdown()
            elements.append(MultimodalElement(
                type="table",
                content=table_md,
                metadata={"table_index": i}
            ))

        obj_metadata = {
            "filename": path.name,
            "page_count": len(result.document.pages) if hasattr(result.document, 'pages') else None,
        }
        if metadata:
            obj_metadata.update(metadata)

        return ResearchObject(
            id=str(uuid.uuid4()),
            source_type=SourceType.PDF,
            content=content_md,
            metadata=obj_metadata,
            elements=elements
        )

    def _ingest_fallback(self, file_path: str, path: Path, metadata: Optional[dict]) -> ResearchObject:
        try:
            import fitz
            doc = fitz.open(file_path)
            pages = []
            for page in doc:
                pages.append(page.get_text())
            content = "\n\n".join(pages)
            page_count = len(doc)
            doc.close()
        except ImportError:
            logger.warning("Neither docling nor PyMuPDF installed. Reading raw text.")
            with open(file_path, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
            page_count = None

        obj_metadata = {"filename": path.name, "page_count": page_count}
        if metadata:
            obj_metadata.update(metadata)

        return ResearchObject(
            id=str(uuid.uuid4()),
            source_type=SourceType.PDF,
            content=content,
            metadata=obj_metadata,
            elements=[]
        )
