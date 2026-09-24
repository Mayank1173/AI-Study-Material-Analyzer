"""RAG document-processing, knowledge-base, and answer layers.

Phase 1 turns an uploaded file into normalized, metadata-rich, ready-to-embed
chunks (:func:`process_document`). Phase 2 embeds those chunks and persists
them in a local, searchable vector store (:class:`KnowledgeBase`).
Phase 3 adds an LLM-backed answer engine that grounds responses in retrieved
study material.

This package is intentionally independent of FastAPI, PostgreSQL, vector
databases, and LLM providers.

    process_document(path, source=..)   -> ProcessedDocument
    get_knowledge_base()                -> KnowledgeBase (searchable index)
    kb.index_material(path, source_ref, uploaded_by) -> int
    kb.search(query, user_id=.., ...)   -> list[SearchResult]
    answer_question(kb, llm, ...)       -> AnswerResult
"""

from rag.answer import AnswerResult, AnswerSource, answer_question
from rag.chunking import ChunkRange, TextChunker
from rag.config import RagSettings, get_rag_settings
from rag.context_builder import (
    NO_CONTEXT_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_context_block,
    build_grounded_prompt,
    build_visual_context_block,
)
from rag.conversation import (
    Conversation,
    ConversationStore,
    ConversationTurn,
    Resolution,
    make_conversation_id,
    resolve_query,
)
from rag.embeddings import (
    DeterministicEmbedder,
    Embedder,
    SentenceTransformersEmbedder,
    get_embedder,
)
from rag.errors import (
    CorruptDocumentError,
    DuplicateChunkError,
    EmbeddingError,
    EmbeddingModelUnavailableError,
    EmptyDocumentError,
    EmptyQueryError,
    ExtractionError,
    IndexingError,
    InvalidVectorError,
    MissingFileError,
    RagError,
    UnsupportedFileTypeError,
    VectorStoreCorruptedError,
    VectorStoreUnavailableError,
)
from rag.extraction import extract_document
from rag.extractors import SUPPORTED_EXTRACTABLE_TYPES, get_extractor
from rag.knowledge_base import KnowledgeBase, get_knowledge_base
from rag.intent import QueryIntent, analyze_query
from rag.llm import LLMProvider, LLMResponse, MockProvider, OllamaProvider
from rag.models import (
    ChunkMetadata,
    ExtractedDocument,
    ExtractedSection,
    IndexedChunk,
    ProcessedDocument,
    SearchResult,
    SourceRef,
    TextChunk,
    VisualElement,
)
from rag.normalize import is_empty, normalize_text
from rag.pipeline import process_document
from rag.vectorstore import (
    SearchFilter,
    SqliteVectorStore,
    VectorStore,
)

__all__ = [
    "AnswerResult",
    "AnswerSource",
    "ChunkMetadata",
    "ChunkRange",
    "Conversation",
    "ConversationStore",
    "ConversationTurn",
    "CorruptDocumentError",
    "DeterministicEmbedder",
    "DuplicateChunkError",
    "Embedder",
    "EmbeddingError",
    "EmbeddingModelUnavailableError",
    "EmptyDocumentError",
    "EmptyQueryError",
    "ExtractionError",
    "ExtractedDocument",
    "ExtractedSection",
    "IndexedChunk",
    "IndexingError",
    "InvalidVectorError",
    "KnowledgeBase",
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "MissingFileError",
    "NO_CONTEXT_SYSTEM_PROMPT",
    "OllamaProvider",
    "ProcessedDocument",
    "QueryIntent",
    "RagError",
    "RagSettings",
    "Resolution",
    "SUPPORTED_EXTRACTABLE_TYPES",
    "SYSTEM_PROMPT",
    "SearchFilter",
    "SearchResult",
    "SentenceTransformersEmbedder",
    "SourceRef",
    "SqliteVectorStore",
    "TextChunk",
    "TextChunker",
    "UnsupportedFileTypeError",
    "VectorStore",
    "VectorStoreCorruptedError",
    "VectorStoreUnavailableError",
    "VisualElement",
    "answer_question",
    "analyze_query",
    "build_context_block",
    "build_grounded_prompt",
    "build_visual_context_block",
    "extract_document",
    "get_embedder",
    "get_extractor",
    "get_knowledge_base",
    "get_rag_settings",
    "is_empty",
    "make_conversation_id",
    "normalize_text",
    "process_document",
    "resolve_query",
]