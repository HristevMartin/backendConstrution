from flask import request
from flask_restful import Resource
from models.TraderProject import TraderProject
from util.gcs_handler import GCSHandler
from util.email_service import EmailService
import uuid
from datetime import datetime

class SaveTraderProject(Resource):
    def post(self):
        try:
            print("Request content type:", request.content_type)
            print("Form data:", dict(request.form))
            print("Files received:", len(request.files.getlist('projectImages')) if request.files else 0)
            
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
                    # Continue without images if GCS fails
                    image_urls = []
            
            # Add image URLs to form data
            form_data['projectImages'] = image_urls
            
            print('Final form data:', {
                'project_id': project_id,
                'user_id': user_id,
                'name': form_data.get('name'),
                'email': form_data.get('email'),
                'primaryTrade': form_data.get('primaryTrade'),
                'city': form_data.get('city'),
                'image_count': len(image_urls)
            })
            
            # Save trader registration data to database using the TraderProject model
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
                    createdDate=datetime.utcnow()
                )
                
                trader_project.save()
                
                print(f'Trader registration saved to database successfully with ID: {project_id}')
                
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
                        "createdDate": trader_project.createdDate.isoformat()
                    },
                    "images_uploaded": len(image_urls),
                    "image_urls": image_urls
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
        
    def get(self):
        try:
            projects = TraderProject.objects()
            return {"success": True, "projects": projects}, 200
        except Exception as e:
            print(f"Error fetching trader projects: {str(e)}")
            return {"error": f"Failed to fetch trader projects: {str(e)}"}, 500
        
        