from google.cloud import storage
from werkzeug.utils import secure_filename
import os
from config import Config
from datetime import datetime
import mimetypes

class GCSHandler:
    def __init__(self):
        """Initialize GCS client with credentials"""
        try:
            # Initialize the client with service account credentials
            if Config.GCS_CREDENTIALS_PATH and os.path.exists(Config.GCS_CREDENTIALS_PATH):
                self.client = storage.Client.from_service_account_json(
                    Config.GCS_CREDENTIALS_PATH,
                    project=Config.GCS_PROJECT_ID
                )
            else:
                # Use default credentials (for cloud environments)
                self.client = storage.Client(project=Config.GCS_PROJECT_ID)
            
            self.bucket_name = Config.GCS_BUCKET_NAME
            self.bucket = self.client.bucket(self.bucket_name)
            
        except Exception as e:
            print(f"Error initializing GCS client: {str(e)}")
            raise e

    def upload_profile_image(self, file, user_id, file_type='profile_image_pictures'):
        """
        Upload a profile image to GCS
        
        Args:
            file: The file object to upload
            user_id: The user ID for folder organization
            file_type: Either 'profile_image_pictures' or 'profile_project_pictures'
        
        Returns:
            str: The public URL of the uploaded file or None if failed
        """
        try:
            if not file or file.filename == '':
                return None
            
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            
            # Create the blob path: folder_type/user_id/filename
            blob_path = f"{file_type}/{user_id}/{unique_filename}"
            
            # Create blob object
            blob = self.bucket.blob(blob_path)
            
            # Set content type
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            blob.content_type = content_type
            
            # Upload the file
            file.seek(0)  # Reset file pointer to beginning
            blob.upload_from_file(file, content_type=content_type)
            
            # Make the blob publicly accessible (optional - you might want authentication)
            blob.make_public()
            
            # Return the public URL
            public_url = blob.public_url
            print(f"File uploaded successfully to GCS: {public_url}")
            
            return public_url
            
        except Exception as e:
            print(f"Error uploading file to GCS: {str(e)}")
            return None

    def delete_file(self, file_url):
        """
        Delete a file from GCS using its URL
        
        Args:
            file_url: The public URL of the file to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract blob name from URL
            # Format: https://storage.googleapis.com/bucket_name/blob_path
            if not file_url or 'storage.googleapis.com' not in file_url:
                return False
            
            # Extract the blob path from URL
            parts = file_url.split(f'/{self.bucket_name}/')
            if len(parts) < 2:
                return False
            
            blob_path = parts[1]
            blob = self.bucket.blob(blob_path)
            
            # Delete the blob
            blob.delete()
            print(f"File deleted successfully from GCS: {file_url}")
            return True
            
        except Exception as e:
            print(f"Error deleting file from GCS: {str(e)}")
            return False

    def get_signed_url(self, blob_path, expiration_minutes=60):
        """
        Generate a signed URL for private file access
        
        Args:
            blob_path: The path of the blob in GCS
            expiration_minutes: URL expiration time in minutes
        
        Returns:
            str: Signed URL or None if failed
        """
        try:
            blob = self.bucket.blob(blob_path)
            
            # Generate signed URL
            from datetime import timedelta
            expiration_time = timedelta(minutes=expiration_minutes)
            
            signed_url = blob.generate_signed_url(
                expiration=expiration_time,
                method='GET'
            )
            
            return signed_url
            
        except Exception as e:
            print(f"Error generating signed URL: {str(e)}")
            return None

    def list_user_files(self, user_id, file_type='profile_image_pictures'):
        """
        List all files for a specific user
        
        Args:
            user_id: The user ID
            file_type: Either 'profile_image_pictures' or 'profile_project_pictures'
        
        Returns:
            list: List of file URLs
        """
        try:
            prefix = f"{file_type}/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            file_urls = []
            for blob in blobs:
                file_urls.append(blob.public_url)
            
            return file_urls
            
        except Exception as e:
            print(f"Error listing user files: {str(e)}")
            return [] 