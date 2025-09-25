from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class User(BaseModel):
    id: Optional[str] = None
    clerk_user_id: str
    email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class LoanApplication(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    annual_salary: int
    employer_name: str
    ssn: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Document(BaseModel):
    id: Optional[str] = None
    user_id: str
    application_id: Optional[str] = None
    filename: str
    gcp_url: str
    file_type: str
    file_size: int
    uploaded_at: Optional[datetime] = None

class VerificationResult(BaseModel):
    id: Optional[str] = None
    application_id: str
    document_id: str
    
    # OCR extracted data
    extracted_data: Dict[str, Any]
    
    # Verification results for each field
    name_match: bool
    name_reason: Optional[str] = None
    
    salary_match: bool
    salary_reason: Optional[str] = None
    extracted_salary: Optional[int] = None
    
    employer_match: bool
    employer_reason: Optional[str] = None
    extracted_employer: Optional[str] = None
    
    ssn_match: bool
    ssn_reason: Optional[str] = None
    extracted_ssn: Optional[str] = None
    
    # Overall verification status
    overall_status: str  # "verified", "mismatch", "pending"
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
