from google.cloud import storage
from app.core.config import settings
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

class GCPService:
    def __init__(self):
        self.bucket_name = settings.GCP_BUCKET_NAME
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str) -> str:
        """Upload file to GCP Cloud Storage and return public URL"""
        try:
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Create blob
            blob = self.bucket.blob(unique_filename)
            
            # Upload file
            blob.upload_from_string(file_content, content_type=content_type)
            
            # Make blob publicly accessible
            blob.make_public()
            
            # Return public URL
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error uploading file to GCP: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def delete_file(self, gcp_url: str) -> bool:
        """Delete file from GCP Cloud Storage"""
        try:
            # Extract blob name from URL
            blob_name = gcp_url.split(f"https://storage.googleapis.com/{self.bucket_name}/")[-1]
            
            # Delete blob
            blob = self.bucket.blob(blob_name)
            blob.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from GCP: {e}")
            return False
    
    async def get_file_url(self, gcp_url: str) -> Optional[str]:
        """Get signed URL for private file access"""
        try:
            # Extract blob name from URL
            blob_name = gcp_url.split(f"https://storage.googleapis.com/{self.bucket_name}/")[-1]
            
            # Generate signed URL (valid for 1 hour)
            blob = self.bucket.blob(blob_name)
            signed_url = blob.generate_signed_url(expiration=3600)
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating signed URL: {e}")
            return None

# Global instance
gcp_service = GCPService()
