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
                job = ClientProject.objects(project_id=conv.job_id, is_deleted=False).first()
                
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


class PastJobs(Resource):
    @auth.login_required
    def get(self):
        try:
            user_id = str(auth.current_user().id)
            print('show me the user_id', user_id)
            
            # Check if user is a trader by checking if TraderProject exists
            trader_profile = TraderProject.objects(userId=user_id).first()
            is_trader = trader_profile is not None
            
            # Query ratings based on user type
            if is_trader:
                # Trader: get ratings where they are the service provider (userId)
                ratings = TraderRatingModel.objects(userId=user_id)
                user_type = "trader"
                print(f'User is a trader. Found {ratings.count()} ratings received')
            else:
                # Homeowner: get ratings where they are the client (homeownerId)
                ratings = TraderRatingModel.objects(homeownerId=user_id)
                user_type = "homeowner"
                print(f'User is a homeowner. Found {ratings.count()} ratings given')
            
            ratings_list = []
            for rating in ratings:
                rating_data = {
                    'userId': rating.userId,
                    'homeownerId': rating.homeownerId,
                    'jobId': rating.jobId,
                    'rating': rating.rating,
                    'comment': rating.comment,
                    'createdDate': rating.createdDate.isoformat() if rating.createdDate else None,
                    'updatedDate': rating.updatedDate.isoformat() if rating.updatedDate else None
                }
                
                # Enrich with job details
                try:
                    job = ClientProject.objects(project_id=rating.jobId, is_deleted=False).first()
                    if job:
                        rating_data['job_title'] = job.job_title
                        rating_data['job_description'] = job.job_description
                        rating_data['location'] = job.location
                        rating_data['job_status'] = job.status
                except Exception as e:
                    print(f"Error fetching job details for {rating.jobId}: {str(e)}")
                    rating_data['job_title'] = "Unknown"
                
                # Enrich with trader details (useful for homeowners)
                if not is_trader:
                    try:
                        trader = TraderProject.objects(userId=rating.userId).first()
                        if trader:
                            rating_data['trader_name'] = trader.name
                            rating_data['trader_trade'] = trader.primaryTrade
                    except Exception as e:
                        print(f"Error fetching trader details for {rating.userId}: {str(e)}")
                
                ratings_list.append(rating_data)
            
            return {
                "success": True,
                "user_type": user_type,
                "ratings": ratings_list,
                "total_ratings": len(ratings_list),
                "message": f"Past jobs retrieved successfully for {user_type}"
            }, 200
            
        except Exception as e:
            print(f'Error in PastJobs: {str(e)}')
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve past jobs"
            }, 500


class GetTraderRating(Resource):
    @auth.login_required
    def get(self):
        user_id = str(auth.current_user().id)
        
        trader_profile = TraderProject.objects(userId=user_id).first()
        is_trader = trader_profile is not None
        
        if is_trader:
            trader_rating = TraderRatingModel.objects(userId=user_id).all()
            user_type = "trader"
        else:
            trader_rating = TraderRatingModel.objects(homeownerId=user_id).all()
            user_type = "homeowner"
        
        print(f'User type: {user_type}, Found {trader_rating.count()} ratings')

        total_rating = 0
        count = 0
        comments_list = []

        for rating in trader_rating:
            if rating.rating is not None:
                total_rating += int(rating.rating)
                count += 1
            
            if rating.comment:
                comment_obj = {
                    "comment": rating.comment,
                    "rating": int(rating.rating) if rating.rating is not None else None,
                    "createdDate": rating.createdDate.isoformat() if getattr(rating, "createdDate", None) else None,
                    "job_description": "",
                    "job_title": "",
                    "first_name": ""
                }
                
                try:
                    job = ClientProject.objects(project_id=rating.jobId).first()
                    if job:
                        comment_obj["job_description"] = job.job_description or ""
                        comment_obj["job_title"] = job.job_title or ""
                        comment_obj["first_name"] = job.first_name or ""
                    else:
                        print(f"No job found for jobId: {rating.jobId}")
                except Exception as e:
                    print(f"Error fetching job details for rating {rating.jobId}: {str(e)}")
                
                if is_trader:
                    try:
                        trader = TraderProject.objects(userId=rating.userId).first()
                        if trader:
                            comment_obj["trader_name"] = trader.name
                    except Exception as e:
                        print(f"Error fetching trader info: {str(e)}")
                
                comments_list.append(comment_obj)

        average_rating = round(total_rating / count, 2) if count > 0 else None
        return {
            "success": True,
            "user_type": user_type,
            "rating": float(average_rating) if average_rating is not None else 0.0,
            "total_ratings": int(count),
            "comments": comments_list
        }, 200