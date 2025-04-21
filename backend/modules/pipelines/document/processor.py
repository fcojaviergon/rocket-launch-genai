"""
Document processing pipeline
"""
from typing import Dict, Any, List
import uuid
import logging
import numpy as np
from sqlalchemy.orm import Session
from database.models.document import Document
from modules.pipelines.base import BasePipeline
from datetime import datetime
from utils.serialization import serialize_for_json
from core.llm_interface import LLMClientInterface
from docx import Document as DocxDocument
import pypdf
from io import BytesIO

logger = logging.getLogger(__name__)

class DocumentPipeline(BasePipeline):
    """Pipeline for document processing and embedding generation"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.default_model = "gpt-4o"
        self.sync_client = True
        self.default_embedding_model = "text-embedding-3-small"
    
    async def process(self, pipeline_id: uuid.UUID, document: Document) -> Dict[str, Any]:
        """
        Process a document and generate embeddings associated with a pipeline
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Initialize context
        context = {
            "pipeline_id": pipeline_id,
            "document_id": document.id,
            "document_title": document.title,
            "processing_results": {},
            "embeddings": []
        }
        
        # Extract text content
        text_content_task = self.extract_text_from_file(document)
        text_content = await text_content_task
        context["text_content"] = text_content
        
        # Process text content
        await self._process_text_content(context)
        
        # Generate embeddings
        await self._generate_embeddings(context)
        
        # Clean up and return results
        return self._cleanup_and_return(context)
    
    def process_sync(self, pipeline_id: uuid.UUID, document: Document) -> Dict[str, Any]:
        """
        Synchronous version of process for use in Celery tasks
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            
        Returns:
            Dict[str, Any]: Processing results
        """
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.process(pipeline_id, document))
        finally:
            loop.close()
    
    async def extract_text_from_file(
        self, document: Document
    ) -> List[Dict[str, Any]]:
        """Extracts text from file and returns a list of dictionaries containing text and page numbers"""
        logger.info(f"Extracting text from file: {document.file_path}")

        # Read file content as bytes
        with open(document.file_path, 'rb') as file:
            file_content = file.read()

        if document.file_path.lower().endswith(".docx"):
            return await self._process_docx(file_content)
        elif document.file_path.lower().endswith(".pdf"):
            return await self._process_pdf(file_content)
        else:
            raise ValueError(f"Unsupported file type: {document.file_path}")

    async def _process_docx(self, file_content: bytes) -> List[Dict[str, Any]]:
        doc = DocxDocument(BytesIO(file_content))
        texts = []
        paragraphs_per_page = 4

        for i, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip():
                texts.append(
                    {"text": paragraph.text, "page": (i // paragraphs_per_page) + 1}
                )
        return texts

    async def _process_pdf(self, content: bytes) -> List[Dict[str, Any]]:
        pdf_reader = pypdf.PdfReader(BytesIO(content))
        texts = []
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                texts.append({"text": text, "page": page_num})
        return texts
    
    async def _extract_text_content(self, document: Document) -> str:
        """
        Extract text content from document by reading the file
        
        Args:
            document: Document
            
        Returns:
            str: Text content
        """
      
    
    async def _process_text_content(self, context: Dict[str, Any]) -> None:
        """
        Process text content
        
        Args:
            context: Processing context
        """
        # This would use NLP to process text content
        # For now, we'll use a placeholder implementation
        text_content = context.get("text_content", "")
        
        # Example processing results
        processing_results = {
            "word_count": "",
            "character_count": "",
            "language": "en",
            "summary": "This is a summary of the document content.",
            "key_phrases": ["key phrase 1", "key phrase 2", "key phrase 3"],
            "entities": {
                "people": ["Person 1", "Person 2"],
                "organizations": ["Organization 1", "Organization 2"],
                "locations": ["Location 1", "Location 2"]
            }
        }
        
        context["processing_results"] = processing_results
    
    async def _generate_embeddings(self, context: Dict[str, Any]) -> None:
        """
        Generate embeddings for document chunks
        
        Args:
            context: Processing context
        """
        # Get document content
        text_content = context.get("text_content", "")
        pipeline_id = context.get("pipeline_id")
        document_id = context.get("document_id")
        
        # Skip if no content
        if not text_content:
            logger.warning(f"No text content for document {document_id} in pipeline {pipeline_id}")
            return
        
        # Convert text_content to string if it's a list of dictionaries
        if isinstance(text_content, list):
            combined_text = ""
            for item in text_content:
                if isinstance(item, dict) and "text" in item:
                    combined_text += item["text"] + "\n\n"
            text_content = combined_text
        
        # Split text into chunks
        chunks = self._split_text_into_chunks(text_content)
        
        # Generate embeddings for chunks
        embeddings = []
        for chunk in chunks:
            try:
                # Generate embedding
                embedding_vector = self.llm_client.generate_embeddings_sync(
                    texts=[chunk],
                    model=self.default_embedding_model
                )
                
                logger.info(f"Generated embedding for chunk: {chunk}")
                # Add to embeddings list
                embeddings.append({
                    "chunk_text": chunk,
                    "embedding_vector": embedding_vector
                })
            except Exception as e:
                logger.error(f"Error generating embedding for chunk in pipeline {pipeline_id}: {e}")
                # En caso de error, añadir un vector aleatorio
              
        
        # Add embeddings to context
        context["embeddings"] = embeddings
        context["embedding_model"] = self.default_embedding_model
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into chunks
        
        Args:
            text: Text to split
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        # Simple chunking by character count
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    # Usamos la función de serialización del módulo de utilidades
    
    def save_processing_results(self, db: Session, pipeline_id: uuid.UUID, document_id: uuid.UUID, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save processing results to analysis pipeline
        
        Args:
            db: Database session
            pipeline_id: Analysis Pipeline ID
            document_id: Document ID
            results: Processing results
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Import here to avoid circular imports
        from database.models.analysis import AnalysisPipeline
        
        # Get document and pipeline
        document = db.query(Document).filter(Document.id == document_id).first()
        pipeline = db.query(AnalysisPipeline).filter(AnalysisPipeline.id == pipeline_id).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
            
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        # Serializar los resultados para asegurar que sean JSON-serializables
        serialized_results = serialize_for_json(results)
        
        # Update document processing status
        document.processing_status = "COMPLETED"
        document.process_metadata = {
            "processed_at": datetime.utcnow().isoformat(),
            "processor": "DocumentPipeline"
        }
        
        # Update pipeline results
        processing_results = serialized_results.get("processing_results", {})
        if pipeline.results is None:
            pipeline.results = {}
            
        pipeline.results.update({
            "document_processing": {
                "processed_at": datetime.utcnow().isoformat(),
                "text_extracted": True,
                "embeddings_generated": len(serialized_results.get("embeddings", [])) > 0,
                **processing_results
            }
        })
        
        # Save changes
        db.commit()
        db.refresh(document)
        db.refresh(pipeline)
        
        return results
    
    def _cleanup_and_return(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up context and return results
        
        Args:
            context: Processing context
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Return only the necessary data
        return {
            "pipeline_id": context.get("pipeline_id"),
            "document_id": context.get("document_id"),
            "text_content": context.get("text_content", ""),
            "processing_results": context.get("processing_results", {}),
            "embeddings": context.get("embeddings", []),
            "processed_at": datetime.utcnow().isoformat(),
            "model": context.get("model", "default")
        }
        
    def save_embeddings(
        self, 
        db: Session, 
        pipeline_id: uuid.UUID, 
        embeddings: List[Dict[str, Any]], 
        embedding_model: str = "default"
    ) -> List:
        """
        Save embeddings to database associated with a pipeline
        
        Args:
            db: Database session
            pipeline_id: Analysis Pipeline ID
            embeddings: List of embeddings with chunk text
            model: Embedding model name
            
        Returns:
            List: Created embedding objects
        """
        # Import here to avoid circular imports
        from database.models.analysis import PipelineEmbedding
        
        # Delete existing embeddings for this pipeline
        db.query(PipelineEmbedding).filter(
            PipelineEmbedding.pipeline_id == pipeline_id
        ).delete()
        
        # Serializar los embeddings para asegurar que sean JSON-serializables
        serialized_embeddings = serialize_for_json(embeddings)
        
        # Create embedding objects
        db_embeddings = []
        for idx, embedding_data in enumerate(serialized_embeddings):
            embedding_vector = embedding_data["embedding_vector"]
            chunk_text = embedding_data["chunk_text"]
            
            # Asegurarse de que el vector de embedding sea una lista de Python, no un array de NumPy
            if isinstance(embedding_vector, np.ndarray):
                embedding_vector = embedding_vector.tolist()
            
            # Create embedding object
            db_embedding = PipelineEmbedding(
                pipeline_id=pipeline_id,
                embedding_vector=embedding_vector,  # Almacenar como JSON
                chunk_text=chunk_text,
                chunk_index=idx,
                metadata_info={
                    "embedding_model": embedding_model,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(db_embedding)
            db_embeddings.append(db_embedding)
        
        # Commit changes
        try:
            db.commit()
            
            # Refresh objects
            for db_embedding in db_embeddings:
                db.refresh(db_embedding)
                
            return db_embeddings
        except Exception as e:
            logger.error(f"Error saving embeddings: {str(e)}")
            db.rollback()
            raise
