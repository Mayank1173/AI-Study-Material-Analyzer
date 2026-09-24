"""Controlled, user-facing errors raised by the RAG processing layer.

Every error carries a human-readable message that never contains absolute
filesystem paths, secrets, or internal storage details. Low-level library
exceptions are translated here so callers only ever see this stable set.
"""


class RagError(Exception):
    """Base class for all controlled RAG pipeline errors."""


class UnsupportedFileTypeError(RagError):
    """The document's file type has no registered extractor."""


class MissingFileError(RagError):
    """The source document could not be located on disk."""


class CorruptDocumentError(RagError):
    """The document exists but could not be parsed (corrupt or encrypted)."""


class EmptyDocumentError(RagError):
    """The document parsed successfully but contains no usable text."""


class ExtractionError(RagError):
    """A document could not be extracted for an unexpected reason."""


class EmbeddingError(RagError):
    """Text could not be converted into an embedding vector."""


class EmbeddingModelUnavailableError(EmbeddingError):
    """The configured embedding model/sentence-transformer backend is missing."""


class EmptyQueryError(RagError):
    """A semantic search was requested with an empty/blank query."""


class InvalidVectorError(RagError):
    """An embedding vector has the wrong shape, type, or non-finite values."""


class VectorStoreUnavailableError(RagError):
    """The vector store could not be opened or accessed."""


class VectorStoreCorruptedError(RagError):
    """The vector store file/schema exists but holds corrupt or incompatible data."""


class DuplicateChunkError(RagError):
    """A chunk with the given identifier is already present in the store."""


class IndexingError(RagError):
    """A document could not be embedded and indexed for an unexpected reason."""