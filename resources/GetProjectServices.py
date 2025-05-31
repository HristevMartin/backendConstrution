from flask_restful import Resource
from flask import request, url_for
import os
import json
from datetime import datetime
from bson import ObjectId
from models.TraderProfile import TraderProfile


def serialize_mongo_object(obj):
    """Convert MongoDB object to JSON serializable dictionary"""
    if obj is None:
        return None
    
    # Convert to dictionary
    data = obj.to_mongo().to_dict()
    
    # Handle ObjectId conversion
    if '_id' in data:
        data['_id'] = str(data['_id'])
    
    # Handle datetime conversion
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            data[key] = str(value)
    
    return data


class GetProjectServices(Resource):
    def get(self):
        projects = TraderProfile.objects()
        project_list = []
        for project in projects:
            project_data = {
                "trade": project.selectedTrades
            }
            project_list.append(project_data)
        
        return project_list, 200


class GetSpecificServices(Resource):
    def get(self, trade):
        projects = TraderProfile.objects(selectedTrades=trade)
        print('show me the projects', projects)
        project_list = []
        for project in projects:
            # Convert the MongoDB object to a JSON serializable dictionary
            project_data = serialize_mongo_object(project)
            
            # Convert file path to accessible URL if image exists
            if project_data.get('profileImage') and os.path.exists(project_data['profileImage']):
                # Extract parts from the file path: uploads/profile_images/user123/image.jpg
                path_parts = project_data['profileImage'].replace(os.sep, '/').split('/')
                if len(path_parts) >= 4 and path_parts[0] == 'uploads':
                    folder = path_parts[1]  # profile_images
                    user_id = path_parts[2]  # user123
                    filename = path_parts[3]  # image.jpg
                    # Create URL matching our route pattern: /uploads/<folder>/<user_id>/<filename>
                    project_data['profileImageUrl'] = f"{request.url_root}uploads/{folder}/{user_id}/{filename}"
                else:
                    project_data['profileImageUrl'] = None
            else:
                project_data['profileImageUrl'] = None
                
            project_list.append(project_data)
        return project_list, 200
        