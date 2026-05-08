from araya.ingestor.models import ResearchObject, SourceType, MultimodalElement

__all__ = [
    "ResearchObject",
    "SourceType",
    "MultimodalElement",
    "PDFIngestor",
    "AudioIngestor",
    "WebIngestor",
    "ImageIngestor",
    "MultimodalIngestor",
]


def __getattr__(name):
    if name == "PDFIngestor":
        from araya.ingestor.pdf import PDFIngestor
        return PDFIngestor
    if name == "AudioIngestor":
        from araya.ingestor.audio import AudioIngestor
        return AudioIngestor
    if name == "WebIngestor":
        from araya.ingestor.web import WebIngestor
        return WebIngestor
    if name == "ImageIngestor":
        from araya.ingestor.image import ImageIngestor
        return ImageIngestor
    if name == "MultimodalIngestor":
        from araya.ingestor.factory import MultimodalIngestor
        return MultimodalIngestor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
