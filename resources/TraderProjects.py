from flask_restful import Resource
from flask import request
from util.gcs_handler import GCSHandler
from models.TraderProject import TraderProject
import json
import uuid
from datetime import datetime

class SaveTraderProject(Resource):
    def post(self):
        try:
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('projectImages')))
            
            # Generate unique project ID
            project_id = str(uuid.uuid4())
            print(f"Generated project ID: {project_id}")
            
            # Get form data
            form_data = {}
            for key in request.form:
                form_data[key] = request.form[key]
            
            # Extract userId from form data (sent from frontend auth)
            user_id = form_data.get('userId')
            if not user_id:
                return {"error": "userId is required"}, 400
            
            # Add project metadata
            form_data['project_id'] = project_id
            form_data['user_id'] = user_id
            form_data['created_at'] = datetime.utcnow().isoformat()
            
            print(f"Using userId: {user_id} for bucket organization")
            
            # Handle multiple file uploads using Google Cloud Storage
            project_images = request.files.getlist('projectImages')
            image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(project_images)} images for user: {user_id}')
                    
                    for image in project_images:
                        if image and image.filename != '':
                            try:
                                # Generate unique filename to prevent conflicts
                                file_extension = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else 'jpg'
                                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                                
                                # Use existing upload_profile_image method with userId from auth
                                file_url = gcs_handler.upload_profile_image(
                                    file=image,
                                    user_id=user_id,
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
            form_data['projectImages'] = image_urls
            
            print('Final form data:', {
                'project_id': project_id,
                'user_id': user_id,
                'image_count': len(image_urls)
            })
            
            # Save project data to database using the TraderProject model
            try:
                # Create TraderProject object
                trader_project = TraderProject(
                    project_id=project_id,
                    userId=user_id,
                    projectTitle=form_data.get('projectTitle', ''),
                    projectDescription=form_data.get('projectDescription', ''),
                    specifications=form_data.get('specifications', '').split(',') if form_data.get('specifications') else [],
                    location=form_data.get('location', ''),
                    budget=form_data.get('budget', ''),
                    timeline=form_data.get('timeline', ''),
                    projectImages=image_urls,
                    createdDate=datetime.utcnow()
                )
                
                trader_project.save()
                
                print(f'Trader project saved to database successfully with ID: {project_id}')
                
                # Return the saved project data
                return {
                    "success": True,
                    "message": "Trader project created and saved successfully!",
                    "project_id": project_id,
                    "database_id": str(trader_project.id),
                    "user_id": user_id,
                    "data": {
                        "project_id": project_id,
                        "userId": user_id,
                        "projectTitle": trader_project.projectTitle,
                        "projectDescription": trader_project.projectDescription,
                        "specifications": trader_project.specifications,
                        "location": trader_project.location,
                        "budget": trader_project.budget,
                        "timeline": trader_project.timeline,
                        "projectImages": trader_project.projectImages,
                        "createdDate": trader_project.createdDate.isoformat()
                    },
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
            print(f"Error creating trader project: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to create trader project: {str(e)}"}, 500
        
    def get(self):
        try:
            projects = TraderProject.objects()
            return {"success": True, "projects": projects}, 200
        except Exception as e:
            print(f"Error fetching trader projects: {str(e)}")
            return {"error": f"Failed to fetch trader projects: {str(e)}"}, 500
        
        