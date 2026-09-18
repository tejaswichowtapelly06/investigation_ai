"""
Document ingestion pipeline.
Parses, normalizes, chunks, embeds, and stores documents in Qdrant and PostgreSQL.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.db.models import Base, Document, DocumentType
from app.ingestion.chunking import chunk_documents_batch, DocumentChunk
from app.ingestion.embeddings import EmbeddingGenerator
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentIngester:
    """Main document ingestion pipeline."""
    
    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.qdrant_client: Optional[QdrantClient] = None
        self.postgres_engine = None
        self._initialized = False
    
    def initialize(self):
        """Initialize databases and embedding model."""
        if self._initialized:
            return True
        
        try:
            # Initialize PostgreSQL
            self.postgres_engine = create_engine(settings.postgres_url)
            Base.metadata.create_all(self.postgres_engine)
            logger.info("PostgreSQL initialized")
            
            # Initialize Qdrant
            self.qdrant_client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.QDRANT_API_KEY,
                timeout=settings.QDRANT_TIMEOUT
            )
            
            # Create Qdrant collection if it doesn't exist
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if settings.QDRANT_COLLECTION_NAME not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=settings.effective_embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION_NAME}")
            
            # Initialize embedding generator
            self.embedding_generator.initialize()
            
            self._initialized = True
            logger.info("Document ingester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize document ingester: {e}")
            return False
    
    def ingest_document(
        self,
        document_id: str,
        document_type: str,
        title: str,
        content: str,
        service: str = "",
        date: str = "",
        version: str = "",
        source: str = "",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Ingest a single document.
        
        Args:
            document_id: Unique document identifier
            document_type: Type of document
            title: Document title
            content: Document content
            service: Service name
            date: Document date
            version: Document version
            source: Source file path
            metadata: Additional metadata
        
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            # Store document metadata in PostgreSQL
            with Session(self.postgres_engine) as session:
                # Check if document already exists
                existing = session.query(Document).filter_by(document_id=document_id).first()
                if existing:
                    logger.warning(f"Document {document_id} already exists, skipping")
                    return False
                
                # Create document record
                doc = Document(
                    document_id=document_id,
                    document_type=DocumentType(document_type.lower()),
                    title=title,
                    service=service,
                    date=self._parse_date(date),
                    version=version,
                    content=content,
                    source=source,
                    metadata=metadata or {}
                )
                session.add(doc)
                session.commit()
                
                logger.info(f"Stored document {document_id} in PostgreSQL")
            
            # Chunk the document
            chunks = chunk_document(
                content=content,
                document_id=document_id,
                document_type=document_type,
                service=service,
                date=date,
                version=version,
                metadata=metadata
            )
            
            # Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_generator.generate_embeddings_batch(chunk_texts)
            
            # Store chunks in Qdrant
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                if embedding is None:
                    logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_id}")
                    continue
                
                points.append(PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload=chunk.to_payload()
                ))
            
            if points:
                self.qdrant_client.upsert(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    points=points
                )
                logger.info(f"Stored {len(points)} chunks in Qdrant for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting document {document_id}: {e}")
            return False
    
    def ingest_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """
        Ingest multiple documents in batch.
        
        Args:
            documents: List of document dictionaries
        
        Returns:
            Number of successfully ingested documents
        """
        success_count = 0
        
        for doc in documents:
            try:
                if self.ingest_document(
                    document_id=doc.get("document_id", str(uuid.uuid4())),
                    document_type=doc.get("document_type", "unknown"),
                    title=doc.get("title", ""),
                    content=doc.get("content", ""),
                    service=doc.get("service", ""),
                    date=doc.get("date", ""),
                    version=doc.get("version", ""),
                    source=doc.get("source", ""),
                    metadata=doc.get("metadata", {})
                ):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error ingesting document {doc.get('document_id', 'unknown')}: {e}")
        
        logger.info(f"Successfully ingested {success_count}/{len(documents)} documents")
        return success_count
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date {date_str}: {e}")
            return None


def main():
    """Main entry point for ingestion command."""
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Check for data file argument
    if len(sys.argv) < 2:
        print("Usage: python -m app.ingestion.ingest <data_file.json>")
        sys.exit(1)
    
    data_file = sys.argv[1]
    
    # Load documents from JSON file
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = data if isinstance(data, list) else [data]
        logger.info(f"Loaded {len(documents)} documents from {data_file}")
        
    except Exception as e:
        logger.error(f"Failed to load data file: {e}")
        sys.exit(1)
    
    # Ingest documents
    ingester = DocumentIngester()
    success_count = ingester.ingest_documents_batch(documents)
    
    logger.info(f"Ingestion complete: {success_count}/{len(documents)} documents successful")
    
    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
