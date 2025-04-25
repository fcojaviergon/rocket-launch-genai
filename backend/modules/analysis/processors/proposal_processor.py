"""
Procesador para análisis de propuestas
"""
from typing import Dict, Any, List, Optional, Tuple
import uuid
import logging
import json
from sqlalchemy.orm import Session
from datetime import datetime
from core.llm_interface import LLMClientInterface
from modules.document.service import DocumentService
from modules.analysis.prompts.proposal_prompts import (
    CRITERION_EVALUATOR_SYSTEM_PROMPT,
    get_criterion_evaluation_prompt,
    TECHNICAL_EVALUATION_SYSTEM_PROMPT,
    get_technical_evaluation_prompt,
    GRAMMAR_EVALUATION_SYSTEM_PROMPT,
    get_grammar_evaluation_prompt,
    CONSISTENCY_EVALUATION_SYSTEM_PROMPT,
    get_consistency_evaluation_prompt
)

logger = logging.getLogger(__name__)

class ProposalProcessor:
    """Procesador para el análisis de propuestas"""
    
    def __init__(self, llm_client: LLMClientInterface, document_service: Optional[DocumentService] = None):
        self.llm_client = llm_client
        self.document_service = document_service
        self.default_model = "gpt-4o"
        self.embedding_model = "text-embedding-3-small"
    
    def analyze_proposal_content(
        self, 
        proposal_text: str, 
        extracted_criteria: Dict[str, Any],
        evaluation_framework: Dict[str, Any],
        pipeline_id: uuid.UUID,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analizar el contenido de una propuesta con respecto a un análisis de RFP
        
        Args:
            proposal_text: Texto de la propuesta
            extracted_criteria: Criterios extraídos del RFP
            evaluation_framework: Framework de evaluación del RFP
            pipeline_id: ID del pipeline de análisis
            db: Sesión de base de datos
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        logger.info(f"Iniciando análisis de propuesta para pipeline {pipeline_id}")
        
        # Extraer criterios y framework de evaluación del análisis de RFP
        # Verificar si extracted_criteria es un diccionario con la clave 'criteria'
        if isinstance(extracted_criteria, dict) and 'criteria' in extracted_criteria:
            criteria_list = extracted_criteria.get('criteria', [])
        else:
            # Si no es un diccionario o no tiene la clave 'criteria', usar directamente
            criteria_list = extracted_criteria if isinstance(extracted_criteria, list) else []
        
        # Verificar si framework es válido
        if not criteria_list or not evaluation_framework:
            logger.error(f"No se encontraron criterios o framework en el análisis de RFP para pipeline {pipeline_id}")
            return {
                "error": "No se encontraron criterios o framework en el análisis de RFP",
                "analyzed_at": datetime.utcnow().isoformat()
            }
        
        criteria_evaluations = []
        
        logger.info(f"Iniciando evaluación de {len(criteria_list)} criterios para pipeline {pipeline_id}")
        
        # Evaluar criterios
        for criterion in criteria_list:
            criterion_title = criterion.get("title")
            criterion_description = criterion.get("description")
            criterion_retrieve_search_text = criterion.get("retrieve_search_text")
            
            # Manejar el caso en que criterion_retrieve_search_text sea una lista
            search_components = [criterion_title, criterion_description]
            
            # Si criterion_retrieve_search_text es una lista, unir sus elementos
            if isinstance(criterion_retrieve_search_text, list):
                search_components.extend([str(item) for item in criterion_retrieve_search_text if item])
            elif criterion_retrieve_search_text:  # Si es una cadena no vacía
                search_components.append(criterion_retrieve_search_text)
                
            search_text = " ".join(filter(None, search_components))
            logger.info(
                f"Search text for criterion {criterion_title}: {search_text[:200]}..."
            )
                       
            # Obtener peso del criterio
            weight = 0
            for fw_criterion in evaluation_framework.get("criteria", []):
                if fw_criterion.get("title") == criterion_title:
                    weight = fw_criterion.get("weight", 0)
                    break

            if search_text:
                try:
                    document_service = DocumentService(llm_client=self.llm_client)
                    search_results = document_service.search_documents_by_analysis_id_sync(
                        db=db,
                        query=search_text,
                        model=self.embedding_model,
                        limit=5,
                        min_similarity=0.2,
                        user_id=uuid.UUID(user_id) if user_id else None,
                        pipeline_id=pipeline_id
                    )
                    
                    logger.info(f"Search results for criterion {criterion_title}: {search_results}")
                    # Extraer texto relevante de los resultados
                    if search_results and len(search_results) > 0:
                        # Verificar si los resultados tienen el campo 'chunk_text' o 'content'
                        if 'chunk_text' in search_results[0]:
                            relevant_text = "\n\n".join([result.get("chunk_text", "") for result in search_results])
                        else:
                            relevant_text = "\n\n".join([result.get("content", "") for result in search_results])
                        logger.info(f"Búsqueda semántica encontró {len(search_results)} resultados para criterio '{criterion_title}'")
                        # Realizar evaluación del criterio
                        try:
                            # Usar búsqueda semántica y evaluación del criterio
                            evaluation = self._evaluate_criterion(
                                chunk=relevant_text,
                                criterion=criterion,
                                weight=weight,
                                scoring_scale=evaluation_framework.get("scoring_scale", {}),
                                pipeline_id=pipeline_id,
                                db=db,
                                user_id=user_id
                            )
                            criteria_evaluations.append(evaluation)
                            logger.info(f"Criterio {criterion_title} evaluado con score {evaluation['score']}")
                        except Exception as e:
                            logger.error(f"Error al evaluar criterio {criterion_title} para pipeline {pipeline_id}: {e}")
                            criteria_evaluations.append({
                                "criterion": criterion_title,
                                "score": 0,
                                "weight": weight,
                                "justification": f"Error al evaluar: {str(e)}",
                                "strengths": [],
                                "weaknesses": [],
                                "recommendations": []
                            })
                    
                    else:
                        logger.warning(f"No se encontraron resultados en la búsqueda semántica para criterio '{criterion_title}'. Usando texto completo de la propuesta.")
                except Exception as e:
                    logger.error(f"Error en búsqueda semántica para criterio '{criterion_title}': {str(e)}. Usando texto completo de la propuesta.")
            
        
        # Esperar a que terminen las evaluaciones técnicas y gramaticales
        try:
            #technical_evaluation = self._perform_technical_evaluation(proposal_text, user_id)
            technical_evaluation = {
                "score": 0,
                        "assessment": f"Error en evaluación técnica: {str(e)}",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
            
        except Exception as e:
            logger.error(f"Error en evaluación técnica para pipeline {pipeline_id}: {e}")
            technical_evaluation = {
                "score": 0,
                "assessment": f"Error en evaluación técnica: {str(e)}",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
        
        try:
            #consistency_evaluation = self._perform_consistency_evaluation(proposal_text, user_id)
            consistency_evaluation = {
                "score": 0,
                "assessment": f"Error en evaluación de consistencia: {str(e)}",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Error en evaluación de consistencia para pipeline {pipeline_id}: {e}")
            consistency_evaluation = {
                "score": 0,
                "assessment": f"Error en evaluación de consistencia: {str(e)}",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
        try:
            #grammar_evaluation = self._perform_grammar_evaluation(proposal_text, user_id)
            grammar_evaluation = {
                "score": 0,
                "assessment": "Error en evaluación gramatical: No se pudo realizar la evaluación gramatical",
                "issues": [],
                "strengths": [],
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Error en evaluación gramatical para pipeline {pipeline_id}: {e}")
            grammar_evaluation = {
                "score": 0,
                "assessment": f"Error en evaluación gramatical: {str(e)}",
                "issues": [],
                "strengths": [],
                "recommendations": []
            }
        
        # Generar reporte final
        #final_report = self._generate_final_report(criteria_evaluations)
        final_report = {
            "score": 0,
            "assessment": "Error en generación de reporte final: No se pudo generar el reporte final",
            "generated_at": datetime.utcnow().isoformat()
        }
        # Compilar resultados
        results = {
            "criteria_evaluations": criteria_evaluations,
            "technical_evaluation": technical_evaluation,
            "consistency_evaluation": consistency_evaluation,
            "grammar_evaluation": grammar_evaluation,
            "final_report": final_report,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Análisis asíncrono de propuesta completado para pipeline {pipeline_id}")
        return results
        
    def _evaluate_criterion(
        self, 
        chunk: str, 
        criterion: Dict[str, Any],
        weight: int,
        scoring_scale: List[Dict[str, Any]],
        pipeline_id: uuid.UUID,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluar un criterio específico contra el contenido de la propuesta usando búsqueda semántica
        
        Args:
            proposal_text: Texto de la propuesta
            criterion: Criterio a evaluar
            weight: Peso del criterio
            scoring_scale: Escala de puntuación
            pipeline_id: ID del pipeline
            db: Sesión de base de datos
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados de la evaluación
        """
        criterion_title = criterion.get("title", "Sin título")
        criterion_description = criterion.get("description", "Sin descripción")
        criterion_requirements = criterion.get("requirements", [])
        
        # Preparar el prompt para la evaluación
        system_prompt = CRITERION_EVALUATOR_SYSTEM_PROMPT
        
        # Convertir scoring_scale a formato de texto para el prompt
        scoring_scale_text = "\n".join([f"{score.get('score', '')}: {score.get('description', '')}" for score in scoring_scale]) if scoring_scale else ""
        
        user_prompt = get_criterion_evaluation_prompt(
            criterion_title=criterion_title,
            criterion_description=criterion_description,
            criterion_requirements=criterion_requirements,
            scoring_scale=scoring_scale_text,
            chunk=chunk
        )
        
        logger.info(f"Evaluando criterio '{criterion_title}' para pipeline {pipeline_id}")
        
        try:
            # Llamar al LLM para evaluar el criterio
            response = self.llm_client.generate_chat_completion_sync(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                user_id=user_id
            )
            
            # Extraer y validar la respuesta
            result_text = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            result = json.loads(result_text)
            
            # Validar que la respuesta tenga la estructura esperada
            if not isinstance(result, dict) or "score" not in result:
                raise ValueError(f"Respuesta inválida del LLM para criterio {criterion_title}")
            
            # Asegurarse de que la puntuación esté en el rango correcto
            score = int(result.get("score", 0))
            if score < 1 or score > 5:
                score = max(1, min(5, score))  # Limitar a rango 1-5
                
            # Construir resultado final
            evaluation_result = {
                "criterion": criterion_title,
                "description": criterion_description,
                "score": score,
                "weight": weight,
                "justification": result.get("justification", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "recommendations": result.get("recommendations", [])
            }
            
            logger.info(f"Criterio '{criterion_title}' evaluado con puntuación {score}/5 para pipeline {pipeline_id}")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Error al evaluar criterio '{criterion_title}' para pipeline {pipeline_id}: {e}")
            return {
                "criterion": criterion_title,
                "description": criterion_description,
                "score": 0,
                "weight": weight,
                "justification": f"Error en la evaluación: {str(e)}",
                "strengths": [],
                "weaknesses": ["No se pudo evaluar este criterio debido a un error."],
                "recommendations": ["Revisar manualmente este criterio."]
            }
        
    def _perform_technical_evaluation(self, proposal_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Realizar evaluación técnica de la propuesta
        
        Args:
            proposal_text: Texto de la propuesta
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados de la evaluación técnica
        """
        system_prompt = TECHNICAL_EVALUATION_SYSTEM_PROMPT
        user_prompt = get_technical_evaluation_prompt(proposal_text)
        
        try:
            # Llamar al LLM para evaluación técnica
            response = self.llm_client.generate_chat_completion_sync(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                user_id=user_id
            )
            
            # Extraer y validar la respuesta
            result_text = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            result = json.loads(result_text)
            
            # Validar que la respuesta tenga la estructura esperada
            if not isinstance(result, dict) or "score" not in result:
                raise ValueError("Respuesta inválida del LLM para evaluación técnica")
            
            # Asegurarse de que la puntuación esté en el rango correcto
            score = int(result.get("score", 0))
            if score < 1 or score > 5:
                score = max(1, min(5, score))  # Limitar a rango 1-5
                
            return {
                "score": score,
                "assessment": result.get("assessment", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "recommendations": result.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Error en evaluación técnica: {e}")
            return {
                "score": 0,
                "assessment": f"Error en la evaluación técnica: {str(e)}",
                "strengths": [],
                "weaknesses": ["No se pudo realizar la evaluación técnica debido a un error."],
                "recommendations": ["Revisar manualmente los aspectos técnicos de la propuesta."]
            }
    
    def _perform_grammar_evaluation(self, proposal_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Realizar evaluación gramatical y de calidad de escritura de la propuesta
        
        Args:
            proposal_text: Texto de la propuesta
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados de la evaluación gramatical
        """
        system_prompt = GRAMMAR_EVALUATION_SYSTEM_PROMPT
        user_prompt = get_grammar_evaluation_prompt(proposal_text)
        
        try:
            # Llamar al LLM para evaluación gramatical
            response = self.llm_client.generate_chat_completion_sync(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                user_id=user_id
            )
            
            # Extraer y validar la respuesta
            result_text = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            result = json.loads(result_text)
            
            # Validar que la respuesta tenga la estructura esperada
            if not isinstance(result, dict) or "score" not in result:
                raise ValueError("Respuesta inválida del LLM para evaluación gramatical")
            
            # Asegurarse de que la puntuación esté en el rango correcto
            score = int(result.get("score", 0))
            if score < 1 or score > 5:
                score = max(1, min(5, score))  # Limitar a rango 1-5
                
            return {
                "score": score,
                "assessment": result.get("assessment", ""),
                "issues": result.get("issues", []),
                "strengths": result.get("strengths", []),
                "recommendations": result.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Error en evaluación gramatical: {e}")
            return {
                "score": 0,
                "assessment": f"Error en la evaluación gramatical: {str(e)}",
                "issues": [],
                "strengths": [],
                "recommendations": ["Revisar manualmente la gramática y calidad de escritura de la propuesta."]
            }
    
    def _perform_consistency_evaluation(self, proposal_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Realizar evaluación de consistencia de la propuesta
        
        Args:
            proposal_text: Texto de la propuesta
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados de la evaluación de consistencia
        """
        try:
            # Preparar mensajes para la evaluación
            messages = [
                ("system", CONSISTENCY_EVALUATION_SYSTEM_PROMPT),
                ("user", get_consistency_evaluation_prompt(proposal_text))
            ]
            
            response = self.llm_client.generate_chat_completion_sync(
                messages=[{"role": msg[0], "content": msg[1]} for msg in messages],
                model=self.default_model,
                temperature=0.3,
                user_id=user_id
            )
            
            if isinstance(response, str):
                evaluation = json.loads(response)
            else:
                evaluation = json.loads(response.get("choices", [{}])[0].get("message", {}).get("content", "{}"))
                
            return evaluation
            
        except Exception as e:
            logger.error(f"Error en evaluación de consistencia: {str(e)}")
            return {
                "consistency_score": 5.0,
                "contradictions": ["No se pudo realizar la evaluación de consistencia"],
                "misalignments": ["Desconocido debido a un error"],
                "conflicting_promises": ["Desconocido debido a un error"],
                "recommendations": ["Se recomienda revisar manualmente"],
                "error": str(e)
            }
    
    def _generate_final_report(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generar reporte final a partir de todas las evaluaciones de criterios
            
        Args:
            evaluations: Lista de evaluaciones de criterios
                
        Returns:
            Dict[str, Any]: Reporte final
        """
        try:
            # Primero, calcular weighted_score para cada evaluación
            for eval in evaluations:
                # Manejar el peso tanto si viene como string con '%' o como número
                weight = eval["weight"]
                if isinstance(weight, str):
                    weight_percentage = float(weight.strip("%")) / 100
                else:
                    weight_percentage = float(weight) / 100
                    
                eval["weighted_score"] = eval["score"] * weight_percentage
                eval["max_possible"] = 5 * weight_percentage  # 5 es la puntuación máxima posible

            # Luego calcular totales
            total_weighted_score = sum(eval["weighted_score"] for eval in evaluations)
            total_max_possible = sum(eval["max_possible"] for eval in evaluations)
            overall_score = int((total_weighted_score / total_max_possible) * 100) if total_max_possible > 0 else 0

            # Crear scoring breakdown
            scoring_breakdown = [
                {
                    "criterion": eval["criterion"],
                    "weight": (
                        f"{eval['weight']}%"
                        if isinstance(eval["weight"], (int, float))
                        else eval["weight"]
                    ),
                    "score": eval["score"],
                    "weighted_score": round(eval["weighted_score"], 2),
                    "max_possible": round(eval["max_possible"], 2),
                }
                for eval in evaluations
            ]

            def get_overall_assessment(score: int) -> str:
                if score >= 90:
                    return "Excellent proposal, strongly recommended"
                if score >= 80:
                    return "Very good proposal, recommended"
                if score >= 70:
                    return "Good proposal, some improvements needed"
                if score >= 60:
                    return "Moderate proposal, significant improvements needed"
                return "Weak proposal, major improvements required"

            def generate_summary(evaluations: List[Dict], overall_score: int) -> str:
                strengths = [
                    strength
                    for eval in evaluations
                    if eval["score"] >= 4
                    for strength in eval["strengths"][:2]
                ]

                weaknesses = [
                    weakness
                    for eval in evaluations
                    if eval["score"] <= 2
                    for weakness in eval["weaknesses"][:2]
                ]

                summary = (
                    f"Overall Score: {overall_score}/100. "
                    f"Total Weighted Score: {total_weighted_score:.2f} out of {total_max_possible:.2f}. "
                )

                if strengths:
                    summary += "Key Strengths: " + "; ".join(strengths) + ". "

                if weaknesses:
                    summary += (
                        "Critical Areas for Improvement: "
                        + "; ".join(weaknesses)
                        + ". "
                    )

                summary += get_overall_assessment(overall_score)

                return summary

            return {
                "overall_score": overall_score,
                "overall_assessment": get_overall_assessment(overall_score),
                "total_weighted_score": round(total_weighted_score, 2),
                "total_max_possible": round(total_max_possible, 2),
                "scoring_breakdown": scoring_breakdown,
                "summary": generate_summary(evaluations, overall_score),
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            return {
                "error": f"Error generating final report: {str(e)}",
                "overall_score": 0,
                "overall_assessment": "Could not generate assessment due to an error",
                "generated_at": datetime.utcnow().isoformat(),
            }
    