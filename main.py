from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
import logging

from app.routers import applications, auth, documents, verification, stats
from app.core.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OCR Loan Verification API",
    description="API for loan application verification using OCR and AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(verification.router, prefix="/api/verification", tags=["verification"])
app.include_router(stats.router, prefix="/api/stats", tags=["statistics"])

@app.get("/")
async def root():
    return {"message": "OCR Loan Verification API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
