# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
import json
from io import BytesIO
# Make sure to import text from sqlalchemy!
from sqlalchemy import text
from sqlalchemy.sql import select
from sqlalchemy.orm import selectinload

from database.session import get_db
from database.models.document import Document
from schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from core.deps import get_current_user
from modules.document.service import DocumentService
from database.models.user import User
from database.models.pipeline import PipelineExecution
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()
document_service = DocumentService()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new document to the system
    """
    try:
        logger.info(f"Receiving file: {file.filename}, Size: {file.size} bytes")
        content = await file.read()
        logger.info(f"Content read: {len(content)} bytes, content type: {file.content_type}")

        # If no name is provided, use the filename
        if not name:
            name = file.filename

        logger.info(f"Document name: {name}")
        document_data = DocumentCreate(
            name=name
            # Content is passed separately to the service
        )

        # Always pass content as bytes to the document service
        document = await document_service.create_document(
            db=db,
            document_data=document_data,
            content=content,  # Pass raw bytes 
            user_id=current_user.id
        )

        # Verify that the document was created correctly
        if not document or not document.id:
            error_msg = "The document was not created correctly"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Document created with ID: {document.id}")

        # Get the fresh document from the database to ensure all fields are present
        fresh_document = await document_service.get_document(db, document.id)
        if not fresh_document:
            error_msg = "Could not retrieve the newly created document"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Create Pydantic response object
        response_object = DocumentResponse.model_validate(fresh_document)
        logger.info(f"Document created successfully: {response_object.id}")
        
        return response_object

    except HTTPException:
        raise # Re-raise explicit HTTPExceptions
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Unexpected error when uploading document: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error when uploading the document: {str(e)}"
        )


@router.get("", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the list of user documents
    """
    try:
        # Validate limit to avoid overload
        limit = min(limit, 1000) # Set a reasonable maximum limit

        documents = await document_service.get_user_documents(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            type=type # Make sure DocumentService handles this filter if necessary
        )
        # Pydantic v2 validates the list automatically upon return
        return documents
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error getting documents for user {current_user.id}: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting the document list: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a document by its ID
    """
    try:
        # Load document with relationships
        query = select(Document).where(Document.id == document_id).options(
            selectinload(Document.embeddings),
            selectinload(Document.processing_results),
            selectinload(Document.pipeline_executions).options(
                selectinload(PipelineExecution.pipeline)
            )
        )
        
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Verify permission
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document"
            )
            
        # Prepare the response including executions with pipeline details
        document_dict = {
            "id": document.id,
            "title": document.title,
            "content": document.content,
            "status": document.status if hasattr(document, 'status') else None,
            "extracted_text": document.extracted_text if hasattr(document, 'extracted_text') else None,
            "source": document.source if hasattr(document, 'source') else None,
            "metadata": document.metadata if hasattr(document, 'metadata') else None,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "user_id": document.user_id,
            "processing_results": document.processing_results,
            "embeddings": document.embeddings,
            "error": document.error if hasattr(document, 'error') else None,
            "type": document.type
        }
        
        # Add pipeline executions with names
        executions = []
        for execution in document.pipeline_executions:
            pipeline_name = execution.pipeline.name if execution.pipeline else "Unknown"
            
            execution_dict = {
                "id": execution.id,
                "pipeline_id": execution.pipeline_id,
                "document_id": execution.document_id,
                "user_id": execution.user_id,
                "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "created_at": execution.created_at,
                "updated_at": execution.updated_at,
                "pipeline_name": pipeline_name,
                "results": execution.results,
                "parameters": execution.parameters,
                "error_message": execution.error_message
            }
            executions.append(execution_dict)
            
        document_dict["pipeline_executions"] = executions
        
        # If there are no processing_results but there are complete pipeline_executions, we create processing_results from the results
        if (not document.processing_results or len(document.processing_results) == 0) and executions:
            completed_executions = [exec_dict for exec_dict in executions if exec_dict["status"] == "completed" and exec_dict["results"]]
            
            if completed_executions:
                # We use the last completed execution for processing_results
                latest_execution = max(completed_executions, key=lambda x: x["completed_at"] if x["completed_at"] else x["created_at"])
                
                # If there are results, we create a processing_result
                if latest_execution["results"]:
                    processing_results = []
                    result_data = latest_execution["results"]
                    
                    # Extract relevant information from the result
                    summary = None
                    keywords = None
                    token_count = None
                    process_metadata = {}
                    
                    # Try to extract information from the results
                    if "summary" in result_data and isinstance(result_data["summary"], dict):
                        summary = result_data["summary"].get("summary")
                        process_metadata["summary_info"] = result_data["summary"]
                    elif "summary" in result_data and isinstance(result_data["summary"], str):
                        summary = result_data["summary"]
                    
                    if "keywords" in result_data and isinstance(result_data["keywords"], list):
                        keywords = result_data["keywords"]
                    
                    if "tokens_used" in result_data:
                        token_count = result_data["tokens_used"]
                    
                    # Save other relevant fields in process_metadata
                    for key, value in result_data.items():
                        if key not in ["summary", "keywords", "tokens_used"] and value is not None:
                            process_metadata[key] = value
                    
                    # Create a synthetic processing_result
                    processing_result = {
                        "id": uuid.uuid4(),  # Temporary ID for the response
                        "document_id": document.id,
                        "pipeline_name": latest_execution["pipeline_name"],
                        "summary": summary,
                        "keywords": keywords,
                        "token_count": token_count,
                        "process_metadata": process_metadata,
                        "created_at": latest_execution["completed_at"] or latest_execution["created_at"],
                        "updated_at": latest_execution["updated_at"]
                    }
                    
                    processing_results.append(processing_result)
                    document_dict["processing_results"] = processing_results
        
        return document_dict
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting document: {str(e)}"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download a document by its ID
    """
    try:
        # First check if document exists and user has permission
        document = await document_service.get_document(db, document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )
        
        # Verify permission
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document"
            )
        
        # Get the content as bytes
        content = document.content
        
        # If the content is None or empty, try to load it from the file path
        if not content and document.file_path:
            try:
                import os
                if os.path.exists(document.file_path):
                    with open(document.file_path, 'rb') as f:
                        content = f.read()
                else:
                    logger.error(f"File not found at path: {document.file_path}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Document file not found"
                    )
            except Exception as e:
                logger.error(f"Error reading file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error reading document file: {str(e)}"
                )
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not found"
            )
        
        # Determine filename and content type
        filename = document.title or f"document-{document_id}.txt"
        content_type = "application/octet-stream"  # Default
        
        # Try to determine content type from document type or name
        if hasattr(document, 'type') and document.type:
            if document.type.lower() == "pdf":
                content_type = "application/pdf"
                if not filename.lower().endswith('.pdf'):
                    filename += ".pdf"
            elif document.type.lower() in ["docx", "doc"]:
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if not filename.lower().endswith('.docx'):
                    filename += ".docx"
            elif document.type.lower() in ["xlsx", "xls"]:
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if not filename.lower().endswith('.xlsx'):
                    filename += ".xlsx"
            elif document.type.lower() == "txt":
                content_type = "text/plain"
                if not filename.lower().endswith('.txt'):
                    filename += ".txt"
        
        # Create a streaming response with the file content
        return StreamingResponse(
            BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading document: {str(e)}"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document
    """
    try:
        # Get document to verify ownership before deleting
        document = await document_service.get_document(db=db, document_id=document_id)
        if not document:
            # If it does not exist, it is idempotent, we could return 204 or 404
            # Returning 404 is more informative if the client expected it to exist
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="Document not found to delete"
             )

        # Verify that the document belongs to the user or is admin
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this document"
            )

        deleted = await document_service.delete_document(db=db, document_id=document_id)

        if not deleted:
             # This could happen if there was a race condition or a logical error in delete_document
             logger.warning(f"delete_document for {document_id} returned False.")
             # Decide whether to raise an error or just accept (since the desired state is "does not exist")
             # Raising 500 might be more secure if we expect it to always work
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not confirm the deletion of the document"
             )

        # If everything goes well, FastAPI will automatically send 204 No Content
        return None # Important to return None for the 204

    except HTTPException:
        raise # Re-lanzar explícitamente
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error deleting document {document_id} for user {current_user.id}: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting the document: {str(e)}"
        )


@router.post("/embeddings/{document_id}")
async def create_document_embeddings(
    document_id: UUID,
    # Se espera un cuerpo JSON como: {"embeddings": [[...], ...], "chunks_text": ["...", ...], "model": "..."}
    payload: dict = Body(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save pre-calculated embeddings for a document.
    Expects a JSON body with 'embeddings', 'chunks_text' and optionally 'model'.
    """
    try:
        # Extractr datos del payload
        embeddings = payload.get("embeddings")
        chunks_text = payload.get("chunks_text")
        model = payload.get("model", "text-embedding-3-small") # Usar default si no viene

        # Basic payload validations
        if not embeddings or not isinstance(embeddings, list) or not all(isinstance(e, list) for e in embeddings):
             raise HTTPException(status_code=400, detail="The 'embeddings' field is required and must be a list of lists.")
        if not chunks_text or not isinstance(chunks_text, list) or not all(isinstance(t, str) for t in chunks_text):
             raise HTTPException(status_code=400, detail="The 'chunks_text' field is required and must be a list of strings.")
        if len(embeddings) != len(chunks_text):
             raise HTTPException(status_code=400, detail="The number of embeddings must match the number of text chunks.")
        if not model or not isinstance(model, str):
             raise HTTPException(status_code=400, detail="The 'model' field must be a string.")


        # Verify document ownership
        document = await document_service.get_document(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document ownership
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify the embeddings of this document"
            )

        # Guardar embeddings
        saved_embeddings_count = await document_service.save_embeddings(
            db=db,
            document_id=document_id,
            embeddings=embeddings,
            chunks_text=chunks_text,
            model=model
        )

        return {
            "status": "success",
            "message": f"Saved {saved_embeddings_count} embeddings for document {document_id}",
            "document_id": str(document_id),
            "model": model
        }

    except HTTPException:
        raise # Re-lanzar explícitamente
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error saving embeddings for doc {document_id} for user {current_user.id}: {str(e)}\n{error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving embeddings: {str(e)}"
        )

@router.post("/search")
async def search_documents(
    # Using a Pydantic model for the body is more robust
    # class SearchRequest(BaseModel):
    #     query: str
    #     model: str = "text-embedding-3-small"
    #     limit: int = 5
    #     min_similarity: float = 0.5
    # search_params: SearchRequest,
    search_params: dict = Body(...), # Keeping dict for compatibility with the original code
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search documents based on semantic similarity using RAG.
    Expects a JSON body with 'query', and optionally 'model', 'limit', 'min_similarity'.
    """
    try:
        # Extract parameters from the request body and validate/set defaults
        query = search_params.get("query")
        model = search_params.get("model", "text-embedding-3-small")
        document_id = search_params.get("document_id")
        try:
             # Ensure limit is an integer between 1 and a reasonable maximum (e.g., 50)
             limit = min(max(int(search_params.get("limit", 5)), 1), 50)
        except (ValueError, TypeError):
             limit = 5 # Default if not a valid integer
        try:
             # Ensure min_similarity is a float between 0 and 1
             min_similarity = min(max(float(search_params.get("min_similarity", 0.5)), 0.0), 1.0)
        except (ValueError, TypeError):
             min_similarity = 0.5 # Default if not a valid float

        # Log for debugging with sanitized values
        logger.info(f"RAG search: query='{query}', model='{model}', limit={limit}, min_similarity={min_similarity}, user={current_user.id}")

        # Validate that the query is not empty
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The query ('query') is required and must be a string."
            )

        # Delegate the search to the service (assuming search_documents_raw is corrected)
        search_results = await document_service.search_documents_raw(
            db=db,
            query=query,
            model=model,
            limit=limit,
            min_similarity=min_similarity,
            user_id=current_user.id,
            document_id=document_id
        )

        # You might want to format the results here if search_documents_raw
        # returns something raw from the DB, or define a specific response_model.
        return search_results # Assuming the service returns something serializable

    except HTTPException:
         raise # Re-raise explicitly
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error in RAG search for user {current_user.id}: {str(e)}\n{error_detail}")
        # No expose internal details in production
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while performing the search." # Hide detail in production
        )

@router.post("/process-embeddings/{document_id}")
async def process_document_embeddings(
    document_id: UUID,
    model: str = Query("text-embedding-3-small", description="Modelo de embedding a usar"),
    chunk_size: int = Query(1000, ge=100, le=8000, description="Tamaño del chunk"),
    chunk_overlap: int = Query(200, ge=0, le=1000, description="Superposición de chunks"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Processes an existing document: extracts text if necessary,
    divides it into chunks, generates embeddings and saves them.
    """
    try:
        # 1. Get the complete document
        document = await document_service.get_document(db, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # 2. Verify permissions
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission")

        # 3. Configurar y obtener el procesador de embeddings
        try:
            from modules.pipeline.processors import get_processor # Ensure get_processor exists
            embedding_processor = get_processor(
                "embedding", # Use the registered name
                config={
                    "model": model,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                    # No need to pass api_key here if the processor reads from env vars
                }
            )
        except (ImportError, ValueError) as e:
             logger.error(f"Error getting the embedding processor: {e}")
             raise HTTPException(status_code=500, detail="Processing component not available or improperly configured.")

        logger.info(f"Processing embeddings for doc {document_id}...")

        # --- MAIN CHANGE HERE ---
        # 4. Call the process method of the processor, passing the Document object
        #    The processor now handles text extraction.
        result = await embedding_processor.process(document, {}) # Pass the 'document' object
        # ---------------------------

        # 5. Verify the processing result
        if "error" in result:
            logger.error(f"Error during embedding processing for doc {document_id}: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Error generating embeddings: {result['error']}")

        # 6. Save the generated embeddings (if any)
        embeddings_data = result.get("embeddings")
        chunks_text_data = result.get("chunks_text") # Now these are the actual chunks

        if embeddings_data and chunks_text_data:
            logger.info(f"Saving {len(embeddings_data)} generated embeddings for doc {document_id}")
            # Use the model returned by the processor for consistency
            saved_model = result.get("model", model)
            saved_count = await document_service.save_embeddings(
                db=db,
                document_id=document_id,
                embeddings=embeddings_data,
                chunks_text=chunks_text_data, # Save the actual chunks
                model=saved_model
            )

            return {
                "status": "success",
                "message": f"Processed and saved {saved_count} embeddings.",
                "document_id": str(document_id),
                "model": saved_model,
                "chunk_count": result.get("chunk_count", 0)
            }
        elif "chunk_count" in result and result["chunk_count"] == 0:
             # Case where no chunks were generated (empty text or too short after extraction)
             logger.warning(f"No embeddings generated for doc {document_id} (0 chunks).")
             return {
                 "status": "success", # Or "warning"
                 "message": "No embeddings generated (document empty or too short after text extraction).",
                 "document_id": str(document_id),
                 "model": model,
                 "chunk_count": 0
             }
        else:
            # Unexpected error case where missing data in the result
            logger.error(f"Unexpected processor result for doc {document_id}: {result}")
            raise HTTPException(status_code=500, detail="The processor did not generate the expected output.")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Unexpected error in /process-embeddings/{document_id}: {str(e)}\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"Internal error processing embeddings: {str(e)}")