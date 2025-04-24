"""
Procesador para análisis de RFP
"""
from typing import Dict, Any, List, Optional
import uuid
import logging
import json
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime
from core.llm_interface import LLMClientInterface
from modules.analysis.prompts.rfp_prompts import (
    CRITERIA_EXTRACTION_SYSTEM_PROMPT,
    get_criteria_extraction_prompt,
    FRAMEWORK_GENERATION_SYSTEM_PROMPT,
    get_framework_generation_prompt
)

logger = logging.getLogger(__name__)

class RfpProcessor:
    """Procesador para el análisis de documentos RFP"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.default_model = "gpt-4o"
    
    def analyze_rfp_content(self, combined_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the combined content of RFP to extract criteria and generate evaluation framework
        
        Args:
            combined_text: Combined text of all documents
            user_id: ID del usuario para seguimiento de tokens (opcional)
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Verificar longitud del texto y truncar si es necesario
        from core.token_counter import TokenCounter
        token_count = TokenCounter.count_tokens(combined_text, self.default_model)
        max_tokens = TokenCounter.MODEL_CONTEXT_LIMITS.get(self.default_model, 4096) * 0.75  # 75% del límite
        
        if token_count > max_tokens:
            logger.warning(f"El texto combinado excede el límite de tokens ({token_count} > {max_tokens}). Truncando...")
            combined_text = TokenCounter.truncate_text_to_token_limit(combined_text, self.default_model, int(max_tokens))
            logger.info(f"Texto truncado a {TokenCounter.count_tokens(combined_text, self.default_model)} tokens")
        
        # Extract evaluation criteria
        extracted_criteria = self._extract_evaluation_criteria(combined_text, user_id)
        
        # Generate evaluation framework
        evaluation_framework = self._generate_evaluation_framework(extracted_criteria, user_id)
        
        # Return results
        return {
            "extracted_criteria": extracted_criteria,
            "evaluation_framework": evaluation_framework,
            "analyzed_at": datetime.utcnow().isoformat(),
            "token_usage": {
                "input_tokens": token_count,
                "truncated": token_count > max_tokens
            }
        }
    
    def _extract_evaluation_criteria(self, text_content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract evaluation criteria from RFP content
        
        Args:
            text_content: Text content
            
        Returns:
            Dict[str, Any]: Extracted criteria
        """
        try:
            # Use LLM to extract criteria
            if self.llm_client:
                # Preparar mensajes para la extracción de criterios
                messages = [
                    ("system", CRITERIA_EXTRACTION_SYSTEM_PROMPT),
                    ("user", get_criteria_extraction_prompt(text_content))
                ]
                
                # Necesitamos usar asyncio.run para llamar a la función asíncrona
                response = asyncio.run(self.llm_client.generate_chat_completion(
                    messages=[
                        {"role": message[0], "content": message[1]} for message in messages
                    ],
                    model=self.default_model,
                    response_format={"type": "json_object"},
                    user_id=user_id
                ))
                
                # Procesar respuesta
                import json
                if isinstance(response, str):
                    criteria = json.loads(response)
                else:
                    criteria = json.loads(response.choices[0].message.content)
                
                return criteria
            else:
                # Values by default if no LLM client is available
                logger.warning("No LLM client available, using default values")
                return {
                    "criteria": [
                        {
                            "title": "Experiencia técnica",
                            "description": "Experiencia demostrable en tecnologías relevantes",
                            "key_indicators": [
                                "Indicator 1",
                                "Indicator 2",
                                "Indicator 3",
                                "Indicator 4",
                                "Indicator 5"
                            ],
                            "retrieve_search_text": [
                                "Retrieve search text 1",
                                "Retrieve search text 2",
                                "Retrieve search text 3"
                            ],
                            "evidence_of_strong_response": [
                                "Strong response 1",
                                "Strong response 2",
                                "Strong response 3"
                            ]
                        }
                    ],
                    "summary": "Se requiere extraer criterios con un cliente LLM válido"
                }
        except Exception as e:
            logger.error(f"Error al extraer criterios: {e}")
            # Valores por defecto en caso de error
            return {
                "criteria": [],
                "summary": f"Error al extraer criterios: {str(e)}",
                "error": str(e)
            }
    
    def _generate_evaluation_framework(self, criteria: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generar framework de evaluación basado en los criterios extraídos
        
        Args:
            criteria: Criterios extraídos
            
        Returns:
            Dict[str, Any]: Framework de evaluación
        """
        
        logger.info("Generating evaluation framework" + str(criteria))
        try:
            # Use LLM to generate framework
            if self.llm_client:
                # Preparar mensajes para la generación del framework
                messages = [
                    ("system", FRAMEWORK_GENERATION_SYSTEM_PROMPT),
                    ("user", get_framework_generation_prompt(criteria))
                ]
                
                # Necesitamos usar asyncio.run para llamar a la función asíncrona
                response = asyncio.run(self.llm_client.generate_chat_completion(
                    messages=[
                        {"role": message[0], "content": message[1]} for message in messages
                    ],
                    model=self.default_model,
                    response_format={"type": "json_object"},
                    user_id=user_id
                ))
                
                # Procesar respuesta
                import json
                if isinstance(response, str):
                    framework = json.loads(response)
                else:
                    framework = json.loads(response.choices[0].message.content)
                
                # Validate framework structure
                if not all(
                    key in framework
                    for key in ["weighted_criteria", "scoring_scale", "evaluation_guide"]
                ):
                    raise ValueError("Response is missing required keys")

                return framework
            else:
                # Values by default if no LLM client is available
                logger.warning("No LLM client available, using default values")
                return {
                    "weighted_criteria": [
                        {
                            "title": "Error",
                            "weight": "100%"
                        }
                    ],
                    "scoring_scale": [
                        {
                            "score": 1,
                            "description": "Poor (Does not meet requirements)"
                        },
                        {
                            "score": 2,
                            "description": "Fair (Partially meets requirements)"
                        },
                        {
                            "score": 3,
                            "description": "Good (Meets basic requirements)"
                        },
                        {
                            "score": 4,
                            "description": "Very Good (Exceeds requirements in some areas)"
                        },
                        {
                            "score": 5,
                            "description": "Excellent (Significantly exceeds requirements)"
                        }
                    ],
                    "evaluation_guide": "Brief explanation on using the weighted scoring system",
                    "summary": f"Error to generate evaluation framework: {str(e)}",
                    "error": str(e)
                }
        except Exception as e:
            logger.error(f"Error to generate evaluation framework: {e}")
            # Values by default in case of error
            return {
                    "weighted_criteria": [
                        {
                            "criterion": "Error",
                            "weight": "100%"
                        }
                    ],
                    "scoring_scale": [
                        {
                            "score": 1,
                            "description": "Poor (Does not meet requirements)"
                        },
                        {
                            "score": 2,
                            "description": "Fair (Partially meets requirements)"
                        },
                        {
                            "score": 3,
                            "description": "Good (Meets basic requirements)"
                        },
                        {
                            "score": 4,
                            "description": "Very Good (Exceeds requirements in some areas)"
                        },
                        {
                            "score": 5,
                            "description": "Excellent (Significantly exceeds requirements)"
                        }
                    ],
                    "evaluation_guide": "Brief explanation on using the weighted scoring system",
                    "summary": f"Error to generate evaluation framework: {str(e)}",
                    "error": str(e)
                }