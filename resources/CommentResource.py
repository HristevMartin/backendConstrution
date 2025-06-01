from flask_restful import Resource
from flask import request
from models.Comment import Comment
import json
from datetime import datetime
from bson import ObjectId

class SaveComment(Resource):
    def post(self):
        try:
            print("Request content type:", request.content_type)
            
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                print("JSON data received:", data)
            else:
                # Handle form data
                data = {
                    'projectId': request.form.get('projectId', '').strip(),
                    'user': request.form.get('user', '').strip(),
                    'comment': request.form.get('comment', '').strip(),
                    'date': request.form.get('date', '').strip()
                }
                print("Form data received:", data)
            
            # Validate required fields
            if not data.get('projectId'):
                return {"error": "Project ID is required"}, 400
            
            if not data.get('user'):
                return {"error": "User is required"}, 400
            
            if not data.get('comment'):
                return {"error": "Comment is required"}, 400
            
            # Create comment data
            comment_data = {
                'projectId': data['projectId'],
                'user': data['user'],
                'comment': data['comment'],
                'date': data.get('date', ''),
            }
            
            print('Final comment data to save:', comment_data)
            
            # Create and save the comment
            comment = Comment(**comment_data)
            comment.save()
            
            return {
                "message": "Comment saved successfully",
                "comment_id": str(comment.id),
                "projectId": comment.projectId
            }, 200
            
        except Exception as e:
            print(f"Error saving comment: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to save comment: {str(e)}"}, 500

class GetCommentsByProjectId(Resource):
    def get(self, project_id):
        try:
            print(f'Looking for comments with projectId: {project_id}')
            
            # Find all comments for the given projectId
            comments = Comment.objects(projectId=project_id).order_by('-created_at')
            
            if not comments:
                return {"comments": [], "count": 0}, 200
            
            print(f'Found {len(comments)} comments for projectId: {project_id}')
            
            # Convert comments to dictionary list with proper serialization
            comments_list = []
            for comment in comments:
                comment_data = {
                    'id': str(comment.id),
                    'projectId': comment.projectId,
                    'user': comment.user,
                    'comment': comment.comment,
                    'date': comment.date,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                    'updated_at': comment.updated_at.isoformat() if comment.updated_at else None
                }
                comments_list.append(comment_data)
            
            return {
                "comments": comments_list,
                "count": len(comments_list),
                "projectId": project_id
            }, 200
            
        except Exception as e:
            print(f'Error retrieving comments for projectId {project_id}: {str(e)}')
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to retrieve comments: {str(e)}"}, 500

class DeleteComment(Resource):
    def delete(self, comment_id):
        try:
            print(f'Attempting to delete comment with ID: {comment_id}')
            
            # Find and delete the comment
            comment = Comment.objects(id=ObjectId(comment_id)).first()
            
            if not comment:
                return {"error": "Comment not found"}, 404
            
            project_id = comment.projectId
            comment.delete()
            
            print(f'Comment {comment_id} deleted successfully')
            
            return {
                "message": "Comment deleted successfully",
                "comment_id": comment_id,
                "projectId": project_id
            }, 200
            
        except Exception as e:
            print(f'Error deleting comment {comment_id}: {str(e)}')
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to delete comment: {str(e)}"}, 500

class UpdateComment(Resource):
    def put(self, comment_id):
        try:
            print(f'Attempting to update comment with ID: {comment_id}')
            
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = {
                    'comment': request.form.get('comment', '').strip(),
                    'date': request.form.get('date', '').strip()
                }
            
            # Find the comment
            comment = Comment.objects(id=ObjectId(comment_id)).first()
            
            if not comment:
                return {"error": "Comment not found"}, 404
            
            # Update fields if provided
            if data.get('comment'):
                comment.comment = data['comment']
            
            if data.get('date'):
                comment.date = data['date']
            
            # Save the updated comment
            comment.save()
            
            print(f'Comment {comment_id} updated successfully')
            
            # Return updated comment data
            comment_data = {
                'id': str(comment.id),
                'projectId': comment.projectId,
                'user': comment.user,
                'comment': comment.comment,
                'date': comment.date,
                'created_at': comment.created_at.isoformat() if comment.created_at else None,
                'updated_at': comment.updated_at.isoformat() if comment.updated_at else None
            }
            
            return {
                "message": "Comment updated successfully",
                "comment": comment_data
            }, 200
            
        except Exception as e:
            print(f'Error updating comment {comment_id}: {str(e)}')
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to update comment: {str(e)}"}, 500 