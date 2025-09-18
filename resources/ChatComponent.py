from flask_restful import Resource
from flask import request
from models.chat_component import Conversation
from models.message import Message
from models.conversation_participants import ConversationParticipant
from models.ClientProject import ClientProject
from managers.auth import auth
import json
from datetime import datetime
from bson import ObjectId

class ChatComponent(Resource):
    @auth.login_required
    def post(self, conversation_id):
        """Create a new conversation or send a message"""
        try:
            data = request.get_json() or {}
            
            current_user = auth.current_user()
            user_id = str(current_user.id)
            print(f'Authenticated user ID: {current_user.id}')
            
            action = data.get('action', 'create_conversation')
            
            if action == 'send_message':
                return self.save_message(data, user_id, conversation_id)
            else:
                return {
                    "success": True,
                    "message": f"Action '{action}' received successfully",
                    "user_id": user_id,
                    "data": data
                }, 200
                
        except Exception as e:
            print(f"Error in ChatComponent: {str(e)}")
            return {"error": f"Failed to process request: {str(e)}"}, 500

    @auth.login_required
    def get(self, conversation_id):
        """Get messages from an existing conversation"""
        return self.get_messages(auth.current_user().id, conversation_id)

    def get_messages(self, user_id, conversation_id):
        """Get messages from an existing conversation"""
        try:
            # Get messages ordered by creation date (oldest first)
            messages = Message.objects(conversation_id=conversation_id).order_by('created_at')
            
            # Parse messages into JSON-serializable format
            messages_list = []
            for message in messages:
                # Skip deleted messages
                if message.is_deleted():
                    continue
                    
                messages_list.append({
                    "id": str(message.pk),
                    "conversation_id": message.conversation_id,
                    "sender_id": message.sender_id,
                    "body": message.body,
                    "attachments_json": message.attachments_json,
                    "created_at": message.created_at.isoformat(),
                    "edited_at": message.edited_at.isoformat() if message.edited_at else None,
                    "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None
                })
            
            print(f'Found {len(messages_list)} messages for conversation {conversation_id}')
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "messages": messages_list,
                "count": len(messages_list)
            }, 200
            
        except Exception as e:
            print(f"Error getting messages: {str(e)}")
            return {"error": f"Failed to get messages: {str(e)}"}, 500
    
    def save_message(self, data, user_id, conversation_id):
        """Save a message in an existing conversation"""
        try:
            # Extract data (conversation_id now comes from URL parameter)
            message_body = data.get('body')
            
            # Validate required fields
            if not conversation_id or not message_body:
                return {"error": "conversationId and body are required"}, 400
            
            # Check if conversation exists
            conversation = Conversation.objects(conversation_id=conversation_id).first()
            if not conversation:
                return {"error": "Conversation not found"}, 404
            
            # Create new message
            message = Message(
                conversation_id=conversation_id,
                sender_id=user_id,  
                body=message_body
            )
            message.save()
            
            # Update conversation
            conversation.last_message_at = datetime.utcnow()
            conversation.message_count = str(int(conversation.message_count) + 1)
            conversation.save()
            
            return {
                "success": True,
                "message": "Message sent successfully",
                "message_id": str(message.pk),  
                "conversation_id": conversation_id,
                "created_at": message.created_at.isoformat()
            }, 201
            
        except Exception as e:
            print(f"Error saving message: {str(e)}")
            return {"error": f"Failed to save message: {str(e)}"}, 500
      

class CreateChat(Resource):
    """Separate resource for create-chat endpoint"""
    @auth.login_required
    def post(self):
        """Create a conversation from frontend data"""
        try:
            data = request.get_json() or {}
            print('Create chat data:', data)
            
            # Extract user ID from JWT token
            current_user = auth.current_user()
            trader_id = str(current_user.id)  # The authenticated user is the trader
            print(f'Authenticated trader ID: {trader_id}')
            
            # Extract frontend data
            conversation_id = data.get('conversationId')
            homeowner_name = data.get('homeownerName')
            trader_name = data.get('traderName')
            job_title = data.get('jobTitle')
            
            # We need the job ID to create the conversation
            job_id = data.get('job_id')  # From the job/project
            
            print('jobId', job_id)
            print('trader_id', trader_id)
            
            # Validate required IDs (trader_id is now from JWT token)
            if not job_id:
                return {
                    "error": "Missing required field: job_id is required",
                    "received": {
                        "job_id": job_id
                    }
                }, 400
            
            # Retrieve homeowner_id from the job/project
            try:
                project = ClientProject.objects(project_id=job_id).first()
                if not project:
                    return {
                        "error": f"Project not found with jobId: {job_id}",
                        "jobId": job_id
                    }, 404
                
                print('show me the project', project)
                
                homeowner_id = project.user_id
                print('Retrieved homeowner_id from project:', homeowner_id)
                
            except Exception as e:
                print(f"Error retrieving project: {str(e)}")
                return {
                    "error": f"Failed to retrieve project details: {str(e)}",
                    "jobId": job_id
                }, 500
            
            print(f"IDs: job_id={job_id}, homeowner_id={homeowner_id}, trader_id={trader_id}")
            
            # Check if conversation already exists
            existing_conversation = Conversation.objects(
                job_id=job_id,
                homeowner_id=homeowner_id,
                trader_id=trader_id
            ).first()
            
            if existing_conversation:
                print(f"Conversation already exists: {existing_conversation.conversation_id}")
                return {
                    "success": True,
                    "conversation": {
                        "id": existing_conversation.conversation_id,
                        "conversation_id": existing_conversation.conversation_id,
                        "job_id": existing_conversation.job_id,
                        "homeowner_id": existing_conversation.homeowner_id,
                        "trader_id": existing_conversation.trader_id,
                        "status": existing_conversation.status,
                        "createdAt": existing_conversation.created_at.isoformat(),
                        "message_count": existing_conversation.message_count
                    },
                    "message": "Conversation already exists"
                }, 200
            
            # Create new conversation
            conversation = Conversation(
                job_id=job_id,
                homeowner_id=homeowner_id,
                trader_id=trader_id,
                can_view_phone=data.get('can_view_phone', False),
                can_view_email=data.get('can_view_email', True),
                status='open'
            )
            conversation.save()
            print(f"Created conversation: {conversation.conversation_id}")
            
            # Create participant records
            homeowner_participant = ConversationParticipant(
                conversation_id=conversation.conversation_id,
                user_id=homeowner_id,
                role='homeowner'
            )
            homeowner_participant.save()
            
            trader_participant = ConversationParticipant(
                conversation_id=conversation.conversation_id,
                user_id=trader_id,
                role='trader'
            )
            trader_participant.save()
            
            print(f"Created participants for conversation: {conversation.conversation_id}")
            
            return {
                "success": True,
                "conversation": {
                    "id": conversation.conversation_id,
                    "conversation_id": conversation.conversation_id,
                    "homeowner_id": conversation.homeowner_id,
                    "trader_id": conversation.trader_id,
                    "job_id": conversation.job_id,
                    "status": conversation.status,
                    "createdAt": conversation.created_at.isoformat(),
                    "message_count": conversation.message_count
                },
                "message": "Chat created successfully"
            }, 201
            
        except Exception as e:
            print(f"Error creating chat from frontend: {str(e)}")
            return {"error": f"Failed to create chat: {str(e)}"}, 500


class GetAllChats(Resource):
    @auth.login_required
    def get(self, user_id):
        """Get all conversations for a user (both as homeowner and trader)"""
        try:
            current_user = auth.current_user()
            authenticated_user_id = str(current_user.id)
            
            # Verify the user is accessing their own chats
            if authenticated_user_id != user_id:
                return {"error": "Unauthorized access to user chats"}, 403
            
            # Get conversations where user is either homeowner or trader
            homeowner_chats = Conversation.objects(homeowner_id=user_id)
            trader_chats = Conversation.objects(trader_id=user_id)
            
            # Combine and format the results
            all_chats = []
            
            # Add homeowner conversations
            for chat in homeowner_chats:
                all_chats.append({
                    "conversation_id": chat.conversation_id,
                    "job_id": chat.job_id,
                    "user_role": "homeowner",
                    "other_party_id": chat.trader_id,
                    "status": chat.status,
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "message_count": chat.message_count,
                    "created_at": chat.created_at.isoformat()
                })
            
            # Add trader conversations
            for chat in trader_chats:
                all_chats.append({
                    "conversation_id": chat.conversation_id,
                    "job_id": chat.job_id,
                    "user_role": "trader",
                    "other_party_id": chat.homeowner_id,
                    "status": chat.status,
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "message_count": chat.message_count,
                    "created_at": chat.created_at.isoformat()
                })
            
            # Sort by last_message_at (most recent first)
            all_chats.sort(
                key=lambda x: x['last_message_at'] or '1970-01-01T00:00:00',
                reverse=True
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "chats": all_chats,
                "count": len(all_chats)
            }, 200
            
        except Exception as e:
            print(f"Error getting all chats: {str(e)}")
            return {"error": f"Failed to get all chats: {str(e)}"}, 500
