"""
RFP document processor pipeline
"""
import uuid
from typing import Dict, Any
import json
from datetime import datetime
import logging
from core.llm_interface import LLMClientInterface

logger = logging.getLogger(__name__)

class RfpPipeline:
    """Pipeline for RFP documents"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.sync_client = True
        self.default_model = "gpt-4o"
        

    async def process(self, pipeline_id: uuid.UUID, document: Dict[str, Any], text_content: str = None) -> Dict[str, Any]:
        """
        Process an RFP document to extract criteria and generate evaluation framework
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            text_content: Document content (optional, if not provided it will be extracted from the document)
            
        Returns:
            Dict[str, Any]: Processing results
        """
        
        # Initialize context
        context = {
            "pipeline_id": pipeline_id,
            "document_id": document["id"],
            "document_title": document["title"],
            "extracted_criteria": {},
            "evaluation_framework": {}
        }
        
        # Get document content if not provided
        if text_content is None:
            text_content = await self._get_document_content(document)
        
        context["text_content"] = text_content
        
        # Extract evaluation criteria
        await self._extract_evaluation_criteria(context)
        
        # Generate evaluation framework
        await self._generate_evaluation_framework(context)
        
        # Clean up and return results
        return self._cleanup_and_return(context)
    
    def process_sync(self, pipeline_id: uuid.UUID, document: Dict[str, Any], text_content: str = None) -> Dict[str, Any]:
        """
        Synchronous version of process for use in Celery tasks
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            text_content: Document content (optional, if not provided it will be extracted from the document)
            
        Returns:
            Dict[str, Any]: Processing results
        """
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.process(pipeline_id, document, text_content))
        finally:
            loop.close()
    
    async def _get_document_content(self, document: Dict[str, Any]) -> str:
        """
        Get document content by reading the file from disk
        
        Args:
            document: Document
            
        Returns:
            str: Document content
        """
        # Check if we have a file path
        if document.get("file_path"):
            try:
                # In a real environment, we would read the file and extract the text
                # depending on the file type (PDF, DOCX, etc.)
                import os
                
                # Check if the file exists
                if os.path.exists(document["file_path"]):
                    # Simulate text extraction from the file
                    # In a real environment, we would use libraries like PyPDF2, python-docx, etc.
                    logger.info(f"Reading file {document['file_path']}")
                    
                    # Simulate text extraction based on the file type
                    if document["file_path"].lower().endswith('.pdf'):
                        # Simulate PDF extraction
                        return f"[Extracted content from PDF: {document['title']}] This is simulated content for demonstration."
                    elif document["file_path"].lower().endswith(('.docx', '.doc')):
                        # Simulate Word extraction
                        return f"[Extracted content from DOCX: {document['title']}] This is simulated content for demonstration."
                    else:
                        # For other file types, try to read as plain text
                        try:
                            with open(document["file_path"], 'r', encoding='utf-8') as f:
                                return f.read()
                        except Exception as e:
                            logger.error(f"Error reading file {document['file_path']}: {e}")
                            return f"Error reading file {document['title']}. Simulated content for demonstration."
                else:
                    logger.warning(f"File not found: {document['file_path']}")
                    return f"File not found: {document['title']}. Simulated content for demonstration."
                    
            except Exception as e:
                logger.error(f"Error processing file {document['file_path']}: {e}")
                return f"Error processing file {document['title']}. Simulated content for demonstration."
        
        # If no file or error, return an error message
        logger.warning(f"No file found for document {document['id']}")
        return f"No content found for document {document['title']}. Simulated content for demonstration."
    
    async def _extract_evaluation_criteria(self, context: Dict[str, Any]) -> None:
        """
        Extract evaluation criteria from document content
        
        Args:
            context: Processing context
        """
        # Inicializar extracted_criteria con un valor predeterminado
        extracted_criteria = {
            "criteria": [
                {
                    "title": "Criterio por defecto",
                    "description": "Descripción por defecto",
                    "key_indicators": ["Indicador 1", "Indicador 2", "Indicador 3"],
                    "retrieve_search_text": ["Búsqueda 1", "Búsqueda 2", "Búsqueda 3"],
                    "evidence_of_strong_response": ["Evidencia 1", "Evidencia 2", "Evidencia 3"]
                }
            ]
        }
        
        # Obtener el contenido del documento, primero intentar text_content y luego document_content
        document_content = context.get("text_content")
        
        logger.info(f"Document content: {document_content[:100]}...")
        
        # Truncar el contenido si es demasiado largo
        max_chars = 440000  # Aproximadamente 110,000 tokens
        if len(document_content) > max_chars:
            document_content = document_content[:max_chars]
        
        # Definir la estructura JSON esperada para el response_format
        json_schema = {
            "type": "object",
            "properties": {
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "key_indicators": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "retrieve_search_text": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "evidence_of_strong_response": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["title", "description", "key_indicators", "retrieve_search_text", "evidence_of_strong_response"]
                    }
                }
            },
            "required": ["criteria"]
        }
        
        # Preparar el prompt con el contenido del documento
        formatted_prompt = f"""
        Analyze the following Request for Proposal (RFP) document and extract the key evaluation criteria for the proposals:

        {document_content}

        For each identified evaluation criterion:
           a) Provide a clear, specific title for the criterion.
           b) Write a detailed description that explains what exactly should be evaluated.
           c) List 3-5 key indicators that the evaluator will use to evaluate the criterion.
           d) Your task is to generate three different versions of the given criterion to retrieve relevant documents from a vector database.
           e) For each criterion, specify the type of evidence or information that would constitute a strong response.
        """
        
        if self.llm_client:
            try:
                # Usar el modelo predeterminado definido en la configuración
                model = self.default_model
                logger.info(f"Extracting criteria using LLM model (sync): {model}")
                
                # Llamar al LLM para generar la respuesta con formato JSON
                response = self.llm_client.generate_chat_completion_sync(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a senior project manager with experience in evaluating proposals for RFPs. You must respond in valid JSON format."},
                        {"role": "user", "content": formatted_prompt + "\n\nYour response must be in valid JSON format with the following structure: {\"criteria\": [{\"title\": string, \"description\": string, \"key_indicators\": [string], \"retrieve_search_text\": [string], \"evidence_of_strong_response\": [string]}]}"}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                logger.info(f"Response from LLM: {response}")
                # Intentar parsear la respuesta JSON
                try:
                    # Intentar parsear el JSON
                    if isinstance(response, str):
                        parsed_response = json.loads(response)
                        if parsed_response and "criteria" in parsed_response:
                            extracted_criteria = parsed_response
                            logger.info(f"Successfully extracted criteria with {len(extracted_criteria.get('criteria', []))} items")
                    else:
                        # Si es un objeto de respuesta de OpenAI
                        try:
                            json_response = response.choices[0].message.content
                            parsed_response = json.loads(json_response)
                            if parsed_response and "criteria" in parsed_response:
                                extracted_criteria = parsed_response
                                logger.info(f"Successfully extracted criteria with {len(extracted_criteria.get('criteria', []))} items")
                        except Exception as resp_error:
                            logger.error(f"Error extracting content from OpenAI response: {resp_error}")
                except Exception as json_error:
                    logger.error(f"Error parsing JSON response: {json_error}")
                    # Mantener el valor predeterminado
                
            except Exception as e:
                logger.error(f"Error extracting criteria (sync): {e}")
                # Mantener el valor predeterminado
        else:
            # Si no hay cliente LLM disponible
            logger.warning("No LLM client available, using default criteria")
            # Mantener el valor predeterminado
        
        context["extracted_criteria"] = extracted_criteria
    
    async def _generate_evaluation_framework(self, context: Dict[str, Any]) -> None:
        """
        Generate evaluation framework based on extracted criteria
        
        Args:
            context: Analysis context
        """
        # Inicializar framework con un valor predeterminado
        framework = {
            "weighted_criteria": [
                {"criterion": "Criterio por defecto", "weight": "100%"}
            ],
            "scoring_scale": [
                {"score": 1, "description": "Malo (No cumple)"},
                {"score": 2, "description": "Regular (Cumple parcialmente)"},
                {"score": 3, "description": "Bueno (Cumple los requisitos)"},
                {"score": 4, "description": "Muy bueno (Supera los requisitos)"},
                {"score": 5, "description": "Excelente (Supera ampliamente los requisitos)"}
            ],
            "evaluation_guide": "Usa este sistema para evaluar propuestas."
        }
        
        extracted_criteria = context.get("extracted_criteria", {"criteria": []})
        
        # Definir la estructura JSON esperada para el response_format
        json_schema = {
            "type": "object",
            "properties": {
                "weighted_criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "criterion": {"type": "string"},
                            "weight": {"type": "string"}
                        },
                        "required": ["criterion", "weight"]
                    }
                },
                "scoring_scale": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "integer"},
                            "description": {"type": "string"}
                        },
                        "required": ["score", "description"]
                    }
                },
                "evaluation_guide": {"type": "string"}
            },
            "required": ["weighted_criteria", "scoring_scale", "evaluation_guide"]
        }
        
        # Preparar el prompt para generar el framework
        criteria_json = json.dumps(extracted_criteria)
        formatted_prompt = f"""
        Based on the following evaluation criteria for an RFP:

        {criteria_json}

        Please perform the following tasks:

        1. Assign a weight to each criterion based on its importance. The weights should add up to 100%.

        2. Create a scoring scale from 1-5 with descriptions for each score level:
           - 1: Poor (Does not meet requirements)
           - 2: Fair (Partially meets requirements)
           - 3: Good (Meets basic requirements)
           - 4: Very Good (Exceeds requirements in some areas)
           - 5: Excellent (Significantly exceeds requirements)

        3. Provide a brief explanation of how to use this weighted scoring system for proposal evaluation.
        """
        
        if self.llm_client:
            try:
                # Llamar al LLM para generar la respuesta con formato JSON
                response = self.llm_client.generate_chat_completion_sync(
                    model=self.default_model,
                    messages=[
                        {"role": "system", "content": "You are a senior project manager with experience in evaluating proposals for RFPs. You must respond in valid JSON format."},
                        {"role": "user", "content": formatted_prompt + "\n\nYour response must be in valid JSON format with the following structure: {\"weighted_criteria\": [{\"criterion\": string, \"weight\": string}], \"scoring_scale\": [{\"score\": number, \"description\": string}], \"evaluation_guide\": string}"}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                logger.info(f"Response from LLM: {response}")
                
                # Intentar parsear la respuesta JSON
                try:
                    # Extraer JSON si está en un bloque de código markdown
                    if isinstance(response, str) and (response.startswith('```json') or response.startswith('```')):
                        import re
                        code_match = re.search(r'```(?:json)?\s*(.+?)\s*```', response, re.DOTALL)
                        if code_match:
                            response = code_match.group(1).strip()
                    
                    # Intentar parsear el JSON
                    if isinstance(response, str):
                        parsed_response = json.loads(response)
                        if parsed_response and "weighted_criteria" in parsed_response:
                            framework = parsed_response
                            logger.info(f"Successfully generated evaluation framework with {len(framework.get('weighted_criteria', []))} criteria")
                    else:
                        # Si es un objeto de respuesta de OpenAI
                        try:
                            json_response = response.choices[0].message.content
                            parsed_response = json.loads(json_response)
                            if parsed_response and "weighted_criteria" in parsed_response:
                                framework = parsed_response
                                logger.info(f"Successfully generated evaluation framework with {len(framework.get('weighted_criteria', []))} criteria")
                        except Exception as resp_error:
                            logger.error(f"Error extracting content from OpenAI response: {resp_error}")
                except Exception as json_error:
                    logger.error(f"Error parsing JSON response: {json_error}")
                    # Mantener el valor predeterminado
                
            except Exception as e:
                logger.error(f"Error generating framework (sync): {e}")
                # Mantener el valor predeterminado
        else:
            # Si no hay cliente LLM, usar el framework predeterminado
            logger.warning("No LLM client available, using default framework (sync)")
            # Mantener el valor predeterminado
        
        context["evaluation_framework"] = framework
        
        
    def _cleanup_and_return(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up context and return results
        
        Args:
            context: Processing context
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Simplemente devolver los resultados sin validación adicional
        return {
            "pipeline_id": context.get("pipeline_id"),
            "document_id": context.get("document_id"),
            "document_title": context.get("document_title"),
            "extracted_criteria": context.get("extracted_criteria", {"criteria": []}),
            "evaluation_framework": context.get("evaluation_framework", {}),
            "processed_at": datetime.utcnow().isoformat()
        }
