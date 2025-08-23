from flask import request
from werkzeug.datastructures import FileStorage
from flask_restful import Resource
from util.gcs_handler import GCSHandler
from models.ClientProject import ClientProject
import json
import uuid
from datetime import datetime

class ClientProjects(Resource):
    def post(self):
        try:
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('images')))
            
            # Generate unique project ID
            project_id = str(uuid.uuid4())
            print(f"Generated project ID: {project_id}")
            
            # Get form data
            form_data = {}
            for key in request.form:
                form_data[key] = request.form[key]
            
            # Add project metadata
            form_data['project_id'] = project_id
            form_data['created_at'] = datetime.utcnow().isoformat()
            
            # Handle multiple file uploads using Google Cloud Storage
            project_images = request.files.getlist('images')
            image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(project_images)} images for project: {project_id}')
                    
                    for image in project_images:
                        if image and image.filename != '':
                            try:
                                # Generate unique filename to prevent conflicts
                                file_extension = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else 'jpg'
                                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                                
                                # Use existing upload_profile_image method with project_id as user_id
                                file_url = gcs_handler.upload_profile_image(
                                    file=image,
                                    user_id=f"project_{project_id}",
                                    file_type='profile_project_pictures'
                                )
                                
                                if file_url:
                                    image_urls.append(file_url)
                                    print(f"Image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler: {str(e)}")
                    return {"error": "Failed to initialize cloud storage"}, 500
            else:
                return {"error": "At least one image is required"}, 400
            
            # Add image URLs to form data
            form_data['image_urls'] = image_urls
            
            print('Final form data:', {
                'project_id': project_id,
                'email': form_data.get('email', 'N/A'),
                'image_count': len(image_urls)
            })
            
            # Save project data to database using the ClientProject model
            try:

                project = ClientProject.create_project(form_data, image_urls)
                project.save()
                
                print(f'Project saved to database successfully with ID: {project.project_id}')
                
                # Return the saved project data
                return {
                    "success": True,
                    "message": "Project created and saved successfully",
                    "project_id": project.project_id,
                    "database_id": str(project.id),
                    "data": project.to_dict(),
                    "images_uploaded": len(image_urls),
                    "image_urls": image_urls
                }, 201
                
            except Exception as db_error:
                print(f"Error saving to database: {str(db_error)}")
                # Even if database save fails, we still uploaded images successfully
                return {
                    "success": False,
                    "message": "Project created but failed to save to database",
                    "error": str(db_error),
                    "project_id": project_id,
                    "images_uploaded": len(image_urls),
                    "image_urls": image_urls
                }, 500
            
        except Exception as e:
            print(f"Error creating project: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to create project: {str(e)}"}, 500

class GetClientProject(Resource):
    def get(self, project_id):
        """Get a specific client project by project_id"""
        try:
            project = ClientProject.get_by_project_id(project_id)
            
            if not project:
                return {"error": "Project not found"}, 404
            
            return {
                "success": True,
                "project": project.to_dict()
            }, 200
            
        except Exception as e:
            print(f"Error fetching project {project_id}: {str(e)}")
            return {"error": f"Failed to fetch project: {str(e)}"}, 500

class GetClientProjectsByEmail(Resource):
    def get(self, email):
        """Get all client projects by email"""
        try:
            projects = ClientProject.get_by_email(email)
            
            projects_list = [project.to_dict() for project in projects]
            
            return {
                "success": True,
                "projects": projects_list,
                "count": len(projects_list)
            }, 200
            
        except Exception as e:
            print(f"Error fetching projects for email {email}: {str(e)}")
            return {"error": f"Failed to fetch projects: {str(e)}"}, 500

class GetAllClientProjects(Resource):
    def get(self):
        """Get all client projects (recent 50)"""
        try:
            # Get optional limit parameter
            limit = request.args.get('limit', 50, type=int)
            
            projects = ClientProject.get_recent_projects(limit=limit)
            projects_list = [project.to_dict() for project in projects]
            
            return {
                "success": True,
                "projects": projects_list,
                "count": len(projects_list),
                "limit": limit
            }, 200
            
        except Exception as e:
            print(f"Error fetching all projects: {str(e)}")
            return {"error": f"Failed to fetch projects: {str(e)}"}, 500