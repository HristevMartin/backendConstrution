from flask_restful import Resource
from flask import request
from models.TraderProfile import TraderProfile
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from util.gcs_handler import GCSHandler
from bson import ObjectId

class TraderForm(Resource):
    def post(self):
        # Get form data and files
        data = {}
        data['fullName'] = request.form.get('fullName', '')
        data['company'] = request.form.get('company', '')
        data['bio'] = request.form.get('bio', '')
        data['yearsExperience'] = request.form.get('yearsExperience', '')
        data['specialties'] = request.form.get('specialties', '')
        data['userId'] = request.form.get('userId', '')
        data['createdDate'] = datetime.now()
        data['city'] = request.form.get('city', '')
        data['userId'] = request.form.get('userId', '')
        data['selectedTrades'] = request.form.get('selectedTrade', '')
        print('show me the selected trades', data['selectedTrades'])
        
        # Handle file upload using Google Cloud Storage
        profile_image = request.files.get('profileImage')
        if profile_image and profile_image.filename != '':
            try:
                # Initialize GCS handler
                gcs_handler = GCSHandler()
                
                user_id = data.get('userId', 'unknown_user')
                print(f'Uploading profile image for user: {user_id}')
                
                # Upload file to GCS
                file_url = gcs_handler.upload_profile_image(
                    file=profile_image,
                    user_id=user_id,
                    file_type='profile_image_pictures'
                )
                
                if file_url:
                    # Save the GCS URL to database
                    data['profileImage'] = file_url
                    print(f'Profile image uploaded successfully to GCS: {file_url}')
                else:
                    data['profileImage'] = None
                    print('Failed to upload profile image to GCS')
                
            except Exception as e:
                print(f'Error handling file upload to GCS: {str(e)}')
                data['profileImage'] = None
        else:
            data['profileImage'] = None
            print('No profile image uploaded or filename is empty')
        
        print('Received data:', data)
        
        TraderProfile(**data).save()
        return {"message": "Trader form submitted successfully"}, 200

class GetProfileByID(Resource):
    def get(self, profile_id):
        try:
            print(f'Looking for profile with ID/UserID: {profile_id}')
            
            # Try to find by userId first (string field)
            profile = TraderProfile.objects(userId=profile_id).first()
            
            # If not found by userId, try by MongoDB ObjectId
            if not profile:
                try:
                    profile = TraderProfile.objects(id=ObjectId(profile_id)).first()
                except:
                    pass
            
            if not profile:
                return {"error": "Profile not found"}, 404
            
            print('Profile found, converting to dict...')
            
            # Convert to dictionary manually to handle datetime serialization
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
            
            print('Profile data converted successfully')
            return profile_data, 200
            
        except Exception as e:
            print(f'Error in GetProfileByID: {str(e)}')
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to get profile: {str(e)}"}, 500
