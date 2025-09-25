from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Clerk Authentication
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    
    # Google Cloud Platform
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GCP_BUCKET_NAME: str = ""
    GCP_PROJECT_ID: str = ""
    
    # Gemini AI
    GEMINI_API_KEY: str = ""
    
    # Application
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()
