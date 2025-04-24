# -*- coding: utf-8 -*-
from fileinput import filename
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Body, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import uuid
import json
from io import BytesIO
# Make sure to import text from sqlalchemy!
from sqlalchemy import text
from sqlalchemy.sql import select
from sqlalchemy.orm import selectinload

from database.session import get_db
# Import necessary models and schemas
from database.models.document import Document
from database.models.user import User
from schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    EmbeddingsPayload, # Import new schema
    SearchRequest,    # Import new schema
)
# Import dependency functions from their correct locations
from core.dependencies import get_current_user, get_document_service, get_task_manager
from database.session import get_db
from modules.document.service import DocumentService
import logging
import os # Ensure os is imported if not already at top level
import aiofiles # Import aiofiles for async file reading
from database.models.task import TaskType, TaskPriority, TaskStatus

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Upload a new document to the system
    """
    try:
        logger.info(f"Receiving file: {file.filename}, Size: {file.size} bytes")
        content = await file.read()
        logger.info(f"Content read: {len(content)} bytes, content type: {file.content_type}")
        
        name = f"{file.filename}"

        logger.info(f"Document name: {name}")
        document_data = DocumentCreate(
            name=name,
            user_id=current_user.id
            # Content is passed separately to the service
        )

        # Always pass content as bytes to the document service
        document = await doc_service.create_document(
            db=db,
            document_data=document_data,
            content=content,  # Pass raw bytes 
            user_id=current_user.id # Re-add required user_id argument
        )

        # Verify that the document was created correctly
        if not document or not document.id:
            error_msg = "The document was not created correctly"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Document created with ID: {document.id}")

        # Get the fresh document from the database to ensure all fields are present
        fresh_document = await doc_service.get_document(db, document.id)
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
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Get the list of user documents
    """
    try:
        # Validate limit to avoid overload
        limit = min(limit, 1000) # Set a reasonable maximum limit

        documents = await doc_service.get_user_documents(
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
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Get a document by its ID
    """
    try:
        # --- MODIFIED: Use service to get document with details ---
        document = await doc_service.get_document_with_details(db, document_id)
        # ---------------------------------------------------------

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )
            
        # --- Keep permission check in the API layer ---
        # Verify permission
        if document.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document"
            )
             
        # The document object returned by the service now potentially includes
        # synthesized processing_results. We can return it directly.
        # The response_model=DocumentResponse will handle serialization.
        return document

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
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Download a document by its ID
    """
    try:
        # First check if document exists and user has permission
        document = await doc_service.get_document(db, document_id)
        
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
        
        # Check if file_path exists and is not empty
        if not document.file_path:
             logger.error(f"Document {document_id} has no associated file path.")
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="Document file path not found"
             )

        file_path = document.file_path

        # Check if file exists physically on disk
        if not os.path.exists(file_path):
            logger.error(f"File not found at path: {file_path} for document {document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on storage"
            )
            
        # Try to read the file content asynchronously
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
        except FileNotFoundError: # Catch specific error
             logger.error(f"File not found at path during read attempt: {file_path}")
             raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="Document file not found on storage"
             )
        except IOError as e: # Catch other IO errors
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error reading document file: {str(e)}"
            )
        
        if not content: # Should not happen if file read was successful, but as a safeguard
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content could not be read or is empty"
            )
        
        # Determine filename and content type
        filename = document.title or f"document-{document_id}.bin" # Default to .bin
        # Ensure filename doesn't have problematic characters if based on title
        # (Sanitization might be needed depending on how titles are created)
        import re 
        filename = re.sub(r'[\\/*?:"<>|]', "_", filename) # Basic sanitization

        content_type = "application/octet-stream"  # Default
        
        # Try to determine content type from document type or name
        if hasattr(document, 'type') and document.type:
            doc_type_lower = document.type.lower()
            if doc_type_lower == "pdf":
                content_type = "application/pdf"
                if not filename.lower().endswith('.pdf'): filename += ".pdf"
            elif doc_type_lower in ["docx", "doc"]:
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if not filename.lower().endswith('.docx'): filename += ".docx"
            elif doc_type_lower in ["xlsx", "xls"]:
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if not filename.lower().endswith('.xlsx'): filename += ".xlsx"
            elif doc_type_lower == "txt":
                content_type = "text/plain"
                if not filename.lower().endswith('.txt'): filename += ".txt"
            elif doc_type_lower == "json":
                 content_type = "application/json"
                 if not filename.lower().endswith('.json'): filename += ".json"
            # Add more types as needed (jpg, png, etc.)

        logger.info(f"Preparing download for document {document_id}, filename: '{filename}', type: {content_type}")

        # Create a streaming response with the file content
        return StreamingResponse(
            BytesIO(content),
            media_type=content_type,
            headers={
                # Use attachment to force download, inline to suggest display
                # Ensure filename is properly quoted for headers
                "Content-Disposition": f'attachment; filename="{filename}"' 
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading document: {str(e)}" # Avoid exposing raw error in prod
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Delete a document
    """
    try:
        # Get document to verify ownership before deleting
        document = await doc_service.get_document(db=db, document_id=document_id)
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

        logger.info(f"Deleting document {document_id} requested by user {current_user.id}")

        deleted = await doc_service.delete_document(db=db, document_id=document_id)

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
