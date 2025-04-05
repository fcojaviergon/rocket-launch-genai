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
from openai import AsyncOpenAI 
from core.config import settings
import httpx 


import numpy as np
from pathlib import Path

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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def process(self, document_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document and return the results
        
        Args:
            document_content: Document content
            context: Contextual information and results of previous steps
            
        Returns:
            Dict[str, Any]: Processing results
        """
        pass

class TextExtractionProcessor(BaseProcessor):
    """Extract text from documents"""
    
    async def process(self, document_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and clean text from a document"""
        try:
            logger.info(f"TextExtractionProcessor processing document, content length: {len(document_content) if document_content else 0}")
            if not document_content or document_content.strip() == "":
                logger.warning("Document content is empty or whitespace")
                document_content = "No content available"
            
            # If the document is already text, simply clean it
            clean_text = self._clean_text(document_content)
            
            # Calculate basic statistics
            word_count = len(clean_text.split())
            char_count = len(clean_text)
            
            #logger.info(f"Text extracted successfully: {word_count} words, {char_count} chars")
            
            return {
                "extracted_text": clean_text,
                "word_count": word_count,
                "char_count": char_count,
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}", exc_info=True)
            return {
                "error": str(e),
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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Obtener API key con verificación
        api_key = self.config.get("api_key", settings.OPENAI_API_KEY)
        
        # Validar que la API key no esté vacía
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error(f"{self.name}: OPENAI_API_KEY no está definida o está vacía")
            logger.debug(f"API key value: '{api_key}'")
            # Intentar obtener directamente de las variables de entorno
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key or api_key.strip() == "":
                logger.error(f"{self.name}: No se pudo obtener OPENAI_API_KEY del entorno")
                self.client = None
                return
            else:
                logger.info(f"{self.name}: Se obtuvo OPENAI_API_KEY del entorno directamente")
        
        # --- Create httpx client explicitly WITHOUT proxies ---
        try:
            logger.debug(f"[{self.name}] Creating default httpx.AsyncClient()")
            http_client = httpx.AsyncClient() # Without explicit arguments
            logger.debug(f"[{self.name}] httpx.AsyncClient() created successfully.")

            # Parameters for AsyncOpenAI, including the http_client
            client_params = {
                "api_key": api_key,
                "http_client": http_client # Pass the default client
            }

            self.client = AsyncOpenAI(**client_params)
            logger.info(f"AsyncOpenAI initialized for {self.name} with default http_client (chat_service style)")

        except Exception as e:
            # Log the specific error during initialization
            logger.error(f"Error initializing AsyncOpenAI or httpx.AsyncClient in {self.name}: {e}", exc_info=True)
            self.client = None # Ensure self.client is None if it fails
        
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Resumir el siguiente texto en un párrafo conciso"},
                    {"role": "user", "content": text}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
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
        if len(summaries) == 1:
            return summaries[0]
        
        combined_text = "\n\n".join([f"Sección {i+1}: {summary}" for i, summary in enumerate(summaries)])
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Combina estos resúmenes parciales en un único resumen coherente"},
                    {"role": "user", "content": combined_text}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error al combinar resúmenes: {str(e)}")
            return "\n\n".join(["RESUMEN FINAL (no se pudo combinar automáticamente):"] + summaries)
    
    async def process(self, document_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the text using OpenAI with chunking para documentos grandes"""
        if not self.client:
             logger.error(f"{self.name}: AsyncOpenAI client not initialized")
             return {
                 "error": f"AsyncOpenAI client not initialized in {self.name}",
                 "processor": self.name,
                 "timestamp": datetime.utcnow().isoformat()
             }
        try:
            text_to_summarize = context.get("extracted_text", document_content)
            if not text_to_summarize or text_to_summarize.strip() == "":
                logger.warning(f"{self.name}: No text to summarize")
                return {
                    "error": "No text to summarize",
                    "processor": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Dividir el texto en chunks si es necesario
            chunks = self._chunk_text(text_to_summarize, self.max_chunk_tokens)
            total_chunks = len(chunks)
            logger.info(f"{self.name}: Procesando documento en {total_chunks} chunks")
            
            if total_chunks == 1:
                # Si solo hay un chunk, resumir directamente
                logger.info(f"{self.name}: Resumiendo texto directamente (un solo chunk)")
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "Resume el siguiente texto en un párrafo conciso"},
                            {"role": "user", "content": chunks[0]}
                        ],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    summary = response.choices[0].message.content.strip()
                    tokens_used = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
                    
                    logger.info(f"{self.name}: Summary generated successfully, {tokens_used} tokens used")
                    
                    return {
                        "summary": summary,
                        "tokens_used": tokens_used,
                        "processor": self.name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error in direct summarization: {str(e)}")
                    return {
                        "error": str(e),
                        "processor": self.name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            else:
                # Resumir cada chunk por separado
                logger.info(f"{self.name}: Procesando resumen en {total_chunks} partes")
                chunk_summaries = []
                total_tokens = 0
                
                for i, chunk in enumerate(chunks):
                    logger.info(f"{self.name}: Resumiendo chunk {i+1}/{total_chunks}")
                    chunk_summary = await self._summarize_chunk(chunk)
                    chunk_summaries.append(chunk_summary)
                    
                # Combinar los resúmenes en uno solo
                logger.info(f"{self.name}: Combinando {len(chunk_summaries)} resúmenes parciales")
                final_summary = await self._combine_summaries(chunk_summaries)
                
                logger.info(f"{self.name}: Resumen final generado exitosamente a partir de {total_chunks} chunks")
                
                return {
                    "summary": final_summary,
                    "chunks_processed": total_chunks,
                    "processor": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error in {self.name} during process: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class KeywordExtractionProcessor(BaseProcessor):
    """Extract keywords from text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Obtener API key con verificación
        api_key = self.config.get("api_key", settings.OPENAI_API_KEY)
        
        # Validar que la API key no esté vacía
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error(f"{self.name}: OPENAI_API_KEY no está definida o está vacía")
            logger.debug(f"API key value: '{api_key}'")
            # Intentar obtener directamente de las variables de entorno
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key or api_key.strip() == "":
                logger.error(f"{self.name}: No se pudo obtener OPENAI_API_KEY del entorno")
                self.client = None
                return
            else:
                logger.info(f"{self.name}: Se obtuvo OPENAI_API_KEY del entorno directamente")
        
        # --- Create httpx client explicitly WITHOUT proxies ---
        try:
            logger.debug(f"[{self.name}] Creating default httpx.AsyncClient()")
            http_client = httpx.AsyncClient() # Simple
            logger.debug(f"[{self.name}] httpx.AsyncClient() created successfully.")
            client_params = {"api_key": api_key, "http_client": http_client}

            self.client = AsyncOpenAI(**client_params)
            logger.info(f"AsyncOpenAI initialized for {self.name} with default http_client (chat_service style)")
        except Exception as e:
            logger.error(f"Error initializing AsyncOpenAI or httpx.AsyncClient in {self.name}: {e}", exc_info=True)
            self.client = None
            
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.num_keywords = self.config.get("num_keywords", 10)
    
    async def process(self, document_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords from text using OpenAI"""
        if not self.client:
             return {
                 "error": f"AsyncOpenAI client not initialized in {self.name}",
                 "processor": self.name,
                 "timestamp": datetime.utcnow().isoformat()
             }
        try:
            text_to_analyze = context.get("extracted_text", document_content)
            max_length = min(len(text_to_analyze), 4000)
            truncated_text = text_to_analyze[:max_length]
            
            # Asynchronous call with await
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"Extract {self.num_keywords} keywords."},
                    {"role": "user", "content": truncated_text}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            keywords_text = response.choices[0].message.content.strip()
            # More robust handling if the response is not a comma-separated list
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
            
            return {
                "keywords": keywords,
                "tokens_used": tokens_used,
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} durante process: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class SentimentAnalysisProcessor(BaseProcessor):
    """Analyze the sentiment of text"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Obtener API key con verificación
        api_key = self.config.get("api_key", settings.OPENAI_API_KEY)
        
        # Validar que la API key no esté vacía
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error(f"{self.name}: OPENAI_API_KEY no está definida o está vacía")
            logger.debug(f"API key value: '{api_key}'")
            # Intentar obtener directamente de las variables de entorno
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key or api_key.strip() == "":
                logger.error(f"{self.name}: No se pudo obtener OPENAI_API_KEY del entorno")
                self.client = None
                return
            else:
                logger.info(f"{self.name}: Se obtuvo OPENAI_API_KEY del entorno directamente")
       
        
        # --- Create httpx client explicitly WITHOUT proxies ---
        try:
            logger.debug(f"[{self.name}] Creating default httpx.AsyncClient()")
            http_client = httpx.AsyncClient() # Simple
            logger.debug(f"[{self.name}] httpx.AsyncClient() created successfully.")
            client_params = {"api_key": api_key, "http_client": http_client}
      
            self.client = AsyncOpenAI(**client_params)
            logger.info(f"AsyncOpenAI initialized for {self.name} with default http_client (chat_service style)")
        except Exception as e:
            logger.error(f"Error initializing AsyncOpenAI or httpx.AsyncClient in {self.name}: {e}", exc_info=True)
            self.client = None
        
        self.model = self.config.get("model", "gpt-3.5-turbo")
    
    async def process(self, document_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the sentiment of text using OpenAI"""
        if not self.client:
             return {
                 "error": f"AsyncOpenAI client not initialized in {self.name}",
                 "processor": self.name,
                 "timestamp": datetime.utcnow().isoformat()
             }
        try:
            text_to_analyze = context.get("extracted_text", document_content)
            max_length = min(len(text_to_analyze), 4000)
            truncated_text = text_to_analyze[:max_length]
            
            # Asynchronous call with await
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Analyze sentiment (POSITIVE, NEGATIVE, NEUTRAL) and polarity (-1 to 1)."},
                    {"role": "user", "content": truncated_text}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            sentiment_text = response.choices[0].message.content.strip()
            
            sentiment = "NEUTRAL"
            polarity = 0.0
            
            sentiment_upper = sentiment_text.upper()
            if "POSITIVE" in sentiment_upper:
                sentiment = "POSITIVE"
            elif "NEGATIVE" in sentiment_upper:
                sentiment = "NEGATIVE"
            
            polarity_match = re.search(r'(-?\d+(\.\d+)?)', sentiment_text)
            if polarity_match:
                try:
                    polarity = float(polarity_match.group(1))
                    polarity = max(-1.0, min(1.0, polarity))
                except ValueError:
                    logger.warning(f"Could not convertir la polarity a float: {polarity_match.group(1)}")
                    pass # Mantener 0.0 si falla la conversión
            
            return {
                "sentiment": sentiment,
                "polarity": polarity,
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in {self.name} durante process: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "processor": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }

class EmbeddingProcessor(BaseProcessor):
    """Generate embeddings (vectors) of a document for semantic search"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the embedding processor"""
        super().__init__(config)
        self.name = config.get("name", "embedding_processor")

        self.model = config.get("model", "text-embedding-3-small")
        self.chunk_size = config.get("chunk_size", 1000)
        self.chunk_overlap = config.get("chunk_overlap", 200)
        # The actual dimension will be given by OpenAI, so it is not necessary to configure it here unless you want to validate it.
        # self.dimension = config.get("dimension", 1536)

        # Obtener API key con verificación
        api_key = self.config.get("api_key", settings.OPENAI_API_KEY)
        
        # Validar que la API key no esté vacía
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error(f"{self.name}: OPENAI_API_KEY no está definida o está vacía")
            logger.debug(f"API key value: '{api_key}'")
            # Intentar obtener directamente de las variables de entorno
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key or api_key.strip() == "":
                logger.error(f"{self.name}: No se pudo obtener OPENAI_API_KEY del entorno")
                self.client = None
                return
            else:
                logger.info(f"{self.name}: Se obtuvo OPENAI_API_KEY del entorno directamente")
        
        try:
            # Use default httpx client (without explicit proxies)
            http_client = httpx.AsyncClient()
            self.client = AsyncOpenAI(api_key=api_key, http_client=http_client)
            logger.info(f"AsyncOpenAI initialized for {self.name}")
        except Exception as e:
            logger.error(f"Error initializing AsyncOpenAI or httpx.AsyncClient in {self.name}: {str(e)}", exc_info=True)
            self.client = None

    def _extract_text_from_file(self, file_path_str: str) -> Optional[str]:
        """Extract text from a file based on its extension."""
        file_path = Path(file_path_str)
        if not file_path.is_file():
            logger.error(f"The file does not exist in the path: {file_path_str}")
            return None

        extension = file_path.suffix.lower()
        extracted_text = ""

        try:
            if extension == ".pdf":
                # if not fitz: <-- REMOVE
                if not PdfReader: # <-- ADD
                    # logger.error("PyMuPDF (fitz) is not installed. Cannot process PDF.") <-- REMOVE
                    logger.error("pypdf is not installed. Cannot process PDF.") # <-- ADD
                    return None
                logger.info(f"Extracting text from PDF: {file_path_str}")
                # doc = fitz.open(file_path) <-- REMOVE
                # texts = [page.get_text("text") for page in doc] <-- REMOVE
                # doc.close() <-- REMOVE
                reader = PdfReader(file_path) # <-- ADD
                texts = [page.extract_text() for page in reader.pages if page.extract_text()] # <-- ADD (Added check for non-empty text)
                extracted_text = "\\n".join(texts)
            elif extension == ".docx":
                if not docx:
                     logger.error("python-docx is not installed. Cannot process DOCX.")
                     return None
                logger.info(f"Extracting text from DOCX: {file_path_str}")
                doc = docx.Document(file_path)
                texts = [p.text for p in doc.paragraphs]
                extracted_text = "\n".join(texts)
            elif extension == ".txt":
                logger.info(f"Reading text file: {file_path_str}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = f.read()
            else:
                logger.warning(f"Unsupported file extension for direct extraction: {extension}")
                return None # Do not try to process unknown extensions directly

            logger.info(f"Text extracted from {file_path.name}: {len(extracted_text)} characters.")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting text from {file_path_str}: {e}", exc_info=True)
            return None # Return None if extraction fails

    def _chunk_text(self, text: str) -> List[str]:
        """Divide the text into overlapping chunks"""
        if not text: # Handle empty text
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            # Ensure the step is not zero or negative if overlap >= size
            step = self.chunk_size - self.chunk_overlap
            start += step if step > 0 else self.chunk_size # Advance at least 1 if overlap is large
        return [chunk for chunk in chunks if chunk.strip()] # Ignore empty chunks

    # --- MODIFIED process METHOD ---
    async def process(self, document: Document, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from the file if necessary, divide it into chunks,
        and generate embeddings using OpenAI.
        Receives the complete Document object.
        """
        if not self.client:
            return {"error": f"AsyncOpenAI client not initialized in {self.name}"} # Same error as before

        text_to_process = None

        # 1. Intentar extraer texto del archivo usando file_path
        if document.file_path:
            logger.info(f"Attempting text extraction from file: {document.file_path}") # Log attempt
            text_to_process = self._extract_text_from_file(document.file_path)
            if text_to_process is None:
                logger.warning(f"Text extraction failed for file: {document.file_path}") # Log failure
        else:
            logger.warning(f"Document {document.id} does not have file_path. Cannot extract text from the file.")

        # 2. Fallback: If text cannot be extracted or there is no file_path, use document.content
        #    BUT only if it does not seem to be a binary placeholder.
        if text_to_process is None:
            logger.warning(f"Could not extract text from the file for doc {document.id}. Trying to use 'document.content'.")
            # Log the content (or its absence/placeholder status) for clarity
            if document.content:
                if document.content.startswith("[Archivo"):
                    logger.warning(f"\'document.content\' for doc {document.id} starts with placeholder.")
                else:
                    logger.info(f"Using 'document.content' as text source for doc {document.id}.")
                    text_to_process = document.content
            else:
                 logger.warning(f"\'document.content\' for doc {document.id} is empty or null.")

            # Final check before erroring out
            if text_to_process is None:
                 logger.error(f"Could not get valid text content for doc {document.id} from file or 'content'.")
                 return {
                     "error": "Could not get valid text content to process.",
                     "processor": self.name,
                     "timestamp": datetime.utcnow().isoformat()
                 }

        # 3. Chunking
        chunks = self._chunk_text(text_to_process)
        if not chunks:
            logger.warning(f"Processed text for doc {document.id} resulted in 0 chunks.")
            return {"embeddings": [], "chunks_text": [], "chunk_count": 0 } # Return empty

        logger.info(f"Processed text for doc {document.id} divided into {len(chunks)} chunks for embeddings.")

        # 4. Generation of embeddings
        embeddings = []
        try:
            # It is more efficient to send the chunks in batch if the API allows it
            logger.info(f"Generating embeddings for {len(chunks)} chunks with model {self.model}...")
            response = await self.client.embeddings.create(
                input=chunks, # Pass the list of chunks
                model=self.model
            )
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings.")

            # Validate that the number of embeddings matches the number of chunks
            if len(embeddings) != len(chunks):
                logger.error(f"Discrepancy! Expected {len(chunks)} embeddings but received {len(embeddings)}.")
                # You could try to retry, truncate, or fail
                return {"error": "Discrepancy in the number of embeddings received from OpenAI."}

        except Exception as e:
            logger.error(f"Error generating embeddings for the chunks of doc {document.id}: {e}", exc_info=True)
            return {"error": f"Error in calling OpenAI Embeddings: {e}" }

        # 5. Result
        return {
            "embeddings": embeddings,
            "chunks_text": chunks, # ¡Los chunks de texto REAL!
            "model": self.model,
            "dimension": len(embeddings[0]) if embeddings else 0, # Dimensión real del primer vector
            "chunk_count": len(chunks),
            "processor": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _initialize_openai_client(self):
        """Initialize OpenAI client with proper configuration"""
        if self.client:
            return self.client
            
        # Obtener API key con verificación
        api_key = os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY)
        
        # Validar que la API key no esté vacía
        if not api_key or api_key.strip() == "" or api_key == "None":
            logger.error(f"{self.name}: OPENAI_API_KEY no está definida o está vacía")
            return None
    
        timeout = httpx.Timeout(60.0)
        
        try:
            # Create HTTP client for OpenAI
            logger.info(f"[{self.name}] Initializing OpenAI client")
            from openai import AsyncOpenAI
            
            # Reduce excessive debug logging for production
            self.client = AsyncOpenAI(
                api_key=api_key,
                timeout=timeout,
            )
            return self.client
        except Exception as e:
            logger.error(f"[{self.name}] Error initializing OpenAI client: {str(e)}")
            return None

# Register of available processors
AVAILABLE_PROCESSORS = {
    "text_extraction": TextExtractionProcessor,
    "summarizer": SummarizerProcessor,
    "keyword_extraction": KeywordExtractionProcessor,
    "sentiment_analysis": SentimentAnalysisProcessor,
    "embedding": EmbeddingProcessor
}

def get_processor(processor_type: str, config: Optional[Dict[str, Any]] = None) -> BaseProcessor:
    """
    Get an instance of a processor by its type
    
    Args:
        processor_type: Processor type
        config: Optional configuration
        
    Returns:
        BaseProcessor: Instance of the processor
        
    Raises:
        ValueError: If the processor type does not exist
    """
    if processor_type not in AVAILABLE_PROCESSORS:
        raise ValueError(f"Processor not found: {processor_type}")
    
    ProcessorClass = AVAILABLE_PROCESSORS[processor_type]
    # Pass the configuration directly to the constructor of the class
    return ProcessorClass(config) 