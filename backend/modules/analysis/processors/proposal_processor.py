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
        rfp_analysis: Dict[str, Any],
        pipeline_id: uuid.UUID,
        db: Session,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analizar el contenido de una propuesta con respecto a un análisis de RFP
        
        Args:
            proposal_text: Texto de la propuesta
            rfp_analysis: Análisis previo del RFP
            pipeline_id: ID del pipeline de análisis
            db: Sesión de base de datos
            user_id: ID del usuario para registro de tokens
            
        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        logger.info(f"Iniciando análisis de propuesta para pipeline {pipeline_id}")
        
        # Extraer criterios y framework de evaluación del análisis de RFP
        criteria = rfp_analysis.get("criteria", {}).get("criteria", [])
        framework = rfp_analysis.get("framework", {})
        weighted_criteria = framework.get("weighted_criteria", [])
        scoring_scale = framework.get("scoring_scale", [])
        
        if not criteria or not weighted_criteria:
            logger.error(f"No se encontraron criterios o pesos en el análisis de RFP para pipeline {pipeline_id}")
            return {
                "error": "No se encontraron criterios o pesos en el análisis de RFP",
                "analyzed_at": datetime.utcnow().isoformat()
            }
        
        # Crear mapa de criterios por título para fácil acceso
        criteria_map = {criterion.get("title"): criterion for criterion in criteria}
        weight_map = {criterion.get("title"): criterion.get("weight") for criterion in weighted_criteria}
        
        # Evaluar propuesta contra cada criterio
        logger.info(f"Evaluando {len(weighted_criteria)} criterios para pipeline {pipeline_id}")
        criteria_evaluations = []
        
        # Evaluar criterios
        for criterion_with_weight in weighted_criteria:
            criterion_title = criterion_with_weight.get("title")
            criterion = criteria_map.get(criterion_title)
            weight = criterion_with_weight.get("weight")
            
            if not criterion:
                logger.warning(f"No se encontró información para el criterio {criterion_title} en pipeline {pipeline_id}")
                continue
                
            try:
                # Realizar búsqueda semántica y evaluación del criterio
                evaluation = self._evaluate_criterion(
                    proposal_text=proposal_text,
                    criterion=criterion,
                    weight=weight,
                    scoring_scale=scoring_scale,
                    pipeline_id=pipeline_id,
                    db=db,
                    user_id=user_id
                )
                
                criteria_evaluations.append(evaluation)
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
        
        # Esperar a que terminen las evaluaciones técnicas y gramaticales
        try:
            technical_evaluation = self._perform_technical_evaluation(proposal_text, user_id)
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
            grammar_evaluation = self._perform_grammar_evaluation(proposal_text, user_id)
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
        final_report = self._generate_final_report(criteria_evaluations)
        
        # Compilar resultados
        results = {
            "criteria_evaluations": criteria_evaluations,
            "technical_evaluation": technical_evaluation,
            "grammar_evaluation": grammar_evaluation,
            "final_report": final_report,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Análisis asíncrono de propuesta completado para pipeline {pipeline_id}")
        return results
        
    def _evaluate_criterion(
        self, 
        proposal_text: str, 
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
        user_prompt = get_criterion_evaluation_prompt(
            criterion_title=criterion_title,
            criterion_description=criterion_description,
            criterion_requirements=criterion_requirements,
            scoring_scale=scoring_scale,
            proposal_text=proposal_text
        )
        
        logger.info(f"Evaluando criterio '{criterion_title}' para pipeline {pipeline_id}")
        
        try:
            # Llamar al LLM para evaluar el criterio
            response = self.llm_client.chat_completion(
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
            response = self.llm_client.chat_completion(
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
            response = self.llm_client.chat_completion(
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
            
            response = self.llm_client.generate_chat_completion(
                messages=[{"role": msg[0], "content": msg[1]} for msg in messages],
                model=self.default_model,
                temperature=0.3,
                user_id=user_id
            )
            
            if isinstance(response, str):
                evaluation = json.loads(response)
            else:
                evaluation = json.loads(response.choices[0].message.content)
                
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
                eval["max_possible"] = (
                    5 * weight_percentage
                )  # 5 es la puntuación máxima posible

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