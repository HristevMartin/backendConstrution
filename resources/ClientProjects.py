from flask import request
from werkzeug.datastructures import FileStorage
from flask_restful import Resource
from util.gcs_handler import GCSHandler
from util.email_service import EmailService
from models.ClientProject import ClientProject
import json
import uuid
import requests
from datetime import datetime
from managers.auth import auth, _get_token_from_request
from models.user import Users
from models.TraderProject import TraderProject
from services.recommendation_engine import ProjectRecommendationEngine
from services.recommendation_engine import UserService
from models.UserTracker import ClientUserCompletedJobs


def fetch_nuts_from_postcode(postcode):
    """
    Fetch NUTS (Nomenclature of Territorial Units for Statistics) information from postcodes.io API
    Returns the NUTS area if found, otherwise returns 'London' as fallback
    """
    try:
        # Clean the postcode (remove spaces and convert to uppercase)
        clean_postcode = postcode.replace(' ', '').upper()
        
        # Call the postcodes.io API
        url = f"https://api.postcodes.io/postcodes/{clean_postcode}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('result'):
                nuts = data['result'].get('nuts')
                if nuts:
                    print(f"Successfully fetched NUTS area: {nuts} for postcode: {postcode}")
                    return nuts
                else:
                    print(f"No NUTS found in API response for postcode: {postcode}, using fallback 'London'")
                    return 'London'
            else:
                print(f"API returned error status for postcode: {postcode}, using fallback 'London'")
                return 'London'
        else:
            print(f"Failed to fetch NUTS for postcode: {postcode}. Status code: {response.status_code}, using fallback 'London'")
            return 'London'
            
    except Exception as e:
        print(f"Error fetching NUTS for postcode {postcode}: {str(e)}, using fallback 'London'")
        return 'London'

class ClientProjects(Resource):
    @auth.login_required
    def post(self):
        try:
            project_id = str(uuid.uuid4())
            print(f"Generated project ID: {project_id}")

            token = _get_token_from_request()
            if not token:
                return {"error": "Token is required"}, 401

            user_id = auth.current_user().id
            print(f"User ID: {user_id}")

            user = Users.objects(id=user_id).first()
            if not user:
                return {"error": "User not found"}, 404
            
            user_email = user.email
            print(f"User email: {user_email}")
            
            # Get form data
            form_data = {}
            for key in request.form:
                form_data[key] = request.form[key]
            

            form_data['email'] = user_email
            # Extract userId from form data (sent from frontend auth)
            user_id = form_data.get('userId')
            if not user_id:
                return {"error": "userId is required"}, 400
            
            form_data['project_id'] = project_id
            form_data['user_id'] = user_id
            form_data['created_at'] = datetime.utcnow().isoformat()
            
            print(f"Using userId: {user_id} for bucket organization")
            
            # Handle multiple file usploads using Google Cloud Storage (optional)
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
                print("No images provided - creating project without images")
            
            # Add image URLs to form data
            form_data['image_urls'] = image_urls
            
            # Handle location logic based on new UI flow
            location = form_data.get('location', '').strip()
            postcode = form_data.get('postcode', '').strip()
            area = form_data.get('area', '').strip()
            
            # If area is provided (non-London location), use it as the location
            if area and not location:
                form_data['location'] = area
                location = area
                print(f"Using area as location: {area}")
            
            # Check if location is London and fetch NUTS area from postcode
            if location.lower() == 'london' and postcode:
                print(f"Location is London and postcode provided: {postcode}")
                nuts = fetch_nuts_from_postcode(postcode)
                form_data['nuts'] = nuts
                form_data['postcode'] = postcode
                print(f"Added NUTS area to form data: {nuts}")
            elif location.lower() == 'london' and not postcode:
                print(f"Location is London but no postcode provided, using fallback 'London'")
                form_data['nuts'] = 'London'
            else:
                # For non-London locations, use the area/location as nuts
                print(f"Non-London location: {location}")
                form_data['nuts'] = location or area or ''
                # Clear postcode for non-London locations if not provided
                if not postcode:
                    form_data['postcode'] = ''
            
 
            try:
                project = ClientProject.create_project(form_data, image_urls)
                project.save()

                client_tracker = ClientUserCompletedJobs(
                id=str(uuid.uuid4()),
                userId=project.user_id,
                jobId=project.project_id,
                completed_jobs=0,
                cancelled_jobs=0,
                posted_jobs=1,
                last_completed_at=datetime.utcnow(),
                first_posted_at=datetime.utcnow(),
                response_rate=0,
                reliable=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
                )
                
                client_tracker.save()

                print('its passing here')
                
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
        print(f"User ID: {user_id}")
        if not user_id:
            return {"error": "user_id is required"}, 400
        
        projects = ClientProject.objects(user_id=user_id, is_deleted=False)
        projects_list = [project.to_dict() for project in projects]
        
        return {
            "success": True,
            "projects": projects_list
        }, 200


class GetClientProject(Resource):
    def get(self, project_id):
        """Get a specific client project by project_id"""
        try:
            print('show me what is the project id', project_id)
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
        
        
    def delete(self, project_id):
        """Delete a specific client project by project_id"""
        try:
            project = ClientProject.get_by_project_id(project_id)
            if not project:
                return {"error": "Project not found"}, 404
            project.delete()
            return {"success": True, "message": "Project deleted successfully"}, 200
        except Exception as e:
            print(f"Error deleting project {project_id}: {str(e)}")
            return {"error": f"Failed to delete project: {str(e)}"}, 500


class EditClientProject(Resource):
    def put(self, project_id):
        """Edit a specific client project by project_id"""
        try:
            if request.is_json:
                data = request.get_json()
            else:
                # Handle form data
                data = {}
                for key in request.form:
                    data[key] = request.form[key]
            
            print(f"===== EDIT PROJECT DEBUG =====")
            print(f"Project ID: {project_id}")
            print(f"Incoming data keys: {list(data.keys())}")
            print(f"Full incoming data: {data}")
            print(f"==============================")
            
            # Extract userId from form data (sent from frontend auth)
            user_id = data.get('userId')
            if not user_id:
                return {"error": "userId is required for editing"}, 400
            
            print(f"Using userId: {user_id} for bucket organization")
            
            project = ClientProject.get_by_project_id(project_id)

            if not project:
                return {"error": "Project not found"}, 404
            
            # Update fields if provided (skip empty strings to preserve existing data)
            print(f"Before update - Current location: {project.location}")
            print(f"Before update - Current job_title: {project.job_title}")
            print(f"Before update - Current first_name: {project.first_name}")
            print(f"Before update - Current email: {project.email}")
            
            if 'first_name' in data and data['first_name']:  # Only update if not empty
                project.first_name = data['first_name']
                print(f"Updated first_name: {data['first_name']}")
            if 'email' in data and data['email']:  # Only update if not empty
                project.email = data['email']
                print(f"Updated email: {data['email']}")
            if 'phone' in data and data['phone']:  # Only update if not empty
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
            if 'postcode' in data:
                project.postcode = data['postcode']
                print(f"Updated postcode: {data['postcode']}")
                
                # If location is London, fetch NUTS area from postcode
                if project.location and project.location.lower() == 'london' and data['postcode']:
                    print(f"Location is London and postcode updated: {data['postcode']}")
                    nuts = fetch_nuts_from_postcode(data['postcode'])
                    project.nuts = nuts
                    print(f"Updated NUTS area: {nuts}")
                        
            if 'nuts' in data:
                project.nuts = data['nuts']
                print(f"Updated nuts: {data['nuts']}")
            if 'budget' in data:
                project.budget = data['budget']
                print(f"Updated budget: {data['budget']}")
            if 'urgency' in data:
                project.urgency = data['urgency']
                print(f"Updated urgency: {data['urgency']}")
            if 'status' in data:
                project.status = data['status']
                print(f"Updated status: {data['status']}")
                
                # Update ClientUserCompletedJobs if status is completed
                if data['status'].lower() == 'completed':
                    try:
                        client_tracker = ClientUserCompletedJobs.objects(jobId=project_id).first()
                        if client_tracker:
                            client_tracker.completed_jobs = 1
                            client_tracker.cancelled_jobs = 0
                            client_tracker.posted_jobs = 0
                            client_tracker.last_completed_at = datetime.utcnow()
                            client_tracker.updated_at = datetime.utcnow()
                            client_tracker.save()
                            print(f"Marked job {project_id} as completed in ClientUserCompletedJobs")
                        else:
                            print(f"No ClientUserCompletedJobs record found for job {project_id}")
                    except Exception as e:
                        print(f"Error updating ClientUserCompletedJobs: {str(e)}")
                
                # Update ClientUserCompletedJobs if status is cancelled
                elif data['status'].lower() == 'cancelled':
                    try:
                        client_tracker = ClientUserCompletedJobs.objects(jobId=project_id).first()
                        if client_tracker:
                            client_tracker.cancelled_jobs = 1
                            client_tracker.completed_jobs = 0
                            client_tracker.posted_jobs = 0
                            client_tracker.updated_at = datetime.utcnow()
                            client_tracker.save()
                            print(f"Marked job {project_id} as cancelled in ClientUserCompletedJobs")
                        else:
                            print(f"No ClientUserCompletedJobs record found for job {project_id}")
                    except Exception as e:
                        print(f"Error updating ClientUserCompletedJobs: {str(e)}")

                        
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
                'postcode': 'postcode',  # Keep as is since it's already camelCase
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
            
            print('ive been called here')
            
            # Handle image uploads (like in save endpoint)
            project_images = request.files.getlist('new_images')
            new_image_urls = []
            
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    
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
            
            # Handle image deletion first
            images_to_delete = data.get('images_to_delete', '')
            if images_to_delete:
                # Handle both single image (string) and multiple images (comma-separated)
                if isinstance(images_to_delete, str):
                    delete_urls = [url.strip() for url in images_to_delete.split(',') if url.strip()]
                else:
                    delete_urls = images_to_delete if isinstance(images_to_delete, list) else []
                
                # Delete images from Google Cloud Storage first
                try:
                    gcs_handler = GCSHandler()
                    for image_url in delete_urls:
                        try:
                            # Use the existing delete_file method which handles URL parsing
                            deletion_success = gcs_handler.delete_file(image_url)
                            if deletion_success:
                                print(f"Successfully deleted from GCS: {image_url}")
                            else:
                                print(f"Failed to delete from GCS: {image_url}")
                        except Exception as e:
                            print(f"Error deleting image from GCS {image_url}: {str(e)}")
                            # Continue with other deletions even if one fails
                            continue
                except Exception as e:
                    print(f"Error initializing GCS handler for deletion: {str(e)}")
                    # Continue with database update even if GCS deletion fails

                existing_images = project.image_urls or []
                # Remove images that are in the delete list from database
                project.image_urls = [url for url in existing_images if url not in delete_urls]
                print(f"Deleted {len(delete_urls)} images from database: {delete_urls}")
                print(f"Remaining images: {len(project.image_urls)}")

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
            else:
                # Update image count even if no new images (in case of deletions)
                project.image_count = len(project.image_urls or [])
            
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








    def delete(self, project_id):
        """Delete a specific client project by project_id"""
        try:
            project = ClientProject.get_by_project_id(project_id)

            print('show me in here what is the project id', project_id)
            client_tracker = ClientUserCompletedJobs.objects(jobId=project_id).first()
            print('show me in here what is the client tracker', client_tracker)
            client_tracker.cancelled_jobs += 1
            client_tracker.posted_jobs -= 1
            client_tracker.save()

            project.delete()

            return {"success": True, "message": "Project deleted successfully"}, 200
        except Exception as e:
            print(f"Error deleting project {project_id}: {str(e)}")
            return {"error": f"Failed to delete project: {str(e)}"}, 500


class DeleteClientProjectId(Resource):
    def delete(self, project_id):
        """Soft delete a specific client project by project_id"""
        try:
            project = ClientProject.objects(project_id=project_id).first()
            if not project:
                return {"error": "Project not found"}, 404
            
            project.is_deleted = True
            project.save()
            
            return {"success": True, "message": "Project deleted successfully"}, 200
        except Exception as e:
            print(f"Error deleting project {project_id}: {str(e)}")
            return {"error": f"Failed to delete project: {str(e)}"}, 500



class GetAllClientProjects(Resource):
    @auth.login_required
    def get(self):
        try:
            
            token = _get_token_from_request()
            if not token:
                return {"error": "Token is required"}, 401

            toggle = request.args.get('toggle', 'off')

            user_id = auth.current_user().id  
            trader_user_id = Users.objects(id=user_id).first().id

            trader_user_profile_id = TraderProject.objects(userId=str(trader_user_id)).first()

            if not trader_user_profile_id:
                return {"error": "Trader profile not found"}, 404
                
            user_postcode = trader_user_profile_id.postcode

            
            if not token or token == 'null' or token == 'undefined' or token.strip() == '':
                return {"error": "Valid token is required. Token cannot be null, undefined, or empty."}, 401

            
            projects = ClientProject.objects(is_deleted=False)
            projects_list = [project.to_dict() for project in projects]
            
            if toggle == 'on':
                res = self.get_recommendations(trader_user_profile_id, projects_list)
            else:
                res = projects_list

            return {
                "success": True,
                "projects": res,
                "message": "Client projects retrieved successfully"
            }, 200
            
        except Exception as e:
            print(f"Error in GetAllClientProjects: {str(e)}")
            return {"error": f"Failed to retrieve client projects: {str(e)}"}, 500


    def get_recommendations(self, trader_user_profile_id, projects_list):
        print('in here get_recommendations')
        recommendation_engine = ProjectRecommendationEngine()
        user_service = UserService()

        user_preferences = user_service.get_user_preferences(trader_user_profile_id)

        user_postcode = trader_user_profile_id.postcode 

        recommendations = recommendation_engine.get_user_recommendations(
        user_postcode, 
        projects_list,
        user_preferences
        )
        
        return recommendations['immediate_nearby']