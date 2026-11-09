"""Exception hierarchy. Every error raised on purpose by the framework derives from AutomationError."""


class AutomationError(Exception):
    """Base class for all framework errors."""


class ConfigurationError(AutomationError):
    """Invalid or missing settings / credentials."""


class LoginError(AutomationError):
    """Login did not succeed."""


class BookNotFoundError(AutomationError):
    """No library title matches the requested book."""


class AmbiguousBookError(AutomationError):
    """The requested name matches more than one library title."""


class ReaderNotReadyError(AutomationError):
    """The e-book reader did not finish loading."""
