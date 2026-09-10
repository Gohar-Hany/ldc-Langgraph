from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata associated with a knowledge base chunk."""
    document_name: str = Field(description="Name of the source document file")
    section_title: str = Field(default="General", description="Heading or section name")
    category: str = Field(default="general", description="IT domain category e.g. network, security")
    chunk_index: int = Field(default=0, description="Sequential chunk index within the document")


class KnowledgeChunk(BaseModel):
    """A single chunk ingested from corporate knowledge base."""
    id: str = Field(description="Unique identifier for the chunk")
    content: str = Field(description="Textual content of the chunk")
    metadata: ChunkMetadata = Field(description="Chunk metadata and lineage")


class RetrievedDocument(BaseModel):
    """A retrieved document chunk with similarity score."""
    content: str = Field(description="Chunk text content")
    document_name: str = Field(description="Source document file name")
    section_title: str = Field(default="General", description="Source section heading")
    category: str = Field(default="general", description="Category")
    score: float = Field(default=0.0, description="Relevance or similarity score")


class DocumentGrade(BaseModel):
    """Evaluation result for whether a retrieved document answers the query."""
    is_relevant: bool = Field(description="True if document contains information relevant to query")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(default="", description="Brief explanation for relevance determination")


class QueryRewrite(BaseModel):
    """Rewritten query for self-corrective RAG loop."""
    rewritten_query: str = Field(description="Optimized technical search query")
    rationale: str = Field(description="Reason why the query was reformulated")
