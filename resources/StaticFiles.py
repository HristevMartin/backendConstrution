from flask_restful import Resource
from flask import send_file, abort
import os

class ServeUploadedFile(Resource):
    def get(self, folder, user_id, filename):
        """
        Serve uploaded files like images
        URL format: /uploads/{folder}/{user_id}/{filename}
        Example: /uploads/profile_images/user123/image.jpg
        """
        try:
            # Construct the file path
            file_path = os.path.join('uploads', folder, user_id, filename)
            
            # Check if file exists and is within uploads directory (security check)
            if not os.path.exists(file_path):
                abort(404)
            
            # Ensure the path is within the uploads directory (prevent directory traversal)
            if not os.path.abspath(file_path).startswith(os.path.abspath('uploads')):
                abort(403)
            
            # Serve the file
            return send_file(file_path)
            
        except Exception as e:
            print(f"Error serving file: {str(e)}")
            abort(404) 