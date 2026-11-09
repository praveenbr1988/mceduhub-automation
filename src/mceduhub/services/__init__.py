"""Services: business workflows built on top of page objects."""

from mceduhub.services.book_processor import BookProcessor
from mceduhub.services.ebook_capture import EbookCaptureService
from mceduhub.services.resource_download import ResourceDownloadService

__all__ = ["BookProcessor", "EbookCaptureService", "ResourceDownloadService"]
