from flask_restful import Resource
from flask import request
from models.TraderProject import Project  
import json
import os
import uuid
from werkzeug.utils import secure_filename

class SaveProject(Resource):
    def post(self):
        try:
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('projectImages')))
            
            # Get form data
            data = {}
            data['title'] = request.form.get('title', '').strip()
            data['description'] = request.form.get('description', '').strip()
            data['projectDate'] = request.form.get('projectDate', '').strip()
            data['userId'] = request.form.get('userId', '').strip()
            
            # Parse expertise from JSON string
            expertise_str = request.form.get('expertise', '[]')
            try:
                data['expertise'] = json.loads(expertise_str)
            except json.JSONDecodeError as e:
                print(f"Error parsing expertise JSON: {e}")
                data['expertise'] = []
            
            # Validate required fields
            if not data['title']:
                return {"error": "Title is required"}, 400
            
            # Handle multiple file uploads
            project_images = request.files.getlist('projectImages')
            image_paths = []
            
            if project_images:
                # Create user-specific upload directory based on userId
                user_id = data.get('userId', 'unknown_user')
                folder_name = str(user_id) if user_id else 'unknown_user'
                upload_folder = os.path.join('uploads', 'project_images', folder_name)
                
                print(f'Creating upload folder for user {user_id}: {upload_folder}')
                os.makedirs(upload_folder, exist_ok=True)
                print(f'Upload folder created successfully: {upload_folder}')
                
                for image in project_images:
                    if image and image.filename != '':
                        try:
                            # Generate unique filename to avoid conflicts
                            filename = secure_filename(image.filename)
                            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                            unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
                            
                            file_path = os.path.join(upload_folder, unique_filename)
                            
                            # Save the file
                            image.save(file_path)
                            image_paths.append(file_path)
                            print(f"Image saved successfully: {file_path}")
                            
                        except Exception as e:
                            print(f"Error saving image {image.filename}: {str(e)}")
                            continue
            
            data['projectImages'] = image_paths
            
            print('Final data to save:', {
                'title': data['title'],
                'description': data['description'][:50] + '...' if len(data['description']) > 50 else data['description'],
                'projectDate': data['projectDate'],
                'expertise': data['expertise'],
                'image_count': len(image_paths)
            })
            
            # Create and save the project
            project = Project(**data)
            project.save()
            
            return {
                "message": "Project saved successfully",
                "project_id": str(project.id),
                "images_saved": len(image_paths)
            }, 200
            
        except Exception as e:
            print(f"Error saving project: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to save project: {str(e)}"}, 500