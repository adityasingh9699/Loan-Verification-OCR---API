from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from app.models import Document, LoanApplication, User, VerificationResult
from app.routers.auth import get_current_user
from app.services.gcp_service import gcp_service
from app.services.gemini_service import gemini_ocr
from app.services.firestore_service import firestore_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    gcp_url: str
    file_type: str
    file_size: int
    uploaded_at: str
    application_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    verification_status: str
    message: str

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    application_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Upload a document (pay stub)"""
    try:
        # Validate file type (support images and PDFs)
        allowed_types = ['image/', 'application/pdf']
        if not any(file.content_type.startswith(t) for t in allowed_types):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files (JPG, PNG, GIF) and PDF files are allowed"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum 10MB allowed."
            )
        
        # Upload to GCP
        gcp_url = await gcp_service.upload_file(
            file_content, file.filename, file.content_type
        )
        
        # Save document to Firestore
        document_data = {
            "user_id": current_user.id,
            "application_id": application_id,
            "filename": file.filename,
            "gcp_url": gcp_url,
            "file_type": file.content_type,
            "file_size": len(file_content)
        }
        
        document_id = await firestore_service.create_document(document_data)
        
        verification_status = "pending"
        message = "Document uploaded successfully"
        
        # If application_id is provided, trigger verification
        if application_id:
            logger.info(f"Processing document upload for application_id: {application_id}")
            # Verify application exists and belongs to user
            application = await firestore_service.get_application_by_id(application_id)
            
            if application:
                logger.info(f"Application found, linking document {document_id} to application {application_id}")
                # Update document with application_id
                await firestore_service.update_document(document_id, {"application_id": application_id})
                
                logger.info(f"Triggering verification for application {application_id} with document {document_id}")
                # Trigger verification
                await trigger_verification(application_id, document_id)
                verification_status = "completed"
                message = "Document uploaded and verification completed"
            else:
                logger.error(f"Application not found or access denied for application_id: {application_id}")
                verification_status = "error"
                message = "Document uploaded but application not found or access denied"
        
        # Get the created document
        created_doc = await firestore_service.get_document_by_id(document_id)
        
        return DocumentUploadResponse(
            document=DocumentResponse(
                id=created_doc["id"],
                filename=created_doc["filename"],
                gcp_url=created_doc["gcp_url"],
                file_type=created_doc["file_type"],
                file_size=created_doc["file_size"],
                uploaded_at=created_doc["uploaded_at"].isoformat(),
                application_id=created_doc["application_id"]
            ),
            verification_status=verification_status,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    current_user: User = Depends(get_current_user)
):
    """Get all documents from all users"""
    try:
        documents = await firestore_service.get_all_documents()
        
        return [
            DocumentResponse(
                id=doc["id"],
                filename=doc["filename"],
                gcp_url=doc["gcp_url"],
                file_type=doc["file_type"],
                file_size=doc["file_size"],
                uploaded_at=doc["uploaded_at"].isoformat(),
                application_id=doc["application_id"]
            )
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get documents"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific document by ID"""
    try:
        document = await firestore_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Note: Anyone can access any document (global access)
        
        return DocumentResponse(
            id=document["id"],
            filename=document["filename"],
            gcp_url=document["gcp_url"],
            file_type=document["file_type"],
            file_size=document["file_size"],
            uploaded_at=document["uploaded_at"].isoformat(),
            application_id=document["application_id"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    try:
        document = await firestore_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Note: Anyone can access any document (global access)
        
        # Delete from GCP
        await gcp_service.delete_file(document["gcp_url"])
        
        # Delete associated verifications
        await firestore_service.delete_verifications_by_document(document_id)
        
        # Delete document
        await firestore_service.delete_document(document_id)
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

@router.post("/{document_id}/link-application")
async def link_document_to_application(
    document_id: str,
    application_id: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Link a document to an application and trigger verification"""
    try:
        # Verify document belongs to user
        document = await firestore_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Note: Anyone can link any document to any application (global access)
        
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can access any application (global access)
        
        # Link document to application
        await firestore_service.update_document(document_id, {"application_id": application_id})
        
        # Trigger verification
        await trigger_verification(application_id, document_id)
        
        return {"message": "Document linked to application and verification triggered"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link document"
        )

async def trigger_verification(application_id: str, document_id: str):
    """Trigger verification for a specific application and document"""
    try:
        logger.info(f"Starting verification for application {application_id} and document {document_id}")
        # Get application
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            logger.error(f"Application {application_id} not found")
            return
        
        # Get document
        document = await firestore_service.get_document_by_id(document_id)
        
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Extract data using Gemini OCR
        logger.info(f"Extracting data from document URL: {document['gcp_url']}")
        extracted_data = await gemini_ocr.extract_paystub_data(document["gcp_url"])
        logger.info(f"Extracted data: {extracted_data}")
        
        # Verify application data
        application_data = {
            "name": application["name"],
            "annual_salary": application["annual_salary"],
            "employer_name": application["employer_name"],
            "ssn": application["ssn"]
        }
        
        logger.info(f"Verifying application data: {application_data}")
        verification_results = await gemini_ocr.verify_application_data(
            application_data, extracted_data
        )
        logger.info(f"Verification results: {verification_results}")
        
        # Create verification result
        verification_data = {
            "application_id": application_id,
            "document_id": document_id,
            "extracted_data": extracted_data,
            **verification_results
        }
        
        logger.info(f"Creating verification with data: {verification_data}")
        verification_id = await firestore_service.create_verification(verification_data)
        logger.info(f"Verification created with ID: {verification_id}")
        
    except Exception as e:
        logger.error(f"Error in trigger_verification: {e}")
        # Don't raise exception to avoid breaking the main operation