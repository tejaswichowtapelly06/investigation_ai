"""
Mock database implementation with in-memory dataset.
This simulates a real database and can be replaced with Qdrant/PostgreSQL later.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.tools.interfaces import SearchTool, DocumentResult, SearchResult, SearchFilters
import logging

logger = logging.getLogger(__name__)


class MockSearchDatabase(SearchTool):
    """Mock implementation of search tools using in-memory dataset."""
    
    def __init__(self):
        """Initialize mock database with sample documents."""
        self.documents = self._initialize_mock_documents()
        logger.info(f"Mock database initialized with {len(self.documents)} documents")
    
    def _initialize_mock_documents(self) -> List[DocumentResult]:
        """Create mock documents for testing."""
        documents = [
            # Incident Reports
            DocumentResult(
                document_id="INC-2024-001",
                document_type="incident_report",
                title="Payment Service Outage - January 2024",
                service="payment-api",
                date="2024-01-15",
                version="v2.1.0",
                content="Payment service experienced downtime due to database connection pool exhaustion. Root cause was improper connection handling in the retry logic. Resolution involved implementing proper connection pooling and adding circuit breakers.",
                relevance_score=0.9,
                incident_id="INC-2024-001",
                severity="high",
                metadata={"root_cause": "database connection pool exhaustion", "resolution": "connection pooling implementation"}
            ),
            DocumentResult(
                document_id="INC-2024-002",
                document_type="incident_report",
                title="Payment Service Latency - February 2024",
                service="payment-api",
                date="2024-02-20",
                version="v2.1.5",
                content="Payment service experienced high latency due to slow database queries. Root cause was missing database indexes on frequently queried columns. Resolution involved adding appropriate indexes and optimizing query performance.",
                relevance_score=0.85,
                incident_id="INC-2024-002",
                severity="medium",
                metadata={"root_cause": "missing database indexes", "resolution": "index optimization"}
            ),
            DocumentResult(
                document_id="INC-2024-003",
                document_type="incident_report",
                title="User Service Authentication Failure - March 2024",
                service="user-service",
                date="2024-03-15",
                version="v1.5.0",
                content="User service experienced authentication failures due to expired JWT signing keys. Root cause was automated key rotation not updating the service configuration. Resolution involved manual key update and improving rotation process.",
                relevance_score=0.88,
                incident_id="INC-2024-003",
                severity="high",
                metadata={"root_cause": "expired JWT keys", "resolution": "key rotation fix"}
            ),
            DocumentResult(
                document_id="INC-2024-004",
                document_type="incident_report",
                title="Payment Service Outage - May 2024",
                service="payment-api",
                date="2024-05-18",
                version="v2.3.0",
                content="Payment service experienced intermittent outages due to third-party payment gateway API changes. Root cause was lack of API version pinning. Resolution involved pinning to specific API version and adding integration tests.",
                relevance_score=0.82,
                incident_id="INC-2024-004",
                severity="medium",
                metadata={"root_cause": "third-party API changes", "resolution": "API version pinning"}
            ),
            DocumentResult(
                document_id="INC-1042",
                document_type="incident_report",
                title="Order API Latency - September 2024",
                service="orders-api",
                date="2024-09-16",
                version="v2.8.1",
                content="Order API experienced increased latency starting September 16. Initial investigation showed database query performance degradation. Root cause was missing indexes on order_history table after recent schema changes.",
                relevance_score=0.95,
                incident_id="INC-1042",
                severity="high",
                metadata={"root_cause": "missing indexes after schema change", "resolution": "index addition"}
            ),
            
            # Postmortems
            DocumentResult(
                document_id="PM-2024-001",
                document_type="postmortem",
                title="Postmortem: Payment Service Database Exhaustion",
                service="payment-api",
                date="2024-01-20",
                version="v2.1.0",
                content="This postmortem analyzes the January 15 payment service outage. Key findings: connection pool was not properly configured, retry logic was exponential without backoff, monitoring was insufficient. Action items: implement connection pooling, add circuit breakers, improve monitoring.",
                relevance_score=0.92,
                incident_id="INC-2024-001",
                severity="high",
                metadata={"analysis_date": "2024-01-20", "action_items": 3}
            ),
            DocumentResult(
                document_id="PM-1042",
                document_type="postmortem",
                title="Postmortem: Order API Latency Incident",
                service="orders-api",
                date="2024-09-20",
                version="v2.8.1",
                content="Postmortem for September 16 Order API latency incident. Investigation revealed that schema changes on September 15 removed critical indexes. Deployment DEP-882 included these schema changes. No performance testing was conducted before deployment.",
                relevance_score=0.94,
                incident_id="INC-1042",
                severity="high",
                metadata={"analysis_date": "2024-09-20", "related_deployment": "DEP-882"}
            ),
            
            # Deployment Notes
            DocumentResult(
                document_id="DEP-882",
                document_type="deployment_note",
                title="Orders API v2.8.1 Deployment",
                service="orders-api",
                date="2024-09-15",
                version="v2.8.1",
                content="Deployed orders API v2.8.1 with schema changes to order_history table. Removed legacy indexes to improve write performance. Changes: removed index on customer_id, added index on order_date. No performance testing conducted due to time constraints.",
                relevance_score=0.87,
                metadata={"deployment_type": "schema_change", "testing_performed": False}
            ),
            DocumentResult(
                document_id="DEP-501",
                document_type="deployment_note",
                title="Payment API v2.3.0 Deployment",
                service="payment-api",
                date="2024-04-10",
                version="v2.3.0",
                content="Deployed payment API v2.3.0 with improved error handling and retry logic. Added comprehensive logging and monitoring. Fixed connection pool configuration issues identified in previous incidents.",
                relevance_score=0.83,
                metadata={"deployment_type": "feature_release", "testing_performed": True}
            ),
            DocumentResult(
                document_id="DEP-450",
                document_type="deployment_note",
                title="Payment API v2.1.5 Deployment",
                service="payment-api",
                date="2024-02-18",
                version="v2.1.5",
                content="Deployed payment API v2.1.5 with query optimization improvements. Added database indexes for frequently queried columns. Performance improvements expected for customer lookup operations.",
                relevance_score=0.80,
                metadata={"deployment_type": "performance_optimization", "testing_performed": True}
            ),
            
            # Troubleshooting Guides
            DocumentResult(
                document_id="TG-001",
                document_type="troubleshooting_guide",
                title="Payment Service Troubleshooting Guide",
                service="payment-api",
                date="2024-03-01",
                version="v2.2.0",
                content="This guide covers common payment service issues: 1) Connection timeouts - check database connectivity, 2) High latency - review query performance and indexes, 3) Authentication failures - verify API keys, 4) Rate limiting - check quota usage.",
                relevance_score=0.75,
                metadata={"guide_type": "service_specific", "last_updated": "2024-03-01"}
            ),
            DocumentResult(
                document_id="TG-002",
                document_type="troubleshooting_guide",
                title="Order API Performance Troubleshooting",
                service="orders-api",
                date="2024-08-15",
                version="v2.8.0",
                content="Order API performance troubleshooting: 1) High latency - check database query performance, 2) Slow order creation - review index usage, 3) Timeout issues - verify database connection pool settings, 4) Memory issues - check for memory leaks in order processing.",
                relevance_score=0.78,
                metadata={"guide_type": "performance", "last_updated": "2024-08-15"}
            ),
            
            # Architecture Documents
            DocumentResult(
                document_id="ARCH-001",
                document_type="architecture",
                title="Payment Service Architecture",
                service="payment-api",
                date="2024-01-10",
                version="v2.0.0",
                content="Payment service architecture overview: microservice architecture with PostgreSQL database, Redis caching, and external payment gateway integration. Key components: payment processing service, transaction service, notification service. Database schema includes payments, transactions, and refunds tables.",
                relevance_score=0.70,
                metadata={"document_type": "architecture_overview", "components": 3}
            ),
            DocumentResult(
                document_id="ARCH-002",
                document_type="architecture",
                title="Orders Service Architecture",
                service="orders-api",
                date="2024-08-01",
                version="v2.8.0",
                content="Orders service architecture: microservice handling order creation, management, and retrieval. Uses PostgreSQL with order_history, orders, and order_items tables. Key dependencies: inventory service, payment service, user service. Performance critical path: order creation involves inventory check and payment processing.",
                relevance_score=0.72,
                metadata={"document_type": "architecture_overview", "dependencies": 3}
            )
        ]
        
        return documents
    
    def semantic_search(self, query: str, filters: Optional[SearchFilters] = None) -> SearchResult:
        """Perform semantic search on document content."""
        logger.info(f"SEMANTIC_SEARCH - Query: '{query}', Filters: {filters}")
        
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            # Apply filters if provided
            if filters and not self._matches_filters(doc, filters):
                continue
            
            # Simple keyword matching for semantic search
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()
            
            # Calculate relevance score based on keyword matches
            relevance = 0.0
            query_words = [word for word in query_lower.split() if len(word) > 3]
            
            for word in query_words:
                if word in content_lower:
                    relevance += 0.3
                if word in title_lower:
                    relevance += 0.2
            
            # Check for service match
            if filters and filters.service:
                if filters.service.lower() in doc.service.lower():
                    relevance += 0.4
            
            # Normalize relevance score
            relevance = min(relevance, 1.0)
            
            if relevance > 0.3:  # Threshold for including results
                result = doc.model_copy(update={"relevance_score": relevance})
                results.append(result)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"SEMANTIC_SEARCH - Found {len(results)} documents")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"query": query, "filters": filters.model_dump() if filters else None}
        )
    
    def metadata_search(self, filters: SearchFilters) -> SearchResult:
        """Search by metadata fields."""
        logger.info(f"METADATA_SEARCH - Filters: {filters}")
        
        results = []
        
        for doc in self.documents:
            if self._matches_filters(doc, filters):
                relevance = 0.8  # Default relevance for metadata matches
                result = doc.model_copy(update={"relevance_score": relevance})
                results.append(result)
        
        logger.info(f"METADATA_SEARCH - Found {len(results)} documents")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"filters": filters.model_dump()}
        )
    
    def get_document(self, document_id: str) -> Optional[DocumentResult]:
        """Retrieve a specific document by ID."""
        logger.info(f"GET_DOCUMENT - Document ID: '{document_id}'")
        
        for doc in self.documents:
            if doc.document_id == document_id:
                logger.info(f"GET_DOCUMENT - Found document: {document_id}")
                return doc
        
        logger.info(f"GET_DOCUMENT - Document not found: {document_id}")
        return None
    
    def search_related_documents(self, document_id: str) -> SearchResult:
        """Find documents related to a given document."""
        logger.info(f"SEARCH_RELATED - Source document ID: '{document_id}'")
        
        source_doc = self.get_document(document_id)
        if not source_doc:
            logger.warning(f"SEARCH_RELATED - Source document not found: {document_id}")
            return SearchResult(documents=[], total_found=0)
        
        results = []
        
        # Find related documents based on service, version, or incident
        for doc in self.documents:
            if doc.document_id == document_id:
                continue
            
            related = False
            relevance = 0.0
            
            # Same service
            if source_doc.service and doc.service == source_doc.service:
                related = True
                relevance += 0.4
            
            # Same version
            if source_doc.version and doc.version == source_doc.version:
                related = True
                relevance += 0.3
            
            # Same incident ID
            if source_doc.incident_id and doc.incident_id == source_doc.incident_id:
                related = True
                relevance += 0.5
            
            # Same date range (within 7 days)
            if source_doc.date and doc.date:
                try:
                    date1 = datetime.strptime(source_doc.date, "%Y-%m-%d")
                    date2 = datetime.strptime(doc.date, "%Y-%m-%d")
                    if abs((date1 - date2).days) <= 7:
                        related = True
                        relevance += 0.2
                except:
                    pass
            
            if related:
                result = doc.model_copy(update={"relevance_score": min(relevance, 1.0)})
                results.append(result)
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"SEARCH_RELATED - Found {len(results)} related documents")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"source_document": document_id}
        )
    
    def search_historical_incidents(self, service: str, symptom: str) -> SearchResult:
        """Search for historical incidents with similar symptoms."""
        logger.info(f"HISTORICAL_SEARCH - Service: '{service}', Symptom: '{symptom}'")
        
        service_lower = service.lower()
        symptom_lower = symptom.lower()
        
        results = []
        
        for doc in self.documents:
            # Only look at incident reports and postmortems
            if doc.document_type not in ["incident_report", "postmortem"]:
                continue
            
            # Check service match
            service_match = service_lower in doc.service.lower() if service else True
            
            # Check symptom match in content
            symptom_match = symptom_lower in doc.content.lower() if symptom else True
            
            if service_match and symptom_match:
                # Calculate relevance based on symptom specificity
                relevance = 0.7
                if symptom and len(symptom) > 5:
                    relevance += 0.2
                
                result = doc.model_copy(update={"relevance_score": min(relevance, 1.0)})
                results.append(result)
        
        # Sort by date (most recent first for historical comparison)
        results.sort(key=lambda x: x.date, reverse=True)
        
        logger.info(f"HISTORICAL_SEARCH - Found {len(results)} historical incidents")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"service": service, "symptom": symptom}
        )
    
    def search_by_version(self, version: str) -> SearchResult:
        """Search for documents related to a specific version."""
        logger.info(f"VERSION_SEARCH - Version: '{version}'")
        
        results = []
        
        for doc in self.documents:
            if doc.version and version.lower() in doc.version.lower():
                relevance = 0.85
                result = doc.model_copy(update={"relevance_score": relevance})
                results.append(result)
        
        logger.info(f"VERSION_SEARCH - Found {len(results)} documents for version {version}")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"version": version}
        )
    
    def search_by_service(self, service: str) -> SearchResult:
        """Search for documents related to a specific service."""
        logger.info(f"SERVICE_SEARCH - Service: '{service}'")
        
        service_lower = service.lower()
        results = []
        
        for doc in self.documents:
            if service_lower in doc.service.lower():
                relevance = 0.9
                result = doc.model_copy(update={"relevance_score": relevance})
                results.append(result)
        
        logger.info(f"SERVICE_SEARCH - Found {len(results)} documents for service {service}")
        
        return SearchResult(
            documents=results,
            total_found=len(results),
            search_metadata={"service": service}
        )
    
    def _matches_filters(self, doc: DocumentResult, filters: SearchFilters) -> bool:
        """Check if document matches the given filters."""
        if filters.service and filters.service.lower() not in doc.service.lower():
            return False
        
        if filters.version and filters.version.lower() not in doc.version.lower():
            return False
        
        if filters.document_type and filters.document_type != doc.document_type:
            return False
        
        if filters.incident_id and filters.incident_id != doc.incident_id:
            return False
        
        if filters.date_range:
            try:
                start_date = datetime.strptime(filters.date_range[0], "%Y-%m-%d")
                end_date = datetime.strptime(filters.date_range[1], "%Y-%m-%d")
                doc_date = datetime.strptime(doc.date, "%Y-%m-%d") if doc.date else None
                
                if doc_date and (doc_date < start_date or doc_date > end_date):
                    return False
            except:
                pass
        
        return True