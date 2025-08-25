from flask_restful import Resource
from flask import request
from models.TraderProject import Project
import json
import os
import uuid
from werkzeug.utils import secure_filename
from util.gcs_handler import GCSHandler
from models.TraderProfile import TraderProfile
from bson import ObjectId

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

class UpdateProject(Resource):
    def put(self, project_id):
        try:
            print(f"Updating project with ID: {project_id}")
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('projectImages')))
            
            # Find the existing project
            try:
                project = Project.objects(userId=project_id).first()
                print('showing project', project)
            except:
                return {"error": "Invalid project ID format"}, 400
            
            if not project:
                return {"error": "Project not found"}, 404
            
            # Get form data for updates
            data = {}
            
            # Update fields if provided
            if request.form.get('title'):
                data['title'] = request.form.get('title', '').strip()
                project.title = data['title']
            
            if request.form.get('description'):
                data['description'] = request.form.get('description', '').strip()
                project.description = data['description']
                
            if request.form.get('projectDate'):
                data['projectDate'] = request.form.get('projectDate', '').strip()
                project.projectDate = data['projectDate']
            
            # Handle specifications update
            specifications_str = request.form.get('specifications')
            if specifications_str:
                print(f"Raw specifications received: {specifications_str}")
                try:
                    specifications = json.loads(specifications_str)
                    project.specifications = specifications
                    print(f"Parsed specifications: {specifications}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing specifications JSON: {e}")
            
            # Handle image uploads (add to existing images or replace them)
            project_images = request.files.getlist('projectImages')
            new_image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    user_id = project.userId or 'unknown_user'
                    
                    print(f'Uploading {len(project_images)} new project images for user: {user_id}')
                    
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
                                    new_image_urls.append(file_url)
                                    print(f"Project image uploaded successfully to GCS: {file_url}")
                                else:
                                    print(f"Failed to upload project image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading project image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler: {str(e)}")
                    return {"error": "Failed to initialize cloud storage"}, 500
            
            # Handle image update strategy
            replace_images = request.form.get('replaceImages', 'false').lower() == 'true'
            
            if replace_images:
                # Replace all existing images with new ones
                project.projectImages = new_image_urls
                print(f"Replaced all images with {len(new_image_urls)} new images")
            else:
                # Add new images to existing ones
                if new_image_urls:
                    existing_images = project.projectImages or []
                    project.projectImages = existing_images + new_image_urls
                    print(f"Added {len(new_image_urls)} new images to existing {len(existing_images)} images")
            
            # Save the updated project
            project.save()
            
            print('Project updated successfully:', {
                'title': project.title,
                'description': project.description[:50] + '...' if project.description and len(project.description) > 50 else project.description,
                'projectDate': project.projectDate,
                'specifications': project.specifications,
                'total_images': len(project.projectImages or [])
            })
            
            # Return updated project data
            project_data = {
                'id': str(project.id),
                'title': project.title,
                'description': project.description,
                'projectDate': project.projectDate,
                'specifications': project.specifications,
                'projectImages': project.projectImages,
                'userId': project.userId,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
            }
            
            return {
                "message": "Project updated successfully",
                "project": project_data,
                "new_images_added": len(new_image_urls)
            }, 200
            
        except Exception as e:
            print(f"Error updating project: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to update project: {str(e)}"}, 500
        
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