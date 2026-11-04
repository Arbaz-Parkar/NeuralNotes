"""Document parser interfaces and implementations."""

from neuralnotes.parsers.models import ParsedDocument, ParsedPage
from neuralnotes.parsers.pdf import PypdfDocumentParser
from neuralnotes.parsers.protocols import DocumentParser
from neuralnotes.parsers.text import PlainTextDocumentParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "PlainTextDocumentParser",
    "PypdfDocumentParser",
]
