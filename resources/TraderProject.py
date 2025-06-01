from flask_restful import Resource
from flask import request
from models.TraderProject import Project
import json
import os
import uuid
from werkzeug.utils import secure_filename
from util.gcs_handler import GCSHandler
from models.TraderProfile import TraderProfile
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
            
            # Parse specifications from JSON string (renamed from expertise to match frontend)
            specifications_str = request.form.get('specifications', '[]')
            print(f"Raw specifications received: {specifications_str}")
            
            try:
                data['specifications'] = json.loads(specifications_str)
                print(f"Parsed specifications: {data['specifications']}")
            except json.JSONDecodeError as e:
                print(f"Error parsing specifications JSON: {e}")
                data['specifications'] = []
            
            # Validate required fields
            if not data['title']:
                return {"error": "Title is required"}, 400
            
            # Handle multiple file uploads using Google Cloud Storage
            project_images = request.files.getlist('projectImages')
            image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    user_id = data.get('userId', 'unknown_user')
                    
                    print(f'Uploading {len(project_images)} project images for user: {user_id}')
                    
                    for image in project_images:
                        if image and image.filename != '':
                            try:
                                # Upload each image to GCS
                                file_url = gcs_handler.upload_profile_image(
                                    file=image,
                                    user_id=user_id,
                                    file_type='profile_project_pictures'
                                )
                                
                                if file_url:
                                    image_urls.append(file_url)
                                    print(f"Project image uploaded successfully to GCS: {file_url}")
                                else:
                                    print(f"Failed to upload project image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading project image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler: {str(e)}")
                    return {"error": "Failed to initialize cloud storage"}, 500
            
            data['projectImages'] = image_urls
            
            print('Final data to save:', {
                'title': data['title'],
                'description': data['description'][:50] + '...' if len(data['description']) > 50 else data['description'],
                'projectDate': data['projectDate'],
                'specifications': data['specifications'],
                'image_count': len(image_urls)
            })
            
            # Create and save the project
            project = Project(**data)
            project.save()
            
            return {
                "message": "Project saved successfully",
                "project_id": str(project.id),
                "images_saved": len(image_urls)
            }, 200
            
        except Exception as e:
            print(f"Error saving project: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to save project: {str(e)}"}, 500
        
class GetProjectByID(Resource):
    def get(self, project_id):
        try:
            print('Project ID:', project_id)
            project = Project.objects.get(userId=project_id)
            project_dict = json.loads(project.to_json())
            return project_dict, 200
        except Exception as e:
            return {"error": f"Failed to get project: {str(e)}"}, 500
        

class GetAllProfiles(Resource):
    def get(self):
        try:
            profiles = TraderProfile.objects()
            profile_list = []
            for profile in profiles:
                # Convert each profile to a dictionary with proper serialization
                profile_data = {
                    'id': str(profile.id),
                    'fullName': profile.fullName,
                    'company': profile.company,
                    'bio': profile.bio,
                    'city': profile.city,
                    'yearsExperience': profile.yearsExperience,
                    'specialties': profile.specialties,
                    'selectedTrades': profile.selectedTrades,
                    'profileImage': profile.profileImage,
                    'createdDate': profile.createdDate.isoformat() if profile.createdDate else None,
                    'isActive': profile.isActive,
                    'isDeleted': profile.isDeleted,
                    'userId': profile.userId
                }
                profile_list.append(profile_data)
            return {"profiles": profile_list}, 200
        except Exception as e:
            return {"error": f"Failed to get all profiles: {str(e)}"}, 500
