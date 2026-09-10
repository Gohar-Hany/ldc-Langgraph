import os
from pathlib import Path
from typing import List
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

from app.core.logging import logger
from app.schemas.rag_schema import KnowledgeChunk, ChunkMetadata
from app.services.openrouter_embedding import embedding_service
from app.services.qdrant_cloud_service import qdrant_service


class DoclingIngestionService:
    """Service to parse knowledge base documents using Docling and ingest into Qdrant."""

    def __init__(self, kb_dir: str = "data/knowledge_base"):
        self.kb_dir = Path(kb_dir)
        self.converter = DocumentConverter()
        self.chunker = HybridChunker()

    def _infer_category(self, filename: str) -> str:
        name = filename.lower()
        if "vpn" in name or "wifi" in name or "network" in name:
            return "network"
        elif "password" in name or "mfa" in name or "security" in name:
            return "security"
        elif "hardware" in name or "equipment" in name or "laptop" in name:
            return "hardware"
        elif "software" in name or "license" in name:
            return "software"
        return "general"

    def parse_file(self, file_path: Path) -> List[KnowledgeChunk]:
        """Convert a single document using Docling into structured KnowledgeChunks."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"[DoclingIngestion] Converting '{file_path.name}' with Docling...")
        res = self.converter.convert(str(file_path))
        doc = res.document
        
        doc_chunks = list(self.chunker.chunk(doc))
        category = self._infer_category(file_path.name)
        chunks: List[KnowledgeChunk] = []

        for idx, chunk in enumerate(doc_chunks):
            # Extract section headings hierarchy
            headings = getattr(chunk.meta, "headings", []) if hasattr(chunk, "meta") else []
            section_title = " > ".join(headings) if headings else "Overview"
            
            chunk_id = f"{file_path.stem}_chunk_{idx}"
            metadata = ChunkMetadata(
                document_name=file_path.name,
                section_title=section_title,
                category=category,
                chunk_index=idx
            )
            chunks.append(KnowledgeChunk(
                id=chunk_id,
                content=chunk.text.strip(),
                metadata=metadata
            ))

        logger.info(f"[DoclingIngestion] Extracted {len(chunks)} chunks from '{file_path.name}'.")
        return chunks

    def parse_directory(self) -> List[KnowledgeChunk]:
        """Parse all supported documents in the knowledge base directory."""
        if not self.kb_dir.exists():
            logger.warning(f"[DoclingIngestion] Directory '{self.kb_dir}' does not exist.")
            return []

        all_chunks: List[KnowledgeChunk] = []
        supported_exts = [".md", ".txt", ".docx", ".pdf"]

        for file_path in sorted(self.kb_dir.iterdir()):
            if file_path.suffix.lower() in supported_exts and not file_path.name.startswith("."):
                try:
                    chunks = self.parse_file(file_path)
                    all_chunks.extend(chunks)
                except Exception as exc:
                    logger.error(f"[DoclingIngestion: Error] Failed to parse '{file_path.name}': {exc}")

        logger.info(f"[DoclingIngestion] Total parsed chunks across knowledge base: {len(all_chunks)}.")
        return all_chunks

    def ingest_to_qdrant(self, force: bool = False) -> int:
        """Parse all docs, generate embeddings, and upsert into Qdrant Cloud."""
        qdrant_service.ensure_collection()
        existing_count = qdrant_service.count_points()

        if existing_count > 0 and not force:
            logger.info(f"[DoclingIngestion] Collection already contains {existing_count} points. Skipping re-ingestion.")
            return existing_count

        chunks = self.parse_directory()
        if not chunks:
            logger.warning("[DoclingIngestion] No chunks found to ingest.")
            return 0

        # Batch embed in groups of 20
        batch_size = 20
        total_upserted = 0
        logger.info(f"[DoclingIngestion] Generating embeddings and upserting {len(chunks)} chunks in batches of {batch_size}...")

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            texts = [c.content for c in batch_chunks]
            embeddings = embedding_service.embed_texts(texts)
            qdrant_service.upsert_chunks(batch_chunks, embeddings)
            total_upserted += len(batch_chunks)

        logger.info(f"[DoclingIngestion] Finished ingestion. Total points in Qdrant: {total_upserted}.")
        return total_upserted


ingestion_service = DoclingIngestionService()
