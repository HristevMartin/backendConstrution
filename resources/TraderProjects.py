from flask import request
from flask_restful import Resource
from models.TraderProject import TraderProject
from util.gcs_handler import GCSHandler
from util.email_service import EmailService
import uuid
from datetime import datetime
from resources.auth import auth, _get_token_from_request
from models.user import Users

class SaveTraderProject(Resource):
    @auth.login_required
    def post(self):
        try:
            
            token = _get_token_from_request()

            if not token:
                return {"error": "Token is required"}, 401
            
            user_id = auth.current_user().id
            if not user_id:
                return {"error": "User ID is required"}, 401

            user = Users.objects(id=user_id).first()
            if not user:
                return {"error": "User not found"}, 404

            user_email = user.email
            print(f"User email: {user_email}")
            
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

            form_data['email'] = user_email
            
            # Validate required trader registration fields
            required_fields = ['name', 'email', 'primaryTrade', 'city', 'postcode', 'radiusKm', 'marketingConsent']
            missing_fields = [field for field in required_fields if not form_data.get(field)]
            if missing_fields:
                return {"error": f"Missing required fields: {', '.join(missing_fields)}"}, 400
            
            # Add project metadata
            form_data['project_id'] = project_id
            form_data['user_id'] = user_id
            form_data['created_at'] = datetime.utcnow().isoformat()
            
            print(f"Using userId: {user_id} for bucket organization")
            
            # Handle multiple file uploads using Google Cloud Storage (if any)
            project_images = request.files.getlist('projectImages') if request.files else []
            certification_images = request.files.getlist('certificationImages') if request.files else []
            image_urls = []
            certification_urls = []
            
            # Upload project images
            if project_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(project_images)} project images for user: {user_id}')
                    
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
                                    print(f"Project image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload project image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading project image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler for project images: {str(e)}")
                    # Continue without images if GCS fails
                    image_urls = []
            
            # Upload certification images
            if certification_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(certification_images)} certification images for user: {user_id}')
                    
                    for image in certification_images:
                        if image and image.filename != '':
                            try:
                                # Generate unique filename to prevent conflicts
                                file_extension = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else 'jpg'
                                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                                
                                # Use existing upload_profile_image method with userId from auth
                                file_url = gcs_handler.upload_profile_image(
                                    file=image,
                                    user_id=user_id,
                                    file_type='certification_pictures'
                                )
                                
                                if file_url:
                                    certification_urls.append(file_url)
                                    print(f"Certification image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload certification image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading certification image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler for certification images: {str(e)}")
                    # Continue without images if GCS fails
                    certification_urls = []
            
            # Add image URLs to form data
            form_data['projectImages'] = image_urls
            form_data['certificationImages'] = certification_urls
            
            try:
                # Create TraderProject object with trader registration data
                trader_project = TraderProject(
                    project_id=project_id,
                    userId=user_id,
                    name=form_data.get('name'),
                    email=form_data.get('email'),
                    phone=form_data.get('phone', ''),
                    primaryTrade=form_data.get('primaryTrade'),
                    otherServices=form_data.get('otherServices', ''),
                    city=form_data.get('city'),
                    postcode=form_data.get('postcode'),
                    radiusKm=form_data.get('radiusKm'),
                    experienceYears=form_data.get('experienceYears', '0'),
                    certifications=form_data.get('certifications', ''),
                    bio=form_data.get('bio', ''),
                    marketingConsent=form_data.get('marketingConsent'),
                    projectImages=image_urls,
                    certificationImages=certification_urls,
                    createdDate=datetime.utcnow()
                )
                
                trader_project.save()
                
                # Send confirmation email to trader
                try:
                    email_service = EmailService()
                    
                    # Prepare trader data for email
                    trader_email_data = {
                        'project_id': project_id,
                        'name': form_data.get('name'),
                        'email': form_data.get('email'),
                        'primaryTrade': form_data.get('primaryTrade'),
                        'city': form_data.get('city')
                    }
                    
                    # Send trader confirmation email
                    email_service.send_trader_registration_email(trader_email_data)
                    
                    # Send admin notification email
                    admin_email_data = {
                        'project_id': project_id,
                        'name': form_data.get('name'),
                        'email': form_data.get('email'),
                        'phone': form_data.get('phone', 'Not provided'),
                        'primaryTrade': form_data.get('primaryTrade'),
                        'city': form_data.get('city'),
                        'postcode': form_data.get('postcode'),
                        'radiusKm': form_data.get('radiusKm'),
                        'experienceYears': form_data.get('experienceYears', '0'),
                        'certifications': form_data.get('certifications', ''),
                        'bio': form_data.get('bio', 'No bio provided'),
                        'marketingConsent': form_data.get('marketingConsent')
                    }
                    
                    print('its being called in here', admin_email_data)

                    email_service.send_trader_admin_notification_email(admin_email_data)
                    
                except Exception as email_error:
                    print(f"Error sending emails: {str(email_error)}")
                    # Continue even if emails fail
                
                # Return the saved trader registration data
                return {
                    "success": True,
                    "message": "Trader registration completed successfully!",
                    "project_id": project_id,
                    "database_id": str(trader_project.id),
                    "user_id": user_id,
                    "data": {
                        "project_id": project_id,
                        "userId": user_id,
                        "name": trader_project.name,
                        "email": trader_project.email,
                        "phone": trader_project.phone,
                        "primaryTrade": trader_project.primaryTrade,
                        "otherServices": trader_project.otherServices,
                        "city": trader_project.city,
                        "postcode": trader_project.postcode,
                        "radiusKm": trader_project.radiusKm,
                        "experienceYears": trader_project.experienceYears,
                        "certifications": trader_project.certifications,
                        "bio": trader_project.bio,
                        "marketingConsent": trader_project.marketingConsent,
                        "projectImages": trader_project.projectImages,
                        "certificationImages": trader_project.certificationImages,
                        "createdDate": trader_project.createdDate.isoformat()
                    },
                    "images_uploaded": len(image_urls),
                    "image_urls": image_urls,
                    "certification_images_uploaded": len(certification_urls),
                    "certification_urls": certification_urls
                }, 201
                
            except Exception as db_error:
                print(f"Error saving to database: {str(db_error)}")
                return {
                    "success": False,
                    "message": "Trader registration failed to save to database",
                    "error": str(db_error),
                    "project_id": project_id
                }, 500
            
        except Exception as e:
            print(f"Error creating trader registration: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to create trader registration: {str(e)}"}, 500
    
    def get(self, user_id):
        try:
            projects = TraderProject.objects(userId=user_id)
            projects_list = [project.to_dict() for project in projects]
            return {"success": True, "projects": projects_list}, 200
        except Exception as e:
            print(f"Error fetching trader projects: {str(e)}")
            return {"error": f"Failed to fetch trader projects: {str(e)}"}, 500
    
    def put(self, project_id):
        try:
            data = request.get_json()
            project = TraderProject.objects(project_id=project_id).first()
            if not project:
                return {"error": "Project not found"}, 404
            project.update(**data)
            return {"success": True, "project": project.to_dict()}, 200
        except Exception as e:
            print(f"Error updating trader project: {str(e)}")
            return {"error": f"Failed to update trader project: {str(e)}"}, 500


class GetTraderProject(Resource):
    def get(self, user_id):
        print('User ID:', user_id)
        print('Project ID:', user_id)
        try:
            project = TraderProject.objects(userId=user_id).first()
            if not project:
                return {"success": True, "project": None, "message": "No project found for this user"}, 200
            return {"success": True, "project": project.to_dict()}, 200
        except Exception as e:
            print(f"Error fetching trader project: {str(e)}")
            return {"error": f"Failed to fetch trader project: {str(e)}"}, 500
        
    def put(self, user_id):
        try:
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('projectImages')) if request.files else 0)
            
            # Get form data
            form_data = {}
            for key in request.form:
                form_data[key] = request.form[key]
            
            # Get JSON data if present
            json_data = request.get_json() if request.is_json else {}
            
            # Combine form data and JSON data
            update_data = {**form_data, **json_data}
            
            # Filter out fields that don't exist in the TraderProject model
            valid_fields = [
                'name', 'email', 'phone', 'primaryTrade', 'otherServices', 'city', 
                'postcode', 'radiusKm', 'experienceYears', 'certifications', 'bio', 
                'marketingConsent', 'projectTitle', 'projectDescription', 'location', 
                'budget', 'timeline', 'specifications', 'projectImages', 'certificationImages', 'replace_images',
                'existing_portfolio_images'
            ]
            
            # Only include valid fields in the update
            filtered_update_data = {k: v for k, v in update_data.items() if k in valid_fields}
            
            # Find the project to update
            project = TraderProject.objects(userId=user_id).first()
            if not project:
                return {"error": "Project not found"}, 404
            
            # Handle image uploads if any
            project_images = request.files.getlist('projectImages') if request.files else []
            portfolio_images = request.files.getlist('portfolio_image') if request.files else []
            certification_images = request.files.getlist('certificationImages') if request.files else []
            
            # Combine all image files
            all_images = project_images + portfolio_images
            image_urls = []
            certification_urls = []
            
            # Upload project/portfolio images
            if all_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(all_images)} project/portfolio images for user: {user_id}')
                    
                    for image in all_images:
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
                                    print(f"Project/portfolio image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload project/portfolio image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading project/portfolio image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler for project/portfolio images: {str(e)}")
                    # Continue without images if GCS fails
                    image_urls = []
            
            # Upload certification images
            if certification_images:
                try:
                    # Initialize GCS handler
                    gcs_handler = GCSHandler()
                    
                    print(f'Uploading {len(certification_images)} certification images for user: {user_id}')
                    
                    for image in certification_images:
                        if image and image.filename != '':
                            try:
                                # Generate unique filename to prevent conflicts
                                file_extension = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else 'jpg'
                                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                                
                                # Use existing upload_profile_image method with userId from auth
                                file_url = gcs_handler.upload_profile_image(
                                    file=image,
                                    user_id=user_id,
                                    file_type='certification_pictures'
                                )
                                
                                if file_url:
                                    certification_urls.append(file_url)
                                    print(f"Certification image uploaded successfully: {file_url}")
                                else:
                                    print(f"Failed to upload certification image: {image.filename}")
                                    
                            except Exception as e:
                                print(f"Error uploading certification image {image.filename}: {str(e)}")
                                continue
                                
                except Exception as e:
                    print(f"Error initializing GCS handler for certification images: {str(e)}")
                    # Continue without images if GCS fails
                    certification_urls = []
            
            # Handle existing portfolio images (URLs)
            existing_portfolio_images = form_data.get('existing_portfolio_images', '')
            if existing_portfolio_images:
                # If it's a single URL, convert to list
                if isinstance(existing_portfolio_images, str):
                    existing_images_list = [existing_portfolio_images] if existing_portfolio_images else []
                else:
                    existing_images_list = existing_portfolio_images
                
                # Add existing images to the update data
                filtered_update_data['projectImages'] = existing_images_list
                
                # If we have new uploaded images, append them
                if image_urls:
                    filtered_update_data['projectImages'] = existing_images_list + image_urls
            elif image_urls:
                # Only new uploaded images
                filtered_update_data['projectImages'] = image_urls
            
            # Handle certification images
            if certification_urls:
                # If replace_images is true, replace all certification images; otherwise append
                if filtered_update_data.get('replace_images', 'false').lower() == 'true':
                    filtered_update_data['certificationImages'] = certification_urls
                else:
                    # Append new certification images to existing ones
                    existing_certification_images = project.certificationImages or []
                    filtered_update_data['certificationImages'] = existing_certification_images + certification_urls
            
            # Remove existing_portfolio_images from update data since it's not a database field
            filtered_update_data.pop('existing_portfolio_images', None)
            
            # Update the project
            project.update(**filtered_update_data)
            
            # Reload the project to get updated data
            project.reload()
            
            return {
                "success": True, 
                "message": "Project updated successfully",
                "project": project.to_dict(),
                "images_uploaded": len(image_urls) if image_urls else 0,
                "certification_images_uploaded": len(certification_urls) if certification_urls else 0
            }, 200
            
        except Exception as e:
            print(f"Error updating trader project: {str(e)}")
            return {"error": f"Failed to update trader project: {str(e)}"}, 500


class GetTraderRoles(Resource):
    def get(self, user_id):
        try:
            project = TraderProject.objects(userId=user_id).first()
            
            if not project:
                return {"success": True, "project": None, "message": "No project found for this user"}, 200
            
            primary_trade = project.primaryTrade
            print('show me the primary_trade', primary_trade)


            return {"success": True, "specialty": primary_trade}, 200
        except Exception as e:
            print(f"Error fetching trader specialties: {str(e)}")
            return {"error": f"Failed to fetch trader specialties: {str(e)}"}, 500