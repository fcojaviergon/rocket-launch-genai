"""
Proposal document processor pipeline
"""
from typing import Dict, Any, List, Optional, Tuple
import uuid
import json
from datetime import datetime
import logging
from sqlalchemy import select

from database.models.document import Document
from database.models.analysis import RfpAnalysisPipeline
from modules.pipelines.base import BasePipeline
from core.llm_interface import LLMClientInterface

logger = logging.getLogger(__name__)

class ProposalPipeline(BasePipeline):
    """Pipeline for proposal documents"""
    
    def __init__(self, llm_client: LLMClientInterface):
        self.llm_client = llm_client
        self.sync_client = True
        self.default_model = "gpt-4o"
        
    async def process(
        self, 
        pipeline_id: uuid.UUID, 
        document: Document,
        rfp_pipeline: RfpAnalysisPipeline,
        text_content: str = None,
        embeddings: List[Dict[str, Any]] = None,
        db=None
    ) -> Dict[str, Any]:
        """
        Process a proposal document against an RFP, evaluando contra criterios de RFP
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            rfp_pipeline: RFP pipeline with evaluation criteria
            text_content: Contenido de texto del documento (opcional, si no se proporciona se extraerá del documento)
            embeddings: Embeddings generados previamente (opcional)
            db: Database session (opcional, solo necesario si se quieren guardar resultados)
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Initialize context
        context = {
            "pipeline_id": pipeline_id,
            "document_id": document.id,
            "document_title": document.title,
            "rfp_pipeline_id": rfp_pipeline.id,
            "evaluation_results": {},
            "technical_evaluation": {},
            "grammar_evaluation": {},
            "consistency_evaluation": {}
        }
        
        # Get document content if not provided
        if text_content is None:
            text_content = await self._get_document_content(document)
        
        context["text_content"] = text_content
        context["document_content"] = text_content  # Para mantener compatibilidad con el código existente
        
        # Use provided embeddings if available
        if embeddings:
            context["embeddings"] = embeddings
        
        # Get RFP evaluation criteria
        context["evaluation_framework"] = rfp_pipeline.evaluation_framework or {}
        context["extracted_criteria"] = rfp_pipeline.extracted_criteria or {}
        
        # Evaluate against criteria
        await self._evaluate_against_criteria(context)
        
        # Evaluate technical aspects
        await self._perform_technical_evaluation(context)
        
        # Evaluate grammar and style
        await self._perform_grammar_evaluation(context)
        
        # Evaluate consistency
        await self._perform_consistency_evaluation(context)
        
        # Generate final report
        await self._generate_final_report(context)
        
        # Clean up and return results
        return self._cleanup_and_return(context)
    
    def process_sync(
        self, 
        pipeline_id: uuid.UUID, 
        document: Document,
        rfp_pipeline: RfpAnalysisPipeline,
        text_content: str = None,
        embeddings: List[Dict[str, Any]] = None,
        db=None
    ) -> Dict[str, Any]:
        """
        Synchronous version of process for use in Celery tasks
        
        Args:
            pipeline_id: Analysis Pipeline ID
            document: Document to process
            rfp_pipeline: RFP pipeline with evaluation criteria
            text_content: Contenido de texto del documento (opcional, si no se proporciona se extraerá del documento)
            embeddings: Embeddings generados previamente (opcional)
            db: Database session (opcional, solo necesario si se quieren guardar resultados)
            
        Returns:
            Dict[str, Any]: Processing results
        """
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.process(pipeline_id, document, rfp_pipeline, text_content, embeddings, db))
        finally:
            loop.close()
    
    async def _get_document_content(self, document: Document) -> str:
        """
        Get document content by reading the file from disk
        
        Args:
            document: Document
            
        Returns:
            str: Document content
        """
        # Check if we have a file path
        if document.file_path:
            try:
                # En un entorno real, aquí leeríamos el archivo y extraeríamos el texto
                # dependiendo del tipo de archivo (PDF, DOCX, etc.)
                import os
                
                # Verificar que el archivo existe
                if os.path.exists(document.file_path):
                    # Simular la extracción de texto del archivo
                    # En un entorno real, usaríamos bibliotecas como PyPDF2, python-docx, etc.
                    logger.info(f"Leyendo archivo {document.file_path}")
                    
                    # Simulación de extracción de texto basada en el tipo de archivo
                    if document.file_path.lower().endswith('.pdf'):
                        # Simular extracción de PDF
                        return f"[Contenido extraído del PDF: {document.title}] ."
                    elif document.file_path.lower().endswith(('.docx', '.doc')):
                        # Simular extracción de Word
                        return f"[Contenido extraído del DOCX: {document.title}] ."
                    else:
                        # Para otros tipos de archivo, intentar leer como texto plano
                        try:
                            with open(document.file_path, 'r', encoding='utf-8') as f:
                                return f.read()
                        except Exception as e:
                            logger.error(f"Error leyendo archivo {document.file_path}: {e}")
                            return f"Error al leer el archivo {document.title}. Contenido simulado para demostración de propuesta."
                else:
                    logger.warning(f"Archivo no encontrado: {document.file_path}")
                    return f"Archivo no encontrado: {document.title}. Contenido simulado para demostración de propuesta."
                    
            except Exception as e:
                logger.error(f"Error procesando archivo {document.file_path}: {e}")
                return f"Error procesando archivo {document.title}. Contenido simulado para demostración de propuesta."
        
        # Si no hay archivo o hubo un error, devolver un mensaje de error
        logger.warning(f"No se encontró archivo para el documento {document.id}")
        return f"No se encontró contenido para el documento {document.title}. Contenido simulado para demostración de propuesta."
    
    async def _evaluate_against_criteria(self, context: Dict[str, Any]) -> None:
        """
        Evaluate proposal against RFP criteria
        
        Args:
            context: Analysis context
        """
        document_content = context.get("document_content", "")
        evaluation_framework = context.get("evaluation_framework", {})
        
        # Skip if no content or criteria
        if not document_content or not evaluation_framework:
            logger.warning("No document content or evaluation framework available")
            context["evaluation_results"] = {
                "error": "No document content or evaluation framework available",
                "evaluated_at": datetime.utcnow().isoformat()
            }
            return
        
        # Get weighted criteria
        weighted_criteria = evaluation_framework.get("weighted_criteria", [])
        if not weighted_criteria:
            logger.warning("No weighted criteria available in evaluation framework")
            context["evaluation_results"] = {
                "error": "No weighted criteria available in evaluation framework",
                "evaluated_at": datetime.utcnow().isoformat()
            }
            return
        
        # Evaluate each criterion
        evaluation_results = {
            "criteria_evaluations": [],
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        for criterion_item in weighted_criteria:
            # Get criterion details
            criterion_title = criterion_item.get("criterion", "")
            criterion_weight = criterion_item.get("weight", "0%")
            
            # Convert weight to numeric value
            if isinstance(criterion_weight, str) and criterion_weight.endswith("%"):
                try:
                    weight_value = float(criterion_weight.rstrip("%")) / 100
                except ValueError:
                    weight_value = 0
            else:
                weight_value = float(criterion_weight) if isinstance(criterion_weight, (int, float)) else 0
            
            # Get criterion details from extracted criteria
            extracted_criteria = context.get("extracted_criteria", {})
            criterion = extracted_criteria.get(criterion_title, {})
            
            # If no details, create minimal criterion
            if not criterion:
                criterion = {
                    "title": criterion_title,
                    "description": f"Evaluation of {criterion_title}",
                    "key_indicators": [],
                    "evidence_of_strong_response": []
                }
            
            # Prepare search texts
            search_texts = [criterion.get("title", "")]
            if criterion.get("key_indicators"):
                search_texts.extend(criterion.get("key_indicators", []))
            if criterion.get("evidence_of_strong_response"):
                search_texts.extend(criterion.get("evidence_of_strong_response", []))
            
            # Filter out empty texts
            search_texts = [text for text in search_texts if text]
            
            # If no search texts, use criterion title
            if not search_texts:
                search_texts = [criterion_title]
            
            # Buscar textos relevantes usando búsqueda semántica
            relevant_content = await self._similarity_search(document_content, search_texts, context)
            
            # Evaluar el contenido relevante contra el criterio
            evaluation = await self._evaluate_criterion(criterion, relevant_content)
            
            # Add weight information
            evaluation["criterion"] = criterion_title
            evaluation["weight"] = criterion_weight
            evaluation["weight_value"] = weight_value
            
            # Calculate weighted score
            if "score" in evaluation:
                max_score = 5  # Assuming 1-5 scale
                evaluation["weighted_score"] = evaluation["score"] * weight_value
                evaluation["max_possible"] = max_score * weight_value
            
            # Add to results
            evaluation_results["criteria_evaluations"].append(evaluation)
        
        # Guardar los resultados en el contexto
        context["evaluation_results"] = evaluation_results
        
    async def _similarity_search(self, content: str, search_texts: List[str], context: Dict[str, Any]) -> str:
        """
        Realiza una búsqueda semántica en el contenido del documento usando embeddings
        
        Args:
            content: Contenido del documento
            search_texts: Textos de búsqueda
            context: Contexto del procesamiento
            
        Returns:
            str: Contenido relevante
        """
        try:
            # Si no hay textos de búsqueda, devolver una parte del contenido
            if not search_texts:
                max_length = min(len(content), 2000)
                return content[:max_length]
                
            # Usar el pipeline_id para buscar en los embeddings correspondientes
            pipeline_id = context.get("pipeline_id")
            if not pipeline_id:
                logger.warning("No pipeline_id available for similarity search")
                max_length = min(len(content), 2000)
                return content[:max_length]
                
            # Combinar los textos de búsqueda en una sola consulta
            query = " ".join(search_texts[:3])  # Limitar a los 3 primeros para evitar consultas muy largas
            
            # En un entorno real, aquí usaríamos el servicio de documentos para buscar
            # en los embeddings asociados al pipeline
            from modules.document.service import DocumentService
            document_service = DocumentService()
            
            # Importar AsyncSession para crear una sesión de base de datos
            from sqlalchemy.ext.asyncio import AsyncSession
            from core.db import get_async_db
            
            # Crear una sesión de base de datos
            async for db in get_async_db():
                # Generar embedding para la consulta
                query_embedding = await document_service.generate_query_embedding(query)
                
                # Obtener el scenario_id del pipeline actual
                from database.models.analysis import AnalysisPipeline
                pipeline_query = select(AnalysisPipeline).where(AnalysisPipeline.id == pipeline_id)
                pipeline_result = await db.execute(pipeline_query)
                pipeline = pipeline_result.scalar_one_or_none()
                
                scenario_id = None
                if pipeline:
                    scenario_id = pipeline.scenario_id
                    logger.info(f"Searching embeddings for scenario: {scenario_id}")
                
                # Buscar en los embeddings asociados al pipeline
                results = await document_service.search_similar_documents(
                    db=db,
                    query_embedding=query_embedding,
                    user_id=None,  # No filtrar por usuario
                    limit=5,  # Limitar a 5 resultados
                    min_similarity=0.5,  # Umbral de similitud
                    model="default",  # Modelo por defecto
                    analysis_id=scenario_id  # Filtrar por escenario
                )
                
                # Si hay resultados, devolver el contenido relevante
                if results:
                    # Combinar los fragmentos de texto encontrados
                    relevant_texts = [result["chunk_text"] for result in results]
                    return "\n\n".join(relevant_texts)
                    
                break  # Salir del bucle después de la primera iteración
                
            # Si no hay resultados, devolver una parte del contenido
            max_length = min(len(content), 2000)
            return content[:max_length]
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            # En caso de error, devolver una parte del contenido
            max_length = min(len(content), 2000)
            return content[:max_length]
    
    async def _evaluate_criterion(self, criterion: Dict[str, Any], content: str) -> Dict[str, Any]:
        """
        Evalúa un criterio específico contra el contenido relevante
        
        Args:
            criterion: Criterio de evaluación
            content: Contenido relevante
            
        Returns:
            Dict[str, Any]: Resultado de la evaluación
        """
        # Prompt para evaluar el criterio
        EVALUATE_CRITERION_PROMPT = """
        Evaluate the following proposal content against this specific criterion:
        
        Criterion: {criterion_title}
        Description: {criterion_description}
        Key Indicators:
        {key_indicators}
        
        Evidence of a Strong Response:
        {evidence}
        
        Proposal Content:
        {content}
        """
        
    async def _perform_technical_evaluation(self, context: Dict[str, Any]) -> None:
        """
        Perform technical evaluation of proposal
        
        Args:
            context: Analysis context
        """
        # Get document content
        document_content = context.get("document_content", "")
        
        # Skip if no content
        if not document_content:
            logger.warning("No document content available for technical evaluation")
            context["technical_evaluation"] = {
                "error": "No document content available",
                "evaluated_at": datetime.utcnow().isoformat()
            }
            return
        
        # Prepare technical evaluation
        technical_evaluation = {
            "technical_score": 0,
            "key_findings": [],
            "technical_risks": [],
            "implementation_concerns": [],
            "technical_strengths": [],
            "recommendations": [],
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        # In a real environment, here we would call the OpenAI API
        # For now, we use example data
        if self.llm_client:
            try:
                # Prepare prompt
                formatted_prompt = TECHNICAL_EVALUATION_PROMPT.format(
                    content=document_content[:10000]  # Limit content length
                )
                
                # Call API
                response = await self.llm_client.create_completion(formatted_prompt)
                technical_evaluation.update(json.loads(response))
            except Exception as e:
                logger.error(f"Error performing technical evaluation: {e}")
                # En caso de error, mantener la evaluación por defecto
        else:
            # Si no hay cliente LLM, usar la evaluación por defecto
            logger.warning("No LLM client available for technical evaluation")
            
        context["technical_evaluation"] = technical_evaluation
    
    
    async def _perform_consistency_evaluation(self, context: Dict[str, Any]) -> None:
        """
        Perform consistency evaluation
        
        Args:
            context: Analysis context
        """
        # Get document content
        document_content = context.get("document_content", "")
        
        # Skip if no content
        if not document_content:
            logger.warning("No document content available for consistency evaluation")
            context["consistency_evaluation"] = {
                "error": "No document content available",
                "evaluated_at": datetime.utcnow().isoformat()
            }
            return
        
        # Prepare consistency evaluation
        consistency_evaluation = {
            "consistency_score": 0,
            "contradictions": [],
            "misalignments": [],
            "conflicting_promises": [],
            "recommendations": [],
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        # In a real environment, here we would call the OpenAI API
        if self.llm_client:
            try:
                # Prepare prompt
                formatted_prompt = CONSISTENCY_EVALUATION_PROMPT.format(
                    content=document_content[:10000]  # Limit content length
                )
                
                # Call API
                response = await self.llm_client.create_completion(formatted_prompt)
                consistency_evaluation.update(json.loads(response))
            except Exception as e:
                logger.error(f"Error performing consistency evaluation: {e}")
                # En caso de error, mantener la evaluación por defecto
        else:
            # Si no hay cliente LLM, usar la evaluación por defecto
            logger.warning("No LLM client available for consistency evaluation")
            
        context["consistency_evaluation"] = consistency_evaluation
    
    
    async def _perform_grammar_evaluation(self, context: Dict[str, Any]) -> None:
        """
        Perform grammar and writing quality evaluation
        
        Args:
            context: Analysis context
        """
        # Get document content
        document_content = context.get("document_content", "")
        
        # Skip if no content
        if not document_content:
            logger.warning("No document content available for grammar evaluation")
            context["grammar_evaluation"] = {
                "error": "No document content available",
                "evaluated_at": datetime.utcnow().isoformat()
            }
            return
        
        # Prepare grammar evaluation
        grammar_evaluation = {
            "writing_quality_score": 0,
            "grammar_issues": [],
            "style_issues": [],
            "clarity_concerns": [],
            "improvement_suggestions": [],
            "evaluated_at": datetime.utcnow().isoformat()
        }
        
        # In a real environment, here we would call the OpenAI API
        if self.llm_client:
            try:
                # Prepare prompt
                formatted_prompt = GRAMMAR_EVALUATION_PROMPT.format(
                    content=document_content[:10000]  # Limit content length
                )
                
                # Call API
                response = await self.llm_client.create_completion(formatted_prompt)
                grammar_evaluation.update(json.loads(response))
            except Exception as e:
                logger.error(f"Error performing grammar evaluation: {e}")
                # En caso de error, mantener la evaluación por defecto
        else:
            # Si no hay cliente LLM, usar la evaluación por defecto
            logger.warning("No LLM client available for grammar evaluation")
            
        context["grammar_evaluation"] = grammar_evaluation
    
    async def _generate_final_report(self, context: Dict[str, Any]) -> None:
        """
        Generate final report from evaluation results
        
        Args:
            context: Analysis context
        """
        evaluations = context.get("evaluation_results", [])
        
        if not evaluations:
            logger.warning("No evaluation results found for final report")
            context["final_report"] = {}
            return
        
        try:
            # Calcular weighted_score para cada evaluación
            for eval in evaluations:
                # Manejar el peso tanto si viene como string con '%' o como número
                weight = eval["weight"]
                if isinstance(weight, str):
                    weight_percentage = float(weight.strip("%")) / 100
                else:
                    weight_percentage = float(weight) / 100

                eval["weighted_score"] = eval["score"] * weight_percentage
                eval["max_possible"] = 5 * weight_percentage  # 5 es la puntuación máxima posible

            # Calcular totales
            total_weighted_score = sum(eval["weighted_score"] for eval in evaluations)
            total_max_possible = sum(eval["max_possible"] for eval in evaluations)
            overall_score = int((total_weighted_score / total_max_possible) * 100)

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

            # Generar evaluación general
            overall_assessment = self._get_overall_assessment(overall_score)

            # Generar resumen
            summary = self._generate_summary(evaluations, overall_score, total_weighted_score, total_max_possible)

            # Crear informe final
            final_report = {
                "overall_score": overall_score,
                "overall_assessment": overall_assessment,
                "total_weighted_score": round(total_weighted_score, 2),
                "total_max_possible": round(total_max_possible, 2),
                "scoring_breakdown": scoring_breakdown,
                "summary": summary,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            context["final_report"] = final_report
            
        except Exception as e:
            logger.error(f"Error generating final report: {str(e)}")
            context["final_report"] = {
                "error": f"Error generating final report: {str(e)}",
                "generated_at": datetime.utcnow().isoformat()
            }
    
    def _get_overall_assessment(self, score: int) -> str:
        """
        Get overall assessment based on score
        
        Args:
            score: Overall score
            
        Returns:
            str: Overall assessment
        """
        if score >= 90:
            return "Excellent proposal, strongly recommended"
        if score >= 80:
            return "Very good proposal, recommended"
        if score >= 70:
            return "Good proposal, some improvements needed"
        if score >= 60:
            return "Moderate proposal, significant improvements needed"
        return "Weak proposal, major improvements required"
    
    def _generate_summary(self, evaluations: List[Dict], overall_score: int, 
                         total_weighted_score: float, total_max_possible: float) -> str:
        """
        Generate summary from evaluations
        
        Args:
            evaluations: List of evaluation results
            overall_score: Overall score
            total_weighted_score: Total weighted score
            total_max_possible: Total maximum possible score
            
        Returns:
            str: Summary
        """
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

        summary += self._get_overall_assessment(overall_score)

        return summary
    
    def _cleanup_and_return(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up context and return results
        
        Args:
            context: Processing context
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Return only the necessary data
        from datetime import datetime
        
        return {
            "pipeline_id": context.get("pipeline_id"),
            "document_id": context.get("document_id"),
            "document_title": context.get("document_title"),
            "rfp_pipeline_id": context.get("rfp_pipeline_id"),
            "evaluation_results": context.get("evaluation_results", {}),
            "technical_evaluation": context.get("technical_evaluation", {}),
            "grammar_evaluation": context.get("grammar_evaluation", {}),
            "consistency_evaluation": context.get("consistency_evaluation", {}),
            "final_report": context.get("final_report", {}),
            "processed_at": datetime.utcnow().isoformat()
        }
    
