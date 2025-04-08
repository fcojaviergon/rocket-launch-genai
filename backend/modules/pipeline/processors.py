"""
Procesadores para pipelines de documentos
"""
import sys
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import re
from core.config import settings
import httpx 

# Import the interface
from core.llm_interface import LLMClientInterface, LLMMessage 

import numpy as np
from pathlib import Path
import aiofiles
import asyncio
import json

try:

    from pypdf import PdfReader # <-- ADD
    print(f"EMBEDDING DEBUG - Successfully imported pypdf") # <-- ADD
except ImportError as e:

    PdfReader = None # <-- ADD

    print(f"EMBEDDING DEBUG - ImportError when importing pypdf: {e}") # <-- ADD

    logging.warning("pypdf not installed. PDF extraction will not work.") # <-- ADD

try:
    import docx # python-docx
except ImportError:
    docx = None
    logging.warning("python-docx not installed. DOCX extraction will not work.")

from database.models.document import Document

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Base class for pipeline processors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        # Store the shared client if provided
        self.llm_client = llm_client
        
    @abstractmethod
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document object and return the results
        
        Args:
            document: The Document ORM object being processed.
            context: Contextual information and results of previous steps
            
        Returns:
            Dict[str, Any]: Processing results for this step
        """
        pass

class TextExtractionProcessor(BaseProcessor):
    """Extract text from various document formats based on file path"""
    
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and clean text from the document's file"""
        file_path_str = document.file_path
        extracted_text = None
        error_msg = None

        if not file_path_str or not Path(file_path_str).exists():
            logger.error(f"Document file not found or path missing for doc {document.id} at path: {file_path_str}")
            error_msg = "Document file path missing or file not found."
        else:
            file_path = Path(file_path_str)
            file_ext = file_path.suffix.lower()
            logger.info(f"TextExtractionProcessor processing document {document.id} (type: {file_ext}) from path: {file_path}")
            
            try:
                # Use async file reading and thread pool for sync libraries
                loop = asyncio.get_running_loop()
                
                if file_ext == '.txt':
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            extracted_text = await f.read()
                    except Exception as txt_err:
                         error_msg = f"Error reading TXT file: {txt_err}"
                         logger.error(error_msg, exc_info=True)

                elif file_ext == '.pdf':
                    if PdfReader:
                        try:
                            def read_pdf(): # Function to run in thread pool
                                with open(file_path, 'rb') as f:
                                    reader = PdfReader(f)
                                    return '\n'.join([page.extract_text() for page in reader.pages if page.extract_text()])
                            extracted_text = await loop.run_in_executor(None, read_pdf) # Run sync code in thread pool
                        except Exception as pdf_err:
                            error_msg = f"Error reading PDF file: {pdf_err}"
                            logger.error(error_msg, exc_info=True)
                    else:
                        error_msg = "pypdf library not available for PDF extraction."
                        logger.warning(error_msg)

                elif file_ext in ['.docx']:
                    if docx:
                        try:
                            def read_docx(): # Function to run in thread pool
                                doc = docx.Document(file_path)
                                return '\n'.join([para.text for para in doc.paragraphs if para.text])
                            extracted_text = await loop.run_in_executor(None, read_docx) # Run sync code in thread pool
                        except Exception as docx_err:
                             error_msg = f"Error reading DOCX file: {docx_err}"
                             logger.error(error_msg, exc_info=True)
                    else:
                        error_msg = "python-docx library not available for DOCX extraction."
                        logger.warning(error_msg)
                else:
                    # Fallback: Maybe content is already in document.content?
                    if document.content and isinstance(document.content, str):
                         logger.warning(f"Unsupported file type '{file_ext}' for extraction, using existing document.content")
                         extracted_text = document.content
                    else:
                        error_msg = f"Unsupported file type for text extraction: {file_ext}"
                        logger.error(error_msg)
            
            except Exception as e:
                logger.error(f"Generic error during text extraction for {document.id}: {e}", exc_info=True)
                error_msg = f"Generic extraction error: {e}"

        # Handle results
        if error_msg:
             logger.error(f"Failed text extraction for doc {document.id}: {error_msg}")
             return {
                 "error": error_msg,
                 "processor": self.name,
                 "timestamp": datetime.utcnow().isoformat()
             }
        elif extracted_text is None:
            logger.warning(f"No text could be extracted for doc {document.id} (path: {file_path_str}).")
            extracted_text = "" # Ensure it's a string
            
        # Clean the extracted text
        clean_text = self._clean_text(extracted_text)
        word_count = len(clean_text.split())
        char_count = len(clean_text)
        
        logger.info(f"Text extracted successfully for doc {document.id}: {word_count} words, {char_count} chars")
        
        return {
            # Key name changed to reflect it might be the primary content source now
            "document_content": clean_text, 
            "word_count": word_count,
            "char_count": char_count,
            "processor": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean the text by removing special characters, multiple spaces, etc."""
        # Eliminate non-printable characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        # Replace multiple spaces with one
        text = re.sub(r'\s+', ' ', text)
        # Eliminate empty lines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()

class SummarizerProcessor(BaseProcessor):
    """Generate text summaries using language models"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None):
        super().__init__(config)
        
        # Store the passed client
        self.llm_client = llm_client
        
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_chunk_tokens = self.config.get("max_chunk_tokens", 12000)  # Tamaño máximo por chunk
        logger.info(f"{self.name} will use model: {self.model}")
    
    def _chunk_text(self, text: str, max_tokens: int = 12000) -> List[str]:
        """
        Divide el texto en chunks más pequeños para evitar exceder los límites del modelo.
        
        Args:
            text: El texto a dividir
            max_tokens: Aproximación de tokens máximos por chunk (estimamos ~4 chars = 1 token)
            
        Returns:
            List[str]: Lista de chunks de texto
        """
        # Estimación simple: ~4 caracteres = 1 token para texto en inglés/español
        max_chars = max_tokens * 4
        
        # Si el texto es más corto que el máximo, devolverlo directamente
        if len(text) <= max_chars:
            return [text]
        
        # Dividir por párrafos primero
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si añadir este párrafo excedería el límite, guardar el chunk actual y empezar uno nuevo
            if len(current_chunk) + len(paragraph) > max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Añadir el último chunk si no está vacío
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Si algún párrafo individual es demasiado grande, dividirlo por oraciones
        if any(len(chunk) > max_chars for chunk in chunks):
            refined_chunks = []
            for chunk in chunks:
                if len(chunk) > max_chars:
                    # Dividir por oraciones (aproximadamente)
                    sentences = re.split(r'(?<=[.!?])\s+', chunk)
                    sub_chunk = ""
                    for sentence in sentences:
                        if len(sub_chunk) + len(sentence) > max_chars and sub_chunk:
                            refined_chunks.append(sub_chunk.strip())
                            sub_chunk = sentence
                        else:
                            if sub_chunk:
                                sub_chunk += " " + sentence
                            else:
                                sub_chunk = sentence
                    if sub_chunk:
                        refined_chunks.append(sub_chunk.strip())
                else:
                    refined_chunks.append(chunk)
            chunks = refined_chunks
        
        logger.info(f"Texto dividido en {len(chunks)} chunks para procesamiento")
        return chunks
    
    async def _summarize_chunk(self, text: str) -> str:
        """
        Resume un único chunk de texto.
        
        Args:
            text: Texto a resumir
            
        Returns:
            str: Resumen del texto
        """
        try:
            if not self.llm_client:
                raise RuntimeError(f"{self.name}: OpenAI client is not available.")

            # Use the interface method
            summary = await self.llm_client.generate_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Resumir el siguiente texto en un párrafo conciso"},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return summary
        except Exception as e:
            logger.error(f"Error al resumir chunk: {str(e)}")
            return f"Error de resumen: {str(e)}"
    
    async def _combine_summaries(self, summaries: List[str]) -> str:
        """
        Combina múltiples resúmenes en uno final coherente.
        
        Args:
            summaries: Lista de resúmenes parciales
            
        Returns:
            str: Resumen final combinado
        """
        if not self.llm_client:
            raise RuntimeError(f"{self.name}: OpenAI client is not available for combining summaries.")

        if len(summaries) == 1:
            return summaries[0]
        
        combined_text = "\n\n".join([f"Sección {i+1}: {summary}" for i, summary in enumerate(summaries)])
        
        try:
            # Use the interface method
            final_summary = await self.llm_client.generate_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Combina estos resúmenes parciales en un único resumen coherente"},
                    {"role": "user", "content": combined_text}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            return final_summary
        except Exception as e:
            logger.error(f"Error al combinar resúmenes: {str(e)}")
            return "\n\n".join(["RESUMEN FINAL (no se pudo combinar automáticamente):"] + summaries)
    
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the document content to generate a summary"""
        try:
            # Get text from context (preferred) or document.content
            document_content = context.get("document_content", document.content or "")
            if not document_content:
                 logger.warning(f"No document content found in context or document for summarization.")
                 return {"summary": "", "error": "No content to summarize"}

            logger.info(f"SummarizerProcessor processing document {document.id}, content length: {len(document_content)}")

            # Divide text into chunks
            chunks = self._chunk_text(document_content, self.max_chunk_tokens)

            if not chunks:
                 logger.warning(f"Text could not be chunked for summarization (content likely empty).")
                 return {"summary": "", "error": "Content could not be chunked"}

            # Process each chunk in parallel
            summaries = await asyncio.gather(*[self._summarize_chunk(chunk) for chunk in chunks])
            
            # Combine summaries
            final_summary = await self._combine_summaries(summaries)
            
            logger.info(f"Summary generated for document {document.id}: {len(final_summary)} chars")

            # Calculate tokens used (approximation or get from LLM response if available)
            tokens_used = context.get("total_tokens_used", 0) # Placeholder
            
            return {
                "summary": final_summary,
                "tokens_used": tokens_used, # Add token count
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} for doc {document.id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class KeywordExtractionProcessor(BaseProcessor):
    """Extract keywords using language models"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None):
        super().__init__(config)
        
        # Store the passed client
        self.llm_client = llm_client
        
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_keywords = self.config.get("max_keywords", 10)
        self.max_chars_context = self.config.get("max_chars_context", 4000)
    
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the document content to extract keywords"""
        try:
            # Get text from context (preferred) or document.content
            document_content = context.get("document_content", document.content or "")
            if not document_content:
                 logger.warning(f"No document content found in context or document for keyword extraction.")
                 return {"keywords": [], "error": "No content for keyword extraction"}

            logger.info(f"KeywordExtractionProcessor processing document {document.id}")

            if not self.llm_client:
                raise RuntimeError(f"{self.name}: OpenAI client is not available.")

            # Use the interface method
            response_text = await self.llm_client.generate_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Extrae las {self.max_keywords} palabras clave o frases clave más importantes del siguiente texto. Devuelve solo una lista JSON de strings. Ejemplo: [\"palabra clave 1\", \"frase clave 2\"]"},
                    {"role": "user", "content": document_content[:self.max_chars_context]}
                ],
                max_tokens=self.max_keywords * 10, # Estimate tokens needed
                temperature=0.2
            )
            
            # Parse the JSON response
            try:
                keywords = json.loads(response_text)
                if not isinstance(keywords, list):
                    raise ValueError("LLM did not return a JSON list.")
                # Optionally validate content is strings
                keywords = [str(kw) for kw in keywords][:self.max_keywords] # Ensure strings and limit count
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.warning(f"Failed to parse keyword list from LLM response: {parse_error}. Response: {response_text}")
                # Fallback: try regex extraction? or return error?
                keywords = [] # Return empty for now
                # Consider adding the raw response to the error field?
            
            logger.info(f"Keywords extracted for document {document.id}: {keywords}")
            tokens_used = context.get("total_tokens_used", 0) # Placeholder

            return {
                "keywords": keywords,
                "tokens_used": tokens_used, # Add token count
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} for doc {document.id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class SentimentAnalysisProcessor(BaseProcessor):
    """Perform sentiment analysis using language models"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None):
        super().__init__(config)
        
        # Store the passed client
        self.llm_client = llm_client
        
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.max_chars_context = self.config.get("max_chars_context", 4000)
    
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process document content for sentiment analysis"""
        try:
            # Get text from context (preferred) or document.content
            document_content = context.get("document_content", document.content or "")
            if not document_content:
                 logger.warning(f"No document content found in context or document for sentiment analysis.")
                 return {"sentiment": "NEUTRAL", "polarity": 0.0, "error": "No content for sentiment analysis"}

            logger.info(f"SentimentAnalysisProcessor processing document {document.id}")

            if not self.llm_client:
                 raise RuntimeError(f"{self.name}: OpenAI client is not available.")
            
            # Use the interface method
            response_text = await self.llm_client.generate_chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Clasifica el sentimiento del siguiente texto como POSITIVO, NEGATIVO o NEUTRAL. Responde solo con una de esas tres palabras."},
                    {"role": "user", "content": document_content[:self.max_chars_context]}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            sentiment = response_text.strip().upper()
            if sentiment not in ["POSITIVO", "NEGATIVO", "NEUTRAL"]:
                logger.warning(f"Unexpected sentiment response from LLM: {response_text}. Defaulting to NEUTRAL.")
                sentiment = "NEUTRAL"
            
            # Polarity is not directly available from this simple classification
            polarity = 0.0 
            if sentiment == "POSITIVO": polarity = 0.5 # Assign arbitrary polarity
            if sentiment == "NEGATIVO": polarity = -0.5

            logger.info(f"Sentiment analysis for document {document.id}: {sentiment}")
            tokens_used = context.get("total_tokens_used", 0) # Placeholder

            return {
                "sentiment": sentiment,
                "polarity": polarity,
                "tokens_used": tokens_used, # Add token count
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} for doc {document.id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class EmbeddingProcessor(BaseProcessor):
    """Generate embeddings for document chunks"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None):
        super().__init__(config, llm_client)
        self.model = self.config.get("model", "text-embedding-3-small")
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 200)
        logger.info(f"{self.name} initialized. Model: {self.model}, ChunkSize: {self.chunk_size}, Overlap: {self.chunk_overlap}")
        if not self.llm_client:
            logger.warning(f"{self.name} initialized without LLM client. Embedding generation will fail.")

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on character count with overlap."""
        if not text:
            return []

        chunk_size = self.chunk_size
        chunk_overlap = self.chunk_overlap

        # Ensure overlap is not larger than chunk size
        if chunk_overlap >= chunk_size:
            logger.warning(f"Chunk overlap ({chunk_overlap}) is greater than or equal to chunk size ({chunk_size}). Setting overlap to {chunk_size // 2}.")
            chunk_overlap = chunk_size // 2 # Adjust to a reasonable default like half the chunk size

        logger.info(f"Chunking text with character chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

        chunks = []
        start_index = 0
        text_len = len(text)

        while start_index < text_len:
            end_index = min(start_index + chunk_size, text_len)
            chunk = text[start_index:end_index]
            chunks.append(chunk)

            # Move start_index for the next chunk, considering overlap
            # If the next step would be 0 or negative, we are done
            step = chunk_size - chunk_overlap
            if step <= 0:
                 logger.warning(f"Chunk step size is zero or negative (chunk_size={chunk_size}, chunk_overlap={chunk_overlap}). Breaking chunking loop.")
                 break # Avoid infinite loop if overlap is too large

            start_index += step

            # Break if start_index hasn't advanced (e.g., very small step and end of text)
            # This prevents potential infinite loops in edge cases.
            if start_index >= end_index and end_index < text_len:
                 logger.warning(f"Chunking loop detected potential stall (start_index={start_index}, end_index={end_index}, text_len={text_len}). Breaking.")
                 break


        logger.info(f"Chunked text into {len(chunks)} chunks using character-based splitting with overlap.")
        return chunks

    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for document text (obtained from context or document)"""
        try:
            # Get text from context (preferred) or document object
            # Use 'document_content' key as populated by TextExtractionProcessor
            document_content = context.get("document_content", document.content or "") 
            if not document_content:
                 logger.warning(f"No document content found in context or document for embedding.")
                 return {"embeddings": [], "chunks_text": [], "chunk_count": 0, "error": "No content for embedding"}

            logger.info(f"EmbeddingProcessor processing document {document.id}")

            if not self.llm_client:
                 raise RuntimeError(f"{self.name}: LLM client is not available.")

            # Chunk the text
            chunks = self._chunk_text(document_content)
            chunk_count = len(chunks)
            
            if chunk_count == 0:
                logger.warning(f"No chunks generated from document content for doc {document.id}")
                return {"embeddings": [], "chunks_text": [], "chunk_count": 0}

            logger.info(f"Generating embeddings for {chunk_count} chunks using model {self.model}...")
            
            # Generate embeddings using the LLM client interface
            embeddings = await self.llm_client.generate_embeddings(
                texts=chunks,
                model=self.model
            )

            if not embeddings or len(embeddings) != chunk_count:
                 logger.error(f"LLM client failed to return valid embeddings. Expected {chunk_count}, got {len(embeddings) if embeddings else 0}")
                 raise ValueError("Embedding generation failed or returned incorrect number of vectors.")
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings for doc {document.id}")
            
            return {
                "embeddings": embeddings,
                "chunks_text": chunks,
                "chunk_count": chunk_count,
                "model": self.model, # Return the model used
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} for doc {document.id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

# Register of available processors
AVAILABLE_PROCESSORS = {
    "text_extraction": TextExtractionProcessor,
    "summarizer": SummarizerProcessor,
    "keyword_extraction": KeywordExtractionProcessor,
    "sentiment_analysis": SentimentAnalysisProcessor,
    "embedding": EmbeddingProcessor
}

def get_processor(processor_type: str, config: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClientInterface] = None) -> BaseProcessor:
    """
    Get an instance of a processor by its type
    
    Args:
        processor_type: Processor type
        config: Optional configuration
        llm_client: Optional shared LLM client instance
        
    Returns:
        BaseProcessor: Instance of the processor
        
    Raises:
        ValueError: If the processor type does not exist
    """
    if processor_type not in AVAILABLE_PROCESSORS:
        raise ValueError(f"Processor not found: {processor_type}")
    
    ProcessorClass = AVAILABLE_PROCESSORS[processor_type]
    # Pass the configuration directly to the constructor of the class
    return ProcessorClass(config=config, llm_client=llm_client) 