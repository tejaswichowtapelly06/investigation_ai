"""
Document chunking with metadata retention.
"""
import logging
from typing import List, Dict, Any
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentChunk:
    """A chunk of a document with retained metadata."""
    
    def __init__(
        self,
        chunk_id: str,
        content: str,
        document_id: str,
        document_type: str,
        service: str,
        date: str,
        version: str,
        chunk_index: int,
        metadata: Dict[str, Any] = None
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.document_id = document_id
        self.document_type = document_type
        self.service = service
        self.date = date
        self.version = version
        self.chunk_index = chunk_index
        self.metadata = metadata or {}
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "service": self.service,
            "date": self.date,
            "version": self.version,
            "chunk_index": self.chunk_index,
            **self.metadata
        }


def chunk_document(
    content: str,
    document_id: str,
    document_type: str,
    service: str = "",
    date: str = "",
    version: str = "",
    metadata: Dict[str, Any] = None
) -> List[DocumentChunk]:
    """
    Chunk a document into smaller pieces while retaining metadata.
    
    Args:
        content: Full document content
        document_id: Original document ID
        document_type: Type of document
        service: Service name
        date: Document date
        version: Document version
        metadata: Additional metadata
    
    Returns:
        List of DocumentChunk objects
    """
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    
    chunks = []
    
    # Split content into paragraphs first to avoid breaking sentences
    paragraphs = content.split('\n\n')
    
    current_chunk = ""
    chunk_index = 0
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # If adding this paragraph would exceed chunk size, save current chunk
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunk_id = f"{document_id}_chunk_{chunk_index}"
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                content=current_chunk.strip(),
                document_id=document_id,
                document_type=document_type,
                service=service,
                date=date,
                version=version,
                chunk_index=chunk_index,
                metadata=metadata or {}
            ))
            chunk_index += 1
            
            # Start new chunk with overlap
            current_chunk = current_chunk[-chunk_overlap:] if chunk_overlap > 0 else ""
        
        current_chunk += paragraph + "\n\n"
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunk_id = f"{document_id}_chunk_{chunk_index}"
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            content=current_chunk.strip(),
            document_id=document_id,
            document_type=document_type,
            service=service,
            date=date,
            version=version,
            chunk_index=chunk_index,
            metadata=metadata or {}
        ))
    
    logger.info(f"Chunked document {document_id} into {len(chunks)} chunks")
    
    return chunks


def chunk_documents_batch(documents: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """
    Chunk multiple documents in batch.
    
    Args:
        documents: List of document dictionaries with keys: document_id, content, document_type, service, date, version, metadata
    
    Returns:
        List of all DocumentChunk objects
    """
    all_chunks = []
    
    for doc in documents:
        try:
            chunks = chunk_document(
                content=doc.get("content", ""),
                document_id=doc.get("document_id", ""),
                document_type=doc.get("document_type", "unknown"),
                service=doc.get("service", ""),
                date=doc.get("date", ""),
                version=doc.get("version", ""),
                metadata=doc.get("metadata", {})
            )
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Error chunking document {doc.get('document_id', 'unknown')}: {e}")
    
    logger.info(f"Chunked {len(documents)} documents into {len(all_chunks)} total chunks")
    
    return all_chunks
