from flask_restful import Resource
from managers.auth import auth
from models.trader_rating import TraderRating as TraderRatingModel
from models.chat_component import Conversation
from models.TraderProject import TraderProject
from models.ClientProject import ClientProject
from models.message import Message


class TraderRating(Resource):
    @auth.login_required
    def get(self):
        user_id = str(auth.current_user().id)
        print('show me the homeowner user_id', user_id)

        # Get all conversations where the user is the homeowner
        conversations = Conversation.objects(homeowner_id=user_id, status='open')
        
        print(f'Found {conversations.count()} active conversations for homeowner {user_id}')
        
        # Build response with conversation details
        chats_list = []
        for conv in conversations:
            try:
                # Get trader details
                trader = TraderProject.objects(userId=conv.trader_id).first()
                
                # Get job/project details
                job = ClientProject.objects(project_id=conv.job_id).first()
                
                # Get last message
                last_message = Message.objects(conversation_id=conv.conversation_id).order_by('-created_at').first()
                
                chat_data = {
                    'conversation_id': conv.conversation_id,
                    'job_id': conv.job_id,
                    'trader_id': conv.trader_id,
                    'status': conv.status,
                    'message_count': conv.message_count,
                    'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
                    'created_at': conv.created_at.isoformat(),
                    'trader_details': {
                        'name': trader.name if trader else 'Unknown',
                        'primaryTrade': trader.primaryTrade if trader else '',
                        'city': trader.city if trader else '',
                        'email': trader.email if trader and conv.can_view_email else None,
                        'phone': trader.phone if trader and conv.can_view_phone else None,
                    } if trader else None,
                    'job_details': {
                        'job_title': job.job_title if job else '',
                        'job_description': job.job_description if job else '',
                        'budget': job.budget if job else '',
                        'urgency': job.urgency if job else '',
                        'location': job.location if job else '',
                    } if job else None,
                    'last_message': {
                        'body': last_message.body if last_message else '',
                        'sender_id': last_message.sender_id if last_message else '',
                        'created_at': last_message.created_at.isoformat() if last_message else None,
                    } if last_message else None
                }
                
                chats_list.append(chat_data)
                
            except Exception as e:
                print(f"Error processing conversation {conv.conversation_id}: {str(e)}")
                continue
        print('show me the chats_list', chats_list)
        return {
            "success": True,
            "chats": chats_list,
            "total_chats": len(chats_list),
            "message": "Active chats retrieved successfully"
        }, 200
    

    @auth.login_required
    def post(self):
        try:
            from flask import request
            from datetime import datetime
            
            user_id = str(auth.current_user().id)
            data = request.get_json() or {}
            
            print('show me the homeowner user_id', user_id)
            print('show me the incoming data', data)
            
            # Extract required fields
            trader_id = data.get('userId') or data.get('traderId')
            job_id = data.get('jobId')
            rating = data.get('rating')
            comment = data.get('comment', '')
            
            # Validate required fields
            if not trader_id:
                return {"success": False, "error": "userId/traderId is required"}, 400
            if not job_id:
                return {"success": False, "error": "jobId is required"}, 400
            if not rating:
                return {"success": False, "error": "rating is required"}, 400
            
            # Check if rating already exists for this job and homeowner
            existing_rating = TraderRatingModel.objects(
                jobId=job_id, 
                homeownerId=user_id
            ).first()
            
            if existing_rating:
                # Update existing rating
                existing_rating.rating = int(rating)
                existing_rating.comment = comment
                existing_rating.userId = trader_id
                existing_rating.updatedDate = datetime.utcnow()
                existing_rating.save()
                
                print(f"Updated existing rating for job {job_id}")
                
                return {
                    "success": True,
                    "message": "Rating updated successfully",
                    "rating": {
                        "userId": existing_rating.userId,
                        "homeownerId": existing_rating.homeownerId,
                        "jobId": existing_rating.jobId,
                        "rating": existing_rating.rating,
                        "comment": existing_rating.comment,
                        "updatedDate": existing_rating.updatedDate.isoformat()
                    }
                }, 200
            else:
                # Create new rating
                new_rating = TraderRatingModel(
                    userId=trader_id,
                    homeownerId=user_id,
                    jobId=job_id,
                    rating=int(rating),
                    comment=comment,
                    createdDate=datetime.utcnow(),
                    updatedDate=datetime.utcnow()
                )
                new_rating.save()
                
                print(f"Created new rating for job {job_id}")
                
                return {
                    "success": True,
                    "message": "Rating created successfully",
                    "rating": {
                        "userId": new_rating.userId,
                        "homeownerId": new_rating.homeownerId,
                        "jobId": new_rating.jobId,
                        "rating": new_rating.rating,
                        "comment": new_rating.comment,
                        "createdDate": new_rating.createdDate.isoformat()
                    }
                }, 201
                
        except Exception as e:
            print(f"Error saving trader rating: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save rating: {str(e)}"
            }, 500