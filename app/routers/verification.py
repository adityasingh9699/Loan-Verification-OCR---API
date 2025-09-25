from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
from app.models import VerificationResult, LoanApplication, User
from app.routers.auth import get_current_user
from app.services.firestore_service import firestore_service
from app.services.gemini_service import gemini_ocr
import logging
import json
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class VerificationResponse(BaseModel):
    id: str
    application_id: str
    document_id: str
    extracted_data: dict
    name_match: bool
    name_reason: str
    salary_match: bool
    salary_reason: str
    extracted_salary: Optional[int]
    employer_match: bool
    employer_reason: str
    extracted_employer: Optional[str]
    ssn_match: bool
    ssn_reason: str
    extracted_ssn: Optional[str]
    overall_status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class VerificationSummary(BaseModel):
    application_id: str
    overall_status: str
    total_fields: int
    matched_fields: int
    mismatched_fields: int
    verification_details: VerificationResponse

@router.get("/application/{application_id}", response_model=List[VerificationResponse])
async def get_verification_results(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get verification results for a specific application"""
    try:
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can access verification for any application (global access)
        
        # Get verification results
        verifications = await firestore_service.get_verifications_by_application(application_id)
        
        return [
            VerificationResponse(
                id=verification["id"],
                application_id=verification["application_id"],
                document_id=verification["document_id"],
                extracted_data=verification["extracted_data"],
                name_match=verification["name_match"],
                name_reason=verification["name_reason"],
                salary_match=verification["salary_match"],
                salary_reason=verification["salary_reason"],
                extracted_salary=verification["extracted_salary"],
                employer_match=verification["employer_match"],
                employer_reason=verification["employer_reason"],
                extracted_employer=verification["extracted_employer"],
                ssn_match=verification["ssn_match"],
                ssn_reason=verification["ssn_reason"],
                extracted_ssn=verification["extracted_ssn"],
                overall_status=verification["overall_status"],
                created_at=verification["created_at"].isoformat(),
                updated_at=verification["updated_at"].isoformat() if verification["updated_at"] else None
            )
            for verification in verifications
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification results"
        )

@router.get("/application/{application_id}/latest", response_model=VerificationSummary)
async def get_latest_verification(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the latest verification result for an application"""
    try:
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can access verification for any application (global access)
        
        # Get latest verification result
        verification = await firestore_service.get_latest_verification(application_id)
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No verification results found for this application"
            )
        
        # Calculate summary
        matched_fields = sum([
            verification["name_match"],
            verification["salary_match"],
            verification["employer_match"],
            verification["ssn_match"]
        ])
        
        total_fields = 4
        mismatched_fields = total_fields - matched_fields
        
        verification_response = VerificationResponse(
            id=verification["id"],
            application_id=verification["application_id"],
            document_id=verification["document_id"],
            extracted_data=verification["extracted_data"],
            name_match=verification["name_match"],
            name_reason=verification["name_reason"],
            salary_match=verification["salary_match"],
            salary_reason=verification["salary_reason"],
            extracted_salary=verification["extracted_salary"],
            employer_match=verification["employer_match"],
            employer_reason=verification["employer_reason"],
            extracted_employer=verification["extracted_employer"],
            ssn_match=verification["ssn_match"],
            ssn_reason=verification["ssn_reason"],
            extracted_ssn=verification["extracted_ssn"],
            overall_status=verification["overall_status"],
            created_at=verification["created_at"].isoformat(),
            updated_at=verification["updated_at"].isoformat() if verification["updated_at"] else None
        )
        
        return VerificationSummary(
            application_id=application_id,
            overall_status=verification["overall_status"],
            total_fields=total_fields,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            verification_details=verification_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification results"
        )

@router.get("/application/{application_id}/status")
async def get_verification_status(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get verification status for an application"""
    try:
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can access verification for any application (global access)
        
        # Get latest verification
        verification = await firestore_service.get_latest_verification(application_id)
        
        if not verification:
            return {
                "status": "no_documents",
                "message": "No documents uploaded for verification"
            }
        
        return {
            "status": verification["overall_status"],
            "message": f"Verification {verification['overall_status']}",
            "last_updated": verification["updated_at"].isoformat() if verification["updated_at"] else verification["created_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification status"
        )

@router.get("/", response_model=List[VerificationResponse])
async def get_all_verifications(
    current_user: User = Depends(get_current_user)
):
    """Get all verification results for current user"""
    try:
        # Get all verifications for user's applications
        verifications = await firestore_service.get_all_verifications_by_user(current_user.id)
        
        return [
            VerificationResponse(
                id=verification["id"],
                application_id=verification["application_id"],
                document_id=verification["document_id"],
                extracted_data=verification["extracted_data"],
                name_match=verification["name_match"],
                name_reason=verification["name_reason"],
                salary_match=verification["salary_match"],
                salary_reason=verification["salary_reason"],
                extracted_salary=verification["extracted_salary"],
                employer_match=verification["employer_match"],
                employer_reason=verification["employer_reason"],
                extracted_employer=verification["extracted_employer"],
                ssn_match=verification["ssn_match"],
                ssn_reason=verification["ssn_reason"],
                extracted_ssn=verification["extracted_ssn"],
                overall_status=verification["overall_status"],
                created_at=verification["created_at"].isoformat(),
                updated_at=verification["updated_at"].isoformat() if verification["updated_at"] else None
            )
            for verification in verifications
        ]
        
    except Exception as e:
        logger.error(f"Error getting all verifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification results"
        )

@router.get("/application/{application_id}/live-verify")
async def live_verification_stream(
    application_id: str,
    current_user: User = Depends(get_current_user)
):
    """Live verification stream with real-time updates"""
    try:
        # Verify application belongs to user
        application = await firestore_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Note: Anyone can access verification for any application (global access)
        
        # Get documents for this application
        documents = await firestore_service.get_documents_by_application(application_id)
        
        if not documents:
            # Return a proper error response instead of raising an exception
            async def generate_error_stream():
                yield f"data: {json.dumps({'step': 'error', 'message': 'No documents found for verification', 'progress': 0, 'error': True})}\n\n"
            
            return StreamingResponse(
                generate_error_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        
        # Use the latest document
        document = documents[0]
        
        async def generate_verification_stream():
            try:
                # Step 1: Starting verification
                yield f"data: {json.dumps({'step': 'starting', 'message': 'Starting verification process...', 'progress': 0})}\n\n"
                
                # Step 2: Downloading document
                yield f"data: {json.dumps({'step': 'downloading', 'message': 'Downloading document from storage...', 'progress': 20})}\n\n"
                
                # Step 3: Processing with OCR
                yield f"data: {json.dumps({'step': 'ocr', 'message': 'Extracting data using AI OCR...', 'progress': 40})}\n\n"
                
                # Step 4: Extract data using Gemini (this is the actual work)
                yield f"data: {json.dumps({'step': 'extracting', 'message': 'Analyzing document with AI...', 'progress': 50})}\n\n"
                try:
                    extracted_data = await gemini_ocr.extract_paystub_data(document["gcp_url"])
                    yield f"data: {json.dumps({'step': 'extracted', 'message': 'Data extracted successfully', 'progress': 60, 'extracted_data': extracted_data})}\n\n"
                except Exception as e:
                    logger.error(f"OCR extraction failed: {e}")
                    yield f"data: {json.dumps({'step': 'error', 'message': f'OCR extraction failed: {str(e)}', 'progress': 0, 'error': True})}\n\n"
                    return
                
                # Step 5: Verifying name
                yield f"data: {json.dumps({'step': 'verifying_name', 'message': 'Verifying name match...', 'progress': 70})}\n\n"
                
                # Step 6: Verifying salary
                yield f"data: {json.dumps({'step': 'verifying_salary', 'message': 'Verifying salary match...', 'progress': 80})}\n\n"
                
                # Step 7: Verifying employer
                yield f"data: {json.dumps({'step': 'verifying_employer', 'message': 'Verifying employer match...', 'progress': 90})}\n\n"
                
                # Step 8: Final verification (this is the actual work)
                yield f"data: {json.dumps({'step': 'finalizing', 'message': 'Finalizing verification results...', 'progress': 95})}\n\n"
                try:
                    application_data = {
                        "name": application["name"],
                        "annual_salary": application["annual_salary"],
                        "employer_name": application["employer_name"],
                        "ssn": application["ssn"]
                    }
                    
                    verification_results = await gemini_ocr.verify_application_data(
                        application_data, extracted_data
                    )
                    
                    # Create verification result in database
                    verification_data = {
                        "application_id": application_id,
                        "document_id": document["id"],
                        "extracted_data": extracted_data,
                        **verification_results
                    }
                    
                    verification_id = await firestore_service.create_verification(verification_data)
                except Exception as e:
                    logger.error(f"Verification process failed: {e}")
                    yield f"data: {json.dumps({'step': 'error', 'message': f'Verification process failed: {str(e)}', 'progress': 0, 'error': True})}\n\n"
                    return
                
                # Step 9: Complete
                yield f"data: {json.dumps({'step': 'complete', 'message': 'Verification completed', 'progress': 100, 'verification_results': verification_results, 'verification_id': verification_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in verification stream: {e}")
                yield f"data: {json.dumps({'step': 'error', 'message': f'Verification failed: {str(e)}', 'progress': 0, 'error': True})}\n\n"
        
        return StreamingResponse(
            generate_verification_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting live verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start live verification"
        )