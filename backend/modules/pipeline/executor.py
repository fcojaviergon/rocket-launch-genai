"""
Ejecutor de pipelines de documentos
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from database.models.pipeline import Pipeline, PipelineExecution, ExecutionStatus
from database.models.document import Document, DocumentProcessingResult
from modules.pipeline.processors import get_processor, AVAILABLE_PROCESSORS

logger = logging.getLogger(__name__)

class PipelineExecutor:
    """Class to execute document processing pipelines"""
    
    def __init__(self):
        self.context = {}
    
    async def execute(self, execution_id: UUID, pipeline: Pipeline, document: Document) -> Dict[str, Any]:
        """
        Execute a pipeline on a document
        
        Args:
            execution_id: ID of the execution
            pipeline: Pipeline configuration
            document: Document to process
            
        Returns:
            Dict[str, Any]: Processing results
        """
        logger.info(f"Executing pipeline '{pipeline.name}' on document '{document.title}'")
        logger.debug(f"Document content: {document.content[:100]}..." if document.content else "No content")
        
        # Initialize context
        self.context = {
            "execution_id": str(execution_id),
            "pipeline_id": str(pipeline.id),
            "pipeline_name": pipeline.name,
            "document_id": str(document.id),
            "document_title": document.title,
            "results": {},
            "errors": [],
            "_connections": []  # Track connections to ensure cleanup
        }
        
        # Get the steps of the pipeline
        steps = pipeline.steps or []
        
        if not steps:
            error_msg = f"The pipeline '{pipeline.name}' has no steps configured"
            logger.error(error_msg)
            self.context["errors"].append(error_msg)
            return self._cleanup_and_return(self.context)
        
        try:
            # Execute each step in order
            for step in steps:
                # Always use a fresh step context to avoid carrying connection objects
                step_context = {k: v for k, v in self.context.items() 
                               if not k.startswith('_') and not callable(v)}
                
                step_result = await self._execute_step(step, document.content, step_context)
                
                # If there is an error in the step, register it and continue with the next one
                if "error" in step_result:
                    error_msg = f"Error in step '{step.get('name', 'unknown')}': {step_result['error']}"
                    logger.error(error_msg)
                    self.context["errors"].append(error_msg)
                
                # Save results in the context
                step_name = step.get("name", step.get("id", "unknown_step"))
                self.context["results"][step_name] = step_result
                
                # Update the context with values from the current step so they are available for the next steps
                for key, value in step_result.items():
                    if key not in ("error", "processor", "timestamp"):
                        self.context[key] = value
            
            # Generate results summary
            summary = self._generate_results_summary()
            self.context["summary"] = summary
            
            return self._cleanup_and_return(self.context)
            
        except Exception as e:
            error_msg = f"Error executing pipeline: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.context["errors"].append(error_msg)
            return self._cleanup_and_return(self.context)
            
    def _cleanup_and_return(self, context):
        """Clean up any resources and return the context"""
        # Make a clean copy without internal properties to return
        result_context = {k: v for k, v in context.items() 
                         if not k.startswith('_') and not callable(v)}
        return result_context
    
    async def _execute_step(self, step: Dict[str, Any], document_content: str, step_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a step of the pipeline
        
        Args:
            step: Step configuration
            document_content: Document content
            step_context: Context specific for this step (optional)
            
        Returns:
            Dict[str, Any]: Step results
        """
        context = step_context or self.context
        
        try:
            step_type = step.get("type", "processor")
            step_name = step.get("name", step.get("id", "unknown"))
            step_config = step.get("config", {})
            
            logger.info(f"Executing step '{step_name}' of type '{step_type}'")
            
            if step_type not in ("processor", "custom"):
                return {
                    "error": f"Unsupported step type: {step_type}",
                    "processor": "none",
                    "timestamp": context.get("timestamp", "")
                }
            
            # Get the processor with the cleaned configuration
            processor_type = step.get("name", "text_extraction")
            processor = get_processor(processor_type, step_config)
            
            # Execute the processor
            # Special case for embedding processor which needs the document object
            if processor_type == "embedding" and hasattr(processor, "process") and 'document_id' in context:
                from database.session import get_db
                # Get a new db session
                async for db in get_db():
                    # Get the document from the database
                    document = await db.get(Document, UUID(context['document_id']))
                    if document:
                        result = await processor.process(document, context)
                    else:
                        result = {"error": f"Document not found: {context['document_id']}"}
                    break  # Only need one iteration
            else:
                # Regular processors get the document content as string
                result = await processor.process(document_content, context)
            
            # Log the result (excluding large keys)
            log_result = {k: v for k, v in result.items() if k not in ('embeddings', 'chunks_text')}
            #logger.info(f"Step '{step_name}' result: {log_result}")
            
            return result
        except Exception as e:
            logger.error(f"Error in step '{step.get('name', 'unknown')}': {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "processor": step.get("name", "unknown"),
                "timestamp": context.get("timestamp", "")
            }
    
    def _generate_results_summary(self) -> Dict[str, Any]:
        """
        Generates a summary of the results of all steps
        
        Returns:
            Dict[str, Any]: Results summary
        """
        summary = {
            "successful_steps": 0,
            "failed_steps": 0,
            "total_steps": len(self.context.get("results", {})),
            "extracted_info": {}
        }
        
        # Count successful and failed steps
        for step_name, result in self.context.get("results", {}).items():
            if "error" in result:
                summary["failed_steps"] += 1
            else:
                summary["successful_steps"] += 1
        
        # Extract relevant information
        if "summary" in self.context:
            summary["extracted_info"]["summary"] = self.context["summary"]
        
        if "keywords" in self.context:
            summary["extracted_info"]["keywords"] = self.context["keywords"]
        
        if "sentiment" in self.context:
            summary["extracted_info"]["sentiment"] = {
                "label": self.context.get("sentiment", "NEUTRAL"),
                "polarity": self.context.get("polarity", 0.0)
            }
        
        if "word_count" in self.context:
            summary["extracted_info"]["text_stats"] = {
                "word_count": self.context.get("word_count", 0),
                "char_count": self.context.get("char_count", 0)
            }
        
        return summary


async def create_processing_result(db, document_id: UUID, pipeline_name: str, results: Dict[str, Any]) -> DocumentProcessingResult:
    """
    Save the processing results in the database
    
    Args:
        db: Sesión de base de datos
        document_id: ID of the document
        pipeline_name: Name of the pipeline
        results: Processing results
        
    Returns:
        DocumentProcessingResult: Results record
    """
    # Extract information from results - look in the step results
    step_results = results.get("results", {})
    
    logger.debug(f"Creating processing result from pipeline execution. Steps: {list(step_results.keys())}")
    
    # Try to find summary from summarizer step
    summary = ""
    if "summarizer" in step_results and "summary" in step_results["summarizer"]:
        summary = step_results["summarizer"]["summary"]
        logger.debug(f"Found summary from summarizer step: {summary[:100]}...")
    else:
        logger.warning(f"Summary not found in results. Available step results: {list(step_results.keys())}")
        logger.debug(f"Summarizer step data: {step_results.get('summarizer', {})}")
    
    # Try to find keywords from keyword_extraction step
    keywords = []
    if "keyword_extraction" in step_results and "keywords" in step_results["keyword_extraction"]:
        keywords = step_results["keyword_extraction"]["keywords"]
        logger.debug(f"Found keywords from keyword_extraction step: {keywords}")
    else:
        logger.warning(f"Keywords not found in results. Available step results: {list(step_results.keys())}")
        logger.debug(f"Keyword step data: {step_results.get('keyword_extraction', {})}")
    
    # Find total tokens used
    token_count = 0
    for step_name, step_result in step_results.items():
        if "tokens_used" in step_result:
            token_count += step_result["tokens_used"]
    
    # Create results record
    result = DocumentProcessingResult(
        document_id=document_id,
        pipeline_name=pipeline_name,
        summary=summary,
        keywords=keywords,
        token_count=token_count,
        process_metadata=results
    )
    
    # Save in database
    db.add(result)
    await db.commit()
    await db.refresh(result)
    
    logger.info(f"Created DocumentProcessingResult with summary length: {len(summary) if summary else 0}, keywords: {len(keywords)}")
    
    return result 