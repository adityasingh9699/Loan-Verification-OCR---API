from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from app.models import LoanApplication, User, VerificationResult, Document
from app.routers.auth import get_current_user
from app.services.gemini_service import gemini_ocr
from app.services.firestore_service import firestore_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class LoanApplicationCreate(BaseModel):
    name: str
    annual_salary: int
    employer_name: str
    ssn: str

class LoanApplicationUpdate(BaseModel):
    name: Optional[str] = None
    annual_salary: Optional[int] = None
    employer_name: Optional[str] = None
    ssn: Optional[str] = None

class LoanApplicationResponse(BaseModel):
    id: str
    name: str
    annual_salary: int
    employer_name: str
    ssn: str
    created_at: str
    updated_at: str
    verification_status: Optional[str] = None
    user_id: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/", response_model=LoanApplicationResponse)
async def create_application(
    application: LoanApplicationCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new loan application"""
    try:
        # Create new application
        application_data = {
            "user_id": current_user.id,
            "name": application.name,
            "annual_salary": application.annual_salary,
            "employer_name": application.employer_name,
            "ssn": application.ssn
        }
        
        application_id = await firestore_service.create_application(application_data)
        
        # Check if there are any documents to verify against
        documents = await firestore_service.get_documents_by_application(application_id)
        
        if documents:
            # Trigger verification for existing documents
            await trigger_verification(application_id)
        
        # Get the created application
        created_app = await firestore_service.get_application_by_id(application_id)
        
        return LoanApplicationResponse(
            id=created_app["id"],
            name=created_app["name"],
            annual_salary=created_app["annual_salary"],
            employer_name=created_app["employer_name"],
            ssn=created_app["ssn"],
            created_at=created_app["created_at"].isoformat(),
            updated_at=created_app["updated_at"].isoformat() if created_app["updated_at"] else None,
            verification_status="pending" if documents else "no_documents"
        )
        
    except Exception as e:
        logger.error(f"Error creating application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application"
        )

@router.get("/", response_model=List[LoanApplicationResponse])
async def get_applications(
    current_user: User = Depends(get_current_user)
):
    """Get all applications from all users"""
    try:
        applications = await firestore_service.get_all_applications()
        
        result = []
        for app in applications:
            # Get latest verification status
            latest_verification = await firestore_service.get_latest_verification(app["id"])
            
            verification_status = latest_verification["overall_status"] if latest_verification else "no_documents"
            
            result.append(LoanApplicationResponse(
                id=app["id"],
                name=app["name"],
                annual_salary=app["annual_salary"],
                employer_name=app["employer_name"],
                ssn=app["ssn"],
                created_at=app["created_at"].isoformat(),
                updated_at=app["updated_at"].isoformat() if app["updated_at"] else None,
                verification_status=verification_status,
                user_id=app.get("user_id", "unknown")  # Add user_id to track who created the application
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get applications"
        )

@router.get("/{application_id}", response_model=LoanApplicationResponse)
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific application by ID"""
    try:
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can view any application (global access)
        
        # Get latest verification status
        latest_verification = await firestore_service.get_latest_verification(application_id)
        
        verification_status = latest_verification["overall_status"] if latest_verification else "no_documents"
        
        return LoanApplicationResponse(
            id=application["id"],
            name=application["name"],
            annual_salary=application["annual_salary"],
            employer_name=application["employer_name"],
            ssn=application["ssn"],
            created_at=application["created_at"].isoformat(),
            updated_at=application["updated_at"].isoformat() if application["updated_at"] else None,
            verification_status=verification_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application"
        )

@router.put("/{application_id}", response_model=LoanApplicationResponse)
async def update_application(
    application_id: str,
    application_update: LoanApplicationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an existing application"""
    try:
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can update any application (global access)
        
        # Update fields
        update_data = application_update.dict(exclude_unset=True)
        
        if update_data:
            await firestore_service.update_application(application_id, update_data)
            
            # Trigger re-verification
            await trigger_verification(application_id)
        
        # Get updated application
        updated_app = await firestore_service.get_application_by_id(application_id)
        
        # Get latest verification status
        latest_verification = await firestore_service.get_latest_verification(application_id)
        
        verification_status = latest_verification["overall_status"] if latest_verification else "no_documents"
        
        return LoanApplicationResponse(
            id=updated_app["id"],
            name=updated_app["name"],
            annual_salary=updated_app["annual_salary"],
            employer_name=updated_app["employer_name"],
            ssn=updated_app["ssn"],
            created_at=updated_app["created_at"].isoformat(),
            updated_at=updated_app["updated_at"].isoformat() if updated_app["updated_at"] else None,
            verification_status=verification_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application"
        )

@router.delete("/{application_id}")
async def delete_application(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an application"""
    try:
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can delete any application (global access)
        
        # Delete associated documents
        await firestore_service.delete_documents_by_application(application_id)
        
        # Delete associated verifications
        await firestore_service.delete_verifications_by_application(application_id)
        
        # Delete application
        await firestore_service.delete_application(application_id)
        
        return {"message": "Application deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete application"
        )

@router.get("/{application_id}/documents", response_model=List[Document])
async def get_application_documents(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a specific application"""
    try:
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can view documents for any application (global access)
        
        # Get documents for this application
        documents = await firestore_service.get_documents_by_application(application_id)
        
        return [
            Document(
                id=doc["id"],
                user_id=doc["user_id"],
                application_id=doc["application_id"],
                filename=doc["filename"],
                gcp_url=doc["gcp_url"],
                file_type=doc["file_type"],
                file_size=doc["file_size"],
                uploaded_at=doc["uploaded_at"]
            )
            for doc in documents
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application documents"
        )

async def trigger_verification(application_id: str):
    """Trigger verification for an application"""
    try:
        # Get application
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            return
        
        # Get associated documents
        documents = await firestore_service.get_documents_by_application(application_id)
        
        for document in documents:
            # Extract data using Gemini OCR
            extracted_data = await gemini_ocr.extract_paystub_data(document["gcp_url"])
            
            # Verify application data
            application_data = {
                "name": application["name"],
                "annual_salary": application["annual_salary"],
                "employer_name": application["employer_name"],
                "ssn": application["ssn"]
            }
            
            verification_results = await gemini_ocr.verify_application_data(
                application_data, extracted_data
            )
            
            # Create verification result
            verification_data = {
                "application_id": application_id,
                "document_id": document["id"],
                "extracted_data": extracted_data,
                **verification_results
            }
            
            await firestore_service.create_verification(verification_data)
        
    except Exception as e:
        logger.error(f"Error in trigger_verification: {e}")
        # Don't raise exception to avoid breaking the main operation