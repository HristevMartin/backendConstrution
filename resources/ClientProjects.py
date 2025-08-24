from flask import request
from werkzeug.datastructures import FileStorage
from flask_restful import Resource
from util.gcs_handler import GCSHandler
from util.email_service import EmailService
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
            project_images = request.files.getlist('images')
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
                
                # Send confirmation emails
                try:
                    email_service = EmailService()
                    project_dict = project.to_dict()
                    
                    # Send confirmation email to client
                    client_email_sent = email_service.send_project_confirmation_email(project_dict)
                    
                    # Send notification email to admin/team
                    admin_email_sent = email_service.send_admin_notification_email(project_dict)
                    
                    email_status = {
                        "client_email_sent": client_email_sent,
                        "admin_email_sent": admin_email_sent
                    }
                    
                    if client_email_sent:
                        print(f"Confirmation email sent to client: {project.email}")
                    else:
                        print(f"Failed to send confirmation email to client: {project.email}")
                    
                    if admin_email_sent:
                        print("Admin notification email sent successfully")
                    else:
                        print("Failed to send admin notification email")
                        
                except Exception as email_error:
                    print(f"Error sending emails: {str(email_error)}")
                    email_status = {
                        "client_email_sent": False,
                        "admin_email_sent": False,
                        "email_error": str(email_error)
                    }
                
                # Return the saved project data
                return {
                    "success": True,
                    "message": "Project created and saved successfully! Check your email for confirmation.",
                    "project_id": project.project_id,
                    "database_id": str(project.id),
                    "data": project.to_dict(),
                    "images_uploaded": len(image_urls),
                    "image_urls": image_urls,
                    "email_status": email_status
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

    def get(self):
        user_id = request.args.get('user_id')
        if not user_id:
            return {"error": "user_id is required"}, 400
        
        projects = ClientProject.objects(user_id=user_id)
        projects_list = [project.to_dict() for project in projects]
        
        return {
            "success": True,
            "projects": projects_list
        }, 200


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


class EditClientProject(Resource):
    def put(self, project_id):
        """Edit a specific client project by project_id"""
        try:
            print(f"Editing project {project_id}")
            print(f"Request content type: {request.content_type}")
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('new_images')))
            
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                print("JSON data received:", data)
            else:
                # Handle form data
                data = {}
                for key in request.form:
                    data[key] = request.form[key]
                print("Form data received:", data)
            
            # Extract userId from form data (sent from frontend auth)
            user_id = data.get('userId')
            if not user_id:
                return {"error": "userId is required for editing"}, 400
            
            print(f"Using userId: {user_id} for bucket organization")
            
            project = ClientProject.get_by_project_id(project_id)

            if not project:
                return {"error": "Project not found"}, 404
            
            # Update fields if provided
            print(f"Before update - Current location: {project.location}")
            print(f"Before update - Current job_title: {project.job_title}")
            
            if 'first_name' in data:
                project.first_name = data['first_name']
                print(f"Updated first_name: {data['first_name']}")
            if 'email' in data:
                project.email = data['email']
                print(f"Updated email: {data['email']}")
            if 'phone' in data:
                project.phone = data['phone']
                print(f"Updated phone: {data['phone']}")
            if 'contact_method' in data:
                project.contact_method = data['contact_method']
                print(f"Updated contact_method: {data['contact_method']}")
            if 'job_title' in data:
                project.job_title = data['job_title']
                print(f"Updated job_title: {data['job_title']}")
            # Handle the typo case
            if 'ob_title' in data:
                project.job_title = data['ob_title']
                print(f"Updated job_title from ob_title: {data['ob_title']}")
            if 'job_description' in data:
                project.job_description = data['job_description']
                print(f"Updated job_description: {data['job_description']}")
            if 'location' in data:
                project.location = data['location']
                print(f"Updated location: {data['location']}")
            if 'budget' in data:
                project.budget = data['budget']
                print(f"Updated budget: {data['budget']}")
            if 'urgency' in data:
                project.urgency = data['urgency']
                print(f"Updated urgency: {data['urgency']}")
            if 'status' in data:
                project.status = data['status']
                print(f"Updated status: {data['status']}")
            if 'country' in data:
                project.country = data['country']
                print(f"Updated country: {data['country']}")
            if 'service_category' in data:
                project.service_category = data['service_category']
                print(f"Updated service_category: {data['service_category']}")
            if 'gdpr_consent' in data:
                project.gdpr_consent = data.get('gdpr_consent') == 'true' or data.get('gdpr_consent') == True
                print(f"Updated gdpr_consent: {project.gdpr_consent}")
            
            # Also update additional_data field (client consumes from here)
            if not project.additional_data:
                project.additional_data = {}
            
            # Field mapping for camelCase conversion in additional_data
            field_mapping = {
                'service_category': 'serviceCategory',
                'job_title': 'jobTitle',
                'job_description': 'jobDescription',
                'first_name': 'firstName',
                'contact_method': 'contactMethod',
                'gdpr_consent': 'gdprConsent',
                'ob_title': 'jobTitle'  # Handle typo case
            }
            
            # Update additional_data with proper field names
            for key, value in data.items():
                if key not in ['existing_images', 'total_images_count', 'replaceImages']:
                    # Use mapped field name if exists, otherwise use original key
                    mapped_key = field_mapping.get(key, key)
                    project.additional_data[mapped_key] = value
                    print(f"Updated additional_data['{mapped_key}']: {value}")
                    
                    # Also update with original key for backward compatibility
                    if mapped_key != key:
                        project.additional_data[key] = value
                        print(f"Updated additional_data['{key}']: {value} (compatibility)")
            
            print(f"After update - New location: {project.location}")
            print(f"After update - New job_title: {project.job_title}")
            print(f"Updated additional_data: {project.additional_data}")
            
            # Handle image uploads (like in save endpoint)
            project_images = request.files.getlist('new_images')
            new_image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(project_images)} new images for user: {user_id}')
                    
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
                                    new_image_urls.append(file_url)
                                    print(f"Image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler: {str(e)}")
                    return {"error": "Failed to initialize cloud storage"}, 500
            
            # Handle image update strategy
            replace_images = data.get('replaceImages', 'false').lower() == 'true'
            
            if replace_images and new_image_urls:
                # Replace all existing images with new ones
                project.image_urls = new_image_urls
                project.image_count = len(new_image_urls)
                print(f"Replaced all images with {len(new_image_urls)} new images")
            elif new_image_urls:
                # Add new images to existing ones
                existing_images = project.image_urls or []
                project.image_urls = existing_images + new_image_urls
                project.image_count = len(project.image_urls)
                print(f"Added {len(new_image_urls)} new images to existing {len(existing_images)} images")
            
            # Save the updated project
            project.save()
            
            print(f"Project {project_id} updated successfully")
            
            return {
                "success": True,
                "message": "Project updated successfully",
                "project": project.to_dict(),
                "new_images_uploaded": len(new_image_urls),
                "total_images": len(project.image_urls or [])
            }, 200
        except Exception as e:
            print(f"Error editing project {project_id}: {str(e)}")
            return {"error": f"Failed to edit project: {str(e)}"}, 500

