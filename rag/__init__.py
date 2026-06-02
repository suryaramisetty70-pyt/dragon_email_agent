# =============================================================================
# RAG SYSTEM - Retrieval Augmented Generation with ChromaDB
# =============================================================================

import os
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

from core import Config, DragonModule, logger, events
from database import Email, Contact, Thread, get_db_manager

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not available. RAG features will be limited.")

# Sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("Sentence Transformers not available. Using TF-IDF fallback.")


class EmbeddingManager:
    """Manage text embeddings"""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self) -> None:
        """Initialize embedding model"""
        if not ST_AVAILABLE:
            logger.warning("Sentence Transformers not available")
            return
            
        try:
            self.model = SentenceTransformer(
                self.config.embedding_model,
                device=self.config.embedding_device
            )
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded: {self.config.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if self.model:
            try:
                return self.model.encode(text).tolist()
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                return None
        return None
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.model and texts:
            try:
                return self.model.encode(texts).tolist()
            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                return []
        return []
        
    def compute_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """Compute cosine similarity between two texts"""
        emb1 = self.embed_text(text1)
        emb2 = self.embed_text(text2)
        
        if emb1 and emb2:
            import numpy as np
            v1 = np.array(emb1)
            v2 = np.array(emb2)
            return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        return 0.0


class VectorStore:
    """Vector storage using ChromaDB"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.collections: Dict[str, Any] = {}
        self._initialize_store()
        
    def _initialize_store(self) -> None:
        """Initialize ChromaDB client"""
        if not CHROMA_AVAILABLE:
            return
            
        try:
            db_path = os.path.join(config.data_dir, "chroma_db")
            os.makedirs(db_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Create default collections
            self._ensure_collection("emails")
            self._ensure_collection("contacts")
            self._ensure_collection("conversations")
            
            logger.info("ChromaDB initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            
    def _ensure_collection(self, name: str) -> Optional[Any]:
        """Ensure collection exists"""
        if name not in self.collections:
            try:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata={"description": f"{name} vector store"}
                )
            except Exception as e:
                logger.error(f"Failed to create collection {name}: {e}")
                return None
        return self.collections.get(name)
        
    def get_collection(self, name: str) -> Optional[Any]:
        """Get collection by name"""
        if name not in self.collections:
            try:
                self.collections[name] = self.client.get_collection(name)
            except:
                return self._ensure_collection(name)
        return self.collections.get(name)
        
    def add(
        self, 
        collection_name: str, 
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Add documents to collection"""
        collection = self.get_collection(collection_name)
        if not collection:
            return False
            
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
            
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        query_texts: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search documents"""
        collection = self.get_collection(collection_name)
        if not collection:
            return []
            
        try:
            if query_texts:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where
                )
            else:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where
                )
                
            # Format results
            formatted = []
            if results and "documents" in results:
                for i in range(len(results["documents"][0])):
                    formatted.append({
                        "id": results["ids"][0][i] if "ids" in results else "",
                        "document": results["documents"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else 0,
                        "metadata": results["metadatas"][0][i] if "metadatas" in results else {},
                    })
                    
            return formatted
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
            
    def update(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Update documents"""
        collection = self.get_collection(collection_name)
        if not collection:
            return False
            
        try:
            collection.update(
                ids=ids,
                embeddings=embeddings,
                documents=documents	if documents else None,
                metadatas=metadatas if metadatas else None
            )
            return True
        except Exception as e:
            logger.error(f"Update error: {e}")
            return False
            
    def delete(
        self,
        collection_name: str,
        ids: List[str]
    ) -> bool:
        """Delete documents"""
        collection = self.get_collection(collection_name)
        if not collection:
            return False
            
        try:
            collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False
            
    def count(self, collection_name: str) -> int:
        """Get document count"""
        collection = self.get_collection(collection_name)
        if collection:
            return collection.count()
        return 0


class DocumentProcessor:
    """Process emails into searchable documents"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def process_email(self, email: Email) -> Dict[str, Any]:
        """Process email into document"""
        # Create search-friendly text
        parts = [
            f"Subject: {email.subject}",
            f"From: {email.sender_name or email.sender_email}",
            f"Date: {email.date_sent.strftime('%Y-%m-%d %H:%M')}",
        ]
        
        # Add body
        if email.body_plain:
            body = email.body_plain[:5000]  # Limit for embedding
            parts.append(f"Content: {body}")
            
        # Add summary if available
        if email.summary:
            parts.append(f"Summary: {email.summary}")
            
        # Add keywords
        if email.keywords:
            parts.append(f"Keywords: {', '.join(email.keywords)}")
            
        document = " ".join(parts)
        
        metadata = {
            "email_id": email.id,
            "message_id": email.message_id,
            "thread_id": email.thread_id,
            "subject": email.subject,
            "sender": email.sender_email,
            "sender_name": email.sender_name,
            "date_sent": email.date_sent.isoformat() if email.date_sent else None,
            "category": email.category.value if email.category else None,
            "priority": email.priority.value if email.priority else None,
            "importance_score": email.importance_score,
            "is_read": email.is_read,
        }
        
        return {
            "document": document,
            "metadata": metadata
        }
        
    def process_contact(self, contact: Contact) -> Dict[str, Any]:
        """Process contact into document"""
        parts = [
            f"Name: {contact.display_name or contact.name or contact.email}",
            f"Email: {contact.email}",
        ]
        
        if contact.organization:
            parts.append(f"Organization: {contact.organization}")
        if contact.job_title:
            parts.append(f"Job Title: {contact.job_title}")
        if contact.meta_data:
            # Add recent notes
            notes = contact.meta_data.get("notes", [])
            if notes:
                parts.append(f"Notes: {' '.join([n.get('content', '') for n in notes[-5:]])}")
                
        document = " ".join(parts)
        
        metadata = {
            "contact_id": contact.id,
            "email": contact.email,
            "name": contact.display_name or contact.name,
            "organization": contact.organization,
            "is_vip": contact.is_vip,
            "category": contact.category,
        }
        
        return {
            "document": document,
            "metadata": metadata
        }
        
    def process_thread(self, thread: Thread) -> Dict[str, Any]:
        """Process thread into document"""
        parts = [
            f"Thread: {thread.subject}",
            f"Messages: {thread.message_count}",
        ]
        
        if thread.participant_emails:
            parts.append(f"Participants: {', '.join(thread.participant_emails)}")
            
        document = " ".join(parts)
        
        metadata = {
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "message_count": thread.message_count,
            "last_message_date": thread.last_message_date.isoformat() if thread.last_message_date else None,
            "category": thread.category.value if thread.category else None,
        }
        
        return {
            "document": document,
            "metadata": metadata
        }


class SemanticSearch:
    """Semantic search capabilities"""
    
    def __init__(self, config: Config, vector_store: VectorStore, embedding_manager: EmbeddingManager):
        self.config = config
        self.vector_store = vector_store
        self.embeddings = embedding_manager
        
    def search_emails(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Search emails semantically"""
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        if not query_embedding:
            return []
            
        # Build metadata filter
        where_filter = {}
        if category:
            where_filter["category"] = category
        if priority:
            where_filter["priority"] = priority
            
        # Search vector store
        results = self.vector_store.search(
            collection_name="emails",
            query_embedding=query_embedding,
            n_results=limit + 10,  # Get extra for filtering
            where=where_filter if where_filter else None
        )
        
        # Post-filter by date
        if date_from or date_to:
            filtered = []
            for result in results:
                date_str = result.get("metadata", {}).get("date_sent")
                if date_str:
                    date = datetime.fromisoformat(date_str)
                    if date_from and date < date_from:
                        continue
                    if date_to and date > date_to:
                        continue
                filtered.append(result)
            results = filtered
            
        return results[:limit]
        
    def find_similar_emails(
        self,
        email_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find emails similar to given email"""
        # Get email text
        with self.config.db.get_session() as session:
            email = session.query(Email).filter(Email.id == email_id).first()
            if not email:
                return []
                
            text = f"{email.subject} {email.snippet}"
            
        query_embedding = self.embeddings.embed_text(text)
        if not query_embedding:
            return []
            
        return self.vector_store.search(
            collection_name="emails",
            query_embedding=query_embedding,
            n_results=limit + 1,
            where={"email_id": {"$ne": email_id}}
        )[1:]  # Exclude the query email


class RAGSystem(DragonModule):
    """RAG System for email intelligence"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.embeddings = EmbeddingManager(config)
        self.vector_store = VectorStore(config)
        self.document_processor = DocumentProcessor(config)
        self.semantic_search = SemanticSearch(config, self.vector_store, self.embeddings)
        
        self._indexed_count = 0
        self._last_full_index = None
        
    def initialize(self) -> None:
        """Initialize RAG system"""
        super().initialize()
        logger.info("RAG System initialized")
        
    def index_email(self, email: Email) -> bool:
        """Index a single email"""
        doc_data = self.document_processor.process_email(email)
        embedding = self.embeddings.embed_text(doc_data["document"])
        
        if not embedding:
            return False
            
        return self.vector_store.add(
            collection_name="emails",
            ids=[f"email_{email.id}"],
            embeddings=[embedding],
            documents=[doc_data["document"]],
            metadatas=[doc_data["metadata"]]
        )
        
    def index_contact(self, contact: Contact) -> bool:
        """Index a contact"""
        doc_data = self.document_processor.process_contact(contact)
        embedding = self.embeddings.embed_text(doc_data["document"])
        
        if not embedding:
            return False
            
        return self.vector_store.add(
            collection_name="contacts",
            ids=[f"contact_{contact.id}"],
            embeddings=[embedding],
            documents=[doc_data["document"]],
            metadatas=[doc_data["metadata"]]
        )
        
    def index_all(self, batch_size: int = 100) -> Dict[str, int]:
        """Full index of all data"""
        stats = {"emails": 0, "contacts": 0, "errors": 0}
        
        # Index emails in batches
        with self.db.get_session() as session:
            emails = session.query(Email).filter(
                Email.embedding_id.is_(None)
            ).limit(10000).all()
            
            for i in range(0, len(emails), batch_size):
                batch = emails[i:i+batch_size]
                
                for email in batch:
                    try:
                        if self.index_email(email):
                            stats["emails"] += 1
                            email.embedding_id = f"email_{email.id}"
                            self._indexed_count += 1
                    except Exception as e:
                        logger.error(f"Index error for email {email.id}: {e}")
                        stats["errors"] += 1
                        
            # Index contacts
            contacts = session.query(Contact).all()
            for contact in contacts:
                try:
                    if self.index_contact(contact):
                        stats["contacts"] += 1
                except Exception as e:
                    logger.error(f"Index error for contact {contact.id}: {e}")
                    stats["errors"] += 1
                    
        self._last_full_index = datetime.utcnow()
        logger.info(f"Indexing complete: {stats}")
        return stats
        
    def search(
        self,
        query: str,
        scope: str = "all",
        limit: int = 10,
        **filters
    ) -> List[Dict[str, Any]]:
        """Search across all indexed data"""
        results = []
        
        if scope in ["all", "emails"]:
            email_results = self.semantic_search.search_emails(query, limit, **filters)
            for r in email_results:
                r["type"] = "email"
            results.extend(email_results)
            
        if scope in ["all", "contacts"]:
            query_embedding = self.embeddings.embed_text(query)
            if query_embedding:
                contact_results = self.vector_store.search(
                    collection_name="contacts",
                    query_embedding=query_embedding,
                    n_results=limit
                )
                for r in contact_results:
                    r["type"] = "contact"
                results.extend(contact_results)
                
        # Sort by relevance (distance)
        results.sort(key=lambda x: x.get("distance", float("inf")))
        
        return results[:limit]
        
    def get_context_for_query(
        self,
        query: str,
        max_contexts: int = 5
    ) -> str:
        """Get context strings for query to use with LLM"""
        results = self.search(query, limit=max_contexts)
        
        contexts = []
        for result in results:
            doc = result.get("document", "")
            source = result.get("type", "unknown")
            contexts.append(f"[{source.upper()}] {doc}")
            
        return "\n\n".join(contexts)
        
    def reindex_email(self, email_id: int) -> bool:
        """Reindex an email (update)"""
        with self.db.get_session() as session:
            email = session.query(Email).filter(Email.id == email_id).first()
            if not email:
                return False
                
            doc_data = self.document_processor.process_email(email)
            embedding = self.embeddings.embed_text(doc_data["document"])
            
            if not embedding:
                return False
                
            return self.vector_store.update(
                collection_name="emails",
                ids=[f"email_{email.id}"],
                embeddings=[embedding],
                documents=[doc_data["document"]],
                metadatas=[doc_data["metadata"]]
            )
            
    def delete_from_index(self, collection: str, item_id: int) -> bool:
        """Remove item from index"""
        return self.vector_store.delete(
            collection_name=collection,
            ids=[f"{collection}_{item_id}"]
        )
        
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "emails_indexed": self.vector_store.count("emails"),
            "contacts_indexed": self.vector_store.count("contacts"),
            "total_vectors": self.vector_store.count("emails") + self.vector_store.count("contacts"),
            "last_full_index": self._last_full_index.isoformat() if self._last_full_index else None,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": getattr(self.embeddings, 'dimension', 'unknown' if self.embeddings.model else 'model not loaded'),
        }
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        logger.info("RAG System shutdown complete")
