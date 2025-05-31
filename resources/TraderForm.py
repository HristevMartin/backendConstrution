from flask_restful import Resource
from flask import request
from models.TraderProfile import TraderProfile
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

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
        data['userId'] = request.form.get('userId', '')
        data['selectedTrades'] = request.form.get('selectedTrade', '')
        print('show me the selected trades', data['selectedTrades'])
        
        
        # Handle file upload
        profile_image = request.files.get('profileImage')
        if profile_image and profile_image.filename != '':
            try:
                # Secure the filename and save the file
                filename = secure_filename(profile_image.filename)
                
                # Create nested folder structure based on user ID
                user_id = data.get('userId', 'unknown_user')
                # Use user ID as folder name (already secure and unique)
                folder_name = str(user_id) if user_id else 'unknown_user'
                
                # Create the upload path with nested folder structure
                upload_folder = os.path.join('uploads', 'profile_images', folder_name)
                print(f'Creating upload folder: {upload_folder}')
                
                # Create directories if they don't exist
                os.makedirs(upload_folder, exist_ok=True)
                print(f'Upload folder created successfully: {upload_folder}')
                
                # Full file path
                file_path = os.path.join(upload_folder, filename)
                print(f'Saving file to: {file_path}')
                
                # Save the file
                profile_image.save(file_path)
                print(f'File saved successfully: {file_path}')
                
                # Save the file path to database
                data['profileImage'] = file_path
                print(f'Profile image path saved to data: {file_path}')
                
            except Exception as e:
                print(f'Error handling file upload: {str(e)}')
                data['profileImage'] = None
        else:
            data['profileImage'] = None
            print('No profile image uploaded or filename is empty')
        
        print('Received data:', data)
        
        TraderProfile(**data).save()
        return {"message": "Trader form submitted successfully"}, 200

