from google.cloud import firestore
from app.core.config import settings
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class FirestoreService:
    def __init__(self):
        self.db = firestore.Client(project=settings.GCP_PROJECT_ID)
        self.collections = {
            'users': 'users',
            'applications': 'loan_applications',
            'documents': 'documents',
            'verifications': 'verification_results'
        }
    
    def get_collection(self, collection_name: str):
        """Get a Firestore collection reference"""
        return self.db.collection(self.collections[collection_name])
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user document"""
        try:
            doc_ref = self.get_collection('users').document()
            user_data['created_at'] = datetime.utcnow()
            user_data['updated_at'] = datetime.utcnow()
            doc_ref.set(user_data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Clerk user ID"""
        try:
            users = self.get_collection('users').where('clerk_user_id', '==', clerk_user_id).limit(1).stream()
            for user in users:
                user_data = user.to_dict()
                user_data['id'] = user.id
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user by clerk ID: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by document ID"""
        try:
            doc_ref = self.get_collection('users').document(user_id)
            doc = doc_ref.get()
            if doc.exists:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    # Application operations
    async def create_application(self, application_data: Dict[str, Any]) -> str:
        """Create a new loan application"""
        try:
            doc_ref = self.get_collection('applications').document()
            application_data['created_at'] = datetime.utcnow()
            application_data['updated_at'] = datetime.utcnow()
            doc_ref.set(application_data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            raise Exception(f"Failed to create application: {str(e)}")
    
    async def get_application_by_id(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get application by ID"""
        try:
            doc_ref = self.get_collection('applications').document(application_id)
            doc = doc_ref.get()
            if doc.exists:
                app_data = doc.to_dict()
                app_data['id'] = doc.id
                return app_data
            return None
        except Exception as e:
            logger.error(f"Error getting application by ID: {e}")
            return None
    
    async def get_applications_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a user"""
        try:
            applications = self.get_collection('applications').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for app in applications:
                app_data = app.to_dict()
                app_data['id'] = app.id
                result.append(app_data)
            return result
        except Exception as e:
            logger.error(f"Error getting applications by user: {e}")
            return []
    
    async def get_all_applications(self) -> List[Dict[str, Any]]:
        """Get all applications in the database (for global stats)"""
        try:
            applications = self.get_collection('applications').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for app in applications:
                app_data = app.to_dict()
                app_data['id'] = app.id
                result.append(app_data)
            return result
        except Exception as e:
            logger.error(f"Error getting all applications: {e}")
            return []
    
    async def update_application(self, application_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an application"""
        try:
            doc_ref = self.get_collection('applications').document(application_id)
            update_data['updated_at'] = datetime.utcnow()
            doc_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating application: {e}")
            return False
    
    async def delete_application(self, application_id: str) -> bool:
        """Delete an application"""
        try:
            doc_ref = self.get_collection('applications').document(application_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting application: {e}")
            return False
    
    # Document operations
    async def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a new document"""
        try:
            doc_ref = self.get_collection('documents').document()
            document_data['uploaded_at'] = datetime.utcnow()
            doc_ref.set(document_data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise Exception(f"Failed to create document: {str(e)}")
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            doc_ref = self.get_collection('documents').document(document_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                return doc_data
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID: {e}")
            return None
    
    async def get_documents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a user"""
        try:
            documents = self.get_collection('documents').where('user_id', '==', user_id).order_by('uploaded_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for doc in documents:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                result.append(doc_data)
            return result
        except Exception as e:
            logger.error(f"Error getting documents by user: {e}")
            return []
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from all users"""
        try:
            documents = self.get_collection('documents').order_by('uploaded_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for doc in documents:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                result.append(doc_data)
            return result
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return []
    
    async def get_documents_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all documents for an application"""
        try:
            documents = self.get_collection('documents').where('application_id', '==', application_id).stream()
            result = []
            for doc in documents:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                result.append(doc_data)
            return result
        except Exception as e:
            logger.error(f"Error getting documents by application: {e}")
            return []
    
    async def update_document(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a document"""
        try:
            doc_ref = self.get_collection('documents').document(document_id)
            doc_ref.update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        try:
            doc_ref = self.get_collection('documents').document(document_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def delete_documents_by_application(self, application_id: str) -> bool:
        """Delete all documents associated with an application"""
        try:
            # Get all documents for the application
            documents = await self.get_documents_by_application(application_id)
            
            # Delete each document
            for doc in documents:
                doc_ref = self.get_collection('documents').document(doc["id"])
                doc_ref.delete()
            
            logger.info(f"Deleted {len(documents)} documents for application {application_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents by application: {e}")
            return False
    
    # Verification operations
    async def create_verification(self, verification_data: Dict[str, Any]) -> str:
        """Create a new verification result"""
        try:
            doc_ref = self.get_collection('verifications').document()
            verification_data['created_at'] = datetime.utcnow()
            verification_data['updated_at'] = datetime.utcnow()
            doc_ref.set(verification_data)
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error creating verification: {e}")
            raise Exception(f"Failed to create verification: {str(e)}")
    
    async def get_verifications_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """Get all verifications for an application"""
        try:
            verifications = self.get_collection('verifications').where('application_id', '==', application_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for ver in verifications:
                ver_data = ver.to_dict()
                ver_data['id'] = ver.id
                result.append(ver_data)
            return result
        except Exception as e:
            logger.error(f"Error getting verifications by application: {e}")
            return []
    
    async def get_latest_verification(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest verification for an application"""
        try:
            verifications = self.get_collection('verifications').where('application_id', '==', application_id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(1).stream()
            for ver in verifications:
                ver_data = ver.to_dict()
                ver_data['id'] = ver.id
                return ver_data
            return None
        except Exception as e:
            logger.error(f"Error getting latest verification: {e}")
            return None
    
    async def get_all_verifications_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all verifications for a user's applications"""
        try:
            # First get all application IDs for the user
            applications = await self.get_applications_by_user(user_id)
            application_ids = [app['id'] for app in applications]
            
            if not application_ids:
                return []
            
            # Get verifications for all applications
            verifications = self.get_collection('verifications').where('application_id', 'in', application_ids).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            result = []
            for ver in verifications:
                ver_data = ver.to_dict()
                ver_data['id'] = ver.id
                result.append(ver_data)
            return result
        except Exception as e:
            logger.error(f"Error getting all verifications by user: {e}")
            return []
    
    async def delete_verifications_by_application(self, application_id: str) -> bool:
        """Delete all verifications for an application"""
        try:
            verifications = self.get_collection('verifications').where('application_id', '==', application_id).stream()
            for ver in verifications:
                ver.reference.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting verifications by application: {e}")
            return False
    
    async def delete_verifications_by_document(self, document_id: str) -> bool:
        """Delete all verifications for a document"""
        try:
            verifications = self.get_collection('verifications').where('document_id', '==', document_id).stream()
            for ver in verifications:
                ver.reference.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting verifications by document: {e}")
            return False

# Global instance
firestore_service = FirestoreService()
