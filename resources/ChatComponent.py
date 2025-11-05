from flask_restful import Resource
from flask import request
from models.chat_component import Conversation
from models.message import Message
from models.conversation_participants import ConversationParticipant
from models.ClientProject import ClientProject
from models.TraderProject import TraderProject
from managers.auth import auth
import json
import os
import uuid
from datetime import datetime, timedelta
from google.cloud import storage

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
            print('='*80)
            print('💬 SAVE MESSAGE REQUEST')
            print('='*80)
            print(f'📋 conversation_id: {conversation_id}')
            print(f'👤 sender_id (user_id): {user_id}')
            print(f'📋 Request data: {json.dumps(data, indent=2)}')
            
            # Extract data (conversation_id now comes from URL parameter)
            message_body = data.get('body')
            
            # Validate required fields
            if not conversation_id or not message_body:
                print(f'❌ ERROR: Missing required fields')
                print(f'   - conversation_id: {conversation_id}')
                print(f'   - body: {message_body}')
                return {"error": "conversationId and body are required"}, 400
            
            # Check if conversation exists
            conversation = Conversation.objects(conversation_id=conversation_id).first()
            if not conversation:
                print(f'❌ ERROR: Conversation not found: {conversation_id}')
                return {"error": "Conversation not found"}, 404
            
            print(f'✅ Conversation found:')
            print(f'   - conversation_id: {conversation.conversation_id}')
            print(f'   - homeowner_id: {conversation.homeowner_id} (type: {type(conversation.homeowner_id)})')
            print(f'   - trader_id: {conversation.trader_id} (type: {type(conversation.trader_id)})')
            
            # Convert sender_id to string for consistency
            sender_id_str = str(user_id)
            print(f'👤 Sender ID (string): {sender_id_str}')
            
            # Create new message
            message = Message(
                conversation_id=conversation_id,
                sender_id=sender_id_str,
                body=message_body
            )
            message.save()
            print(f'✅ Message saved: {str(message.pk)}')
            
            # Update conversation
            conversation.last_message_at = datetime.utcnow()
            conversation.message_count = str(int(conversation.message_count) + 1)
            conversation.save()
            print(f'✅ Conversation updated: message_count={conversation.message_count}')
            
            # Update unread_count for the recipient (the other participant)
            try:
                print(f'🔍 Finding recipient participant...')
                print(f'   - conversation_id: {conversation_id}')
                print(f'   - sender_id: {sender_id_str}')
                
                # Get ALL participants first for debugging
                all_participants = ConversationParticipant.objects(conversation_id=conversation_id)
                print(f'📋 All participants in conversation ({all_participants.count()} total):')
                for p in all_participants:
                    p_user_id_str = str(p.user_id)
                    print(f'   - user_id: {p_user_id_str} (type: {type(p.user_id)}, raw: {p.user_id})')
                    print(f'     role: {p.role}')
                    print(f'     unread_count: {p.unread_count}')
                    print(f'     matches sender? {p_user_id_str == sender_id_str}')
                
                # Find the recipient participant (not the sender)
                # Try multiple query methods to handle different ID types
                recipient_participant = None
                
                # Method 1: Direct string comparison
                for p in all_participants:
                    p_user_id_str = str(p.user_id)
                    if p_user_id_str != sender_id_str:
                        recipient_participant = p
                        print(f'✅ Found recipient using string comparison: {p_user_id_str}')
                        break
                
                # Method 2: If Method 1 failed, try MongoDB query
                if not recipient_participant:
                    print(f'⚠️ Method 1 failed, trying MongoDB query...')
                    recipient_participant = ConversationParticipant.objects(
                        conversation_id=conversation_id
                    ).filter(user_id__ne=sender_id_str).first()
                    
                    if recipient_participant:
                        print(f'✅ Found recipient using MongoDB query: {str(recipient_participant.user_id)}')
                    else:
                        print(f'❌ Method 2 also failed')
                
                # Method 3: Try with ObjectId conversion if needed
                if not recipient_participant:
                    print(f'⚠️ Method 2 failed, trying ObjectId conversion...')
                    from bson import ObjectId
                    try:
                        sender_oid = ObjectId(sender_id_str) if ObjectId.is_valid(sender_id_str) else None
                        if sender_oid:
                            recipient_participant = ConversationParticipant.objects(
                                conversation_id=conversation_id
                            ).filter(user_id__ne=sender_oid).first()
                            if recipient_participant:
                                print(f'✅ Found recipient using ObjectId query: {str(recipient_participant.user_id)}')
                    except Exception as e:
                        print(f'⚠️ ObjectId conversion failed: {str(e)}')
                
                if recipient_participant:
                    # Increment unread_count by 1
                    current_unread = int(recipient_participant.unread_count or '0')
                    recipient_participant.unread_count = str(current_unread + 1)
                    recipient_participant.save()
                    print(f'✅ Updated unread_count for recipient {str(recipient_participant.user_id)}: {current_unread} -> {current_unread + 1}')
                else:
                    print(f'❌ ERROR: No recipient participant found!')
                    print(f'   This means the conversation only has one participant or lookup failed')
                    print(f'   This is a CRITICAL ERROR - messages won\'t be delivered!')
                    # Don't fail the message save, but log the error
                    
            except Exception as e:
                print(f'❌ ERROR updating unread_count for recipient: {str(e)}')
                import traceback
                traceback.print_exc()
                # Don't fail the message save if unread_count update fails
            
            print('='*80)
            print('✅ MESSAGE SAVE SUCCESSFUL')
            print('='*80)
            
            return {
                "success": True,
                "message": "Message sent successfully",
                "message_id": str(message.pk),
                "conversation_id": conversation_id,
                "created_at": message.created_at.isoformat()
            }, 201
            
        except Exception as e:
            print('='*80)
            print(f'❌ ERROR saving message: {str(e)}')
            print('='*80)
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to save message: {str(e)}"}, 500
      

class CreateChat(Resource):
    """Separate resource for create-chat endpoint"""
    @auth.login_required
    def post(self):
        """Create a conversation from frontend data"""
        try:
            data = request.get_json() or {}
            print('='*80)
            print('📞 CREATE CHAT REQUEST RECEIVED')
            print('='*80)
            print(f'📋 Request data: {json.dumps(data, indent=2)}')
            
            # Extract user ID from JWT token
            current_user = auth.current_user()
            trader_id = str(current_user.id)  # The authenticated user is the trader
            print(f'👤 Authenticated trader ID: {trader_id}')
            
            # Extract frontend data
            conversation_id = data.get('conversationId')
            homeowner_name = data.get('homeownerName')
            trader_name = data.get('traderName')
            job_title = data.get('jobTitle')
            
            # We need the job ID to create the conversation
            job_id = data.get('job_id')  # From the job/project
            homeowner_id_from_request = data.get('homeowner_id')  # From frontend (if provided)
            
            print(f'📋 Request fields:')
            print(f'   - job_id: {job_id}')
            print(f'   - trader_id (from JWT): {trader_id}')
            print(f'   - homeowner_id (from request): {homeowner_id_from_request}')
            
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
                print(f'🔍 Looking up project with job_id: {job_id}')
                project = ClientProject.objects(project_id=job_id, is_deleted=False).first()
                
                if not project:
                    print(f'❌ ERROR: Project not found with job_id: {job_id}')
                    return {
                        "error": f"Project not found with jobId: {job_id}",
                        "jobId": job_id
                    }, 404
                
                print(f'✅ Project found:')
                print(f'   - project_id: {project.project_id}')
                print(f'   - project.user_id: {project.user_id}')
                print(f'   - project.user_id type: {type(project.user_id)}')
                
                homeowner_id = project.user_id
                
                # Convert to string if it's an ObjectId
                if homeowner_id:
                    homeowner_id = str(homeowner_id)
                
                print(f'✅ Retrieved homeowner_id from project: {homeowner_id}')
                
                # Validate homeowner_id
                if not homeowner_id:
                    print(f'❌ ERROR: project.user_id is None or empty!')
                    return {
                        "error": "Project has no user_id (homeowner_id)",
                        "jobId": job_id
                    }, 500
                
                # Warn if frontend sent homeowner_id but it doesn't match
                if homeowner_id_from_request and homeowner_id_from_request != homeowner_id:
                    print(f'⚠️ WARNING: Frontend homeowner_id ({homeowner_id_from_request}) does not match project.user_id ({homeowner_id})')
                    print(f'   Using project.user_id ({homeowner_id}) as source of truth')
                
            except Exception as e:
                print(f'❌ ERROR retrieving project: {str(e)}')
                import traceback
                traceback.print_exc()
                return {
                    "error": f"Failed to retrieve project details: {str(e)}",
                    "jobId": job_id
                }, 500
            
            print(f'📊 Final IDs:')
            print(f'   - job_id: {job_id}')
            print(f'   - homeowner_id: {homeowner_id} (type: {type(homeowner_id)})')
            print(f'   - trader_id: {trader_id} (type: {type(trader_id)})')
            
            # Check if conversation already exists
            existing_conversation = Conversation.objects(
                job_id=job_id,
                homeowner_id=homeowner_id,
                trader_id=trader_id
            ).first()
            
            if existing_conversation:
                print(f'✅ Conversation already exists: {existing_conversation.conversation_id}')
                
                # Verify participants exist
                participants = ConversationParticipant.objects(conversation_id=existing_conversation.conversation_id)
                print(f'📋 Existing participants: {participants.count()}')
                for p in participants:
                    print(f'   - user_id: {str(p.user_id)}, role: {p.role}')
                
                return {
                    "success": True,
                    "conversation": {
                        "id": existing_conversation.conversation_id,
                        "conversation_id": existing_conversation.conversation_id,
                        "job_id": existing_conversation.job_id,
                        "homeowner_id": str(existing_conversation.homeowner_id),
                        "trader_id": str(existing_conversation.trader_id),
                        "status": existing_conversation.status,
                        "createdAt": existing_conversation.created_at.isoformat(),
                        "message_count": existing_conversation.message_count
                    },
                    "message": "Conversation already exists"
                }, 200
            
            # Create new conversation
            print(f'🆕 Creating new conversation...')
            conversation = Conversation(
                job_id=job_id,
                homeowner_id=homeowner_id,
                trader_id=trader_id,
                can_view_phone=data.get('can_view_phone', False),
                can_view_email=data.get('can_view_email', True),
                status='open'
            )
            conversation.save()
            print(f'✅ Created conversation: {conversation.conversation_id}')
            
            # Create participant records
            print(f'👥 Creating participants...')
            
            # Convert IDs to strings for consistency
            homeowner_id_str = str(homeowner_id)
            trader_id_str = str(trader_id)
            
            homeowner_participant = ConversationParticipant(
                conversation_id=conversation.conversation_id,
                user_id=homeowner_id_str,
                role='homeowner'
            )
            homeowner_participant.save()
            print(f'✅ Created homeowner participant: user_id={homeowner_id_str}')
            
            trader_participant = ConversationParticipant(
                conversation_id=conversation.conversation_id,
                user_id=trader_id_str,
                role='trader'
            )
            trader_participant.save()
            print(f'✅ Created trader participant: user_id={trader_id_str}')
            
            # Verify participants were created
            verify_participants = ConversationParticipant.objects(conversation_id=conversation.conversation_id)
            print(f'✅ Verification: {verify_participants.count()} participants found')
            for p in verify_participants:
                print(f'   - user_id: {str(p.user_id)} (type: {type(p.user_id)}), role: {p.role}')
            
            print('='*80)
            print('✅ CONVERSATION CREATION SUCCESSFUL')
            print('='*80)
            
            return {
                "success": True,
                "conversation": {
                    "id": conversation.conversation_id,
                    "conversation_id": conversation.conversation_id,
                    "homeowner_id": str(conversation.homeowner_id),
                    "trader_id": str(conversation.trader_id),
                    "job_id": conversation.job_id,
                    "status": conversation.status,
                    "createdAt": conversation.created_at.isoformat(),
                    "message_count": conversation.message_count
                },
                "message": "Chat created successfully"
            }, 201
            
        except Exception as e:
            print('='*80)
            print(f'❌ ERROR creating chat: {str(e)}')
            print('='*80)
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to create chat: {str(e)}"}, 500


class GetAllChats(Resource):
    @auth.login_required
    def get(self):
        """Get all conversations for a user (both as homeowner and trader)"""
        try:
            current_user = auth.current_user()
            authenticated_user_id = str(current_user.id)
            
            user_id = authenticated_user_id
            
            def get_homeowner_counterparty_info(homeowner_id, job_id):
                """Get homeowner info from ClientProject when viewer is trader"""
                try:
                    # Fetch the ClientProject using job_id to get homeowner details
                    project = ClientProject.objects(project_id=job_id, is_deleted=False).first()
                    if project and project.first_name:
                        name = project.first_name
                        job_title = project.job_title if project.job_title else "Unknown"
                        print('show me the homeowner project', project)
                    else:
                        name = "Unknown"
                        job_title = "Unknown"
                    
                    return {
                        "id": homeowner_id,
                        "name": name,
                        "job_title": job_title,
                        "avatar_url": None
                    }
                except Exception as e:
                    print(f"Error fetching homeowner info for job {job_id}: {str(e)}")
                    return {
                        "id": homeowner_id,
                        "name": "Unknown",
                        "job_title": "Unknown",
                        "avatar_url": None
                    }
            
            def get_trader_counterparty_info(trader_id):
                """Get trader info from TraderProject when viewer is homeowner"""
                try:
                    # Fetch the TraderProject using trader_id to get trader details
                    trader_project = TraderProject.objects(userId=trader_id).first()
                    if trader_project and trader_project.name:
                        name = trader_project.name
                        job_title = trader_project.primaryTrade if trader_project.primaryTrade else "Unknown"
                        print('show me the trader project', trader_project)
                    else:
                        name = "Unknown"
                        job_title = "Unknown"
                    
                    return {
                        "id": trader_id,
                        "name": name,
                        "job_title": job_title,
                        "avatar_url": None
                    }
                except Exception as e:
                    print(f"Error fetching trader info for trader {trader_id}: {str(e)}")
                    return {
                        "id": trader_id,
                        "name": "Unknown",
                        "job_title": "Unknown",
                        "avatar_url": None
                    }
            
            # Get conversations where user is either homeowner or trader
            homeowner_chats = Conversation.objects(homeowner_id=user_id)
            trader_chats = Conversation.objects(trader_id=user_id)
            
            # Combine and format the results
            all_chats = []
            
            # Add homeowner conversations (viewer is homeowner, counterparty is trader)
            for chat in homeowner_chats:
                counterparty_info = get_trader_counterparty_info(chat.trader_id)
                all_chats.append({
                    "conversation_id": chat.conversation_id,
                    "job_id": chat.job_id,
                    "user_role": "homeowner",
                    "status": chat.status,
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "message_count": int(chat.message_count) if chat.message_count else 0,
                    "created_at": chat.created_at.isoformat(),
                    "counterparty": counterparty_info
                })
            
            # Add trader conversations (viewer is trader, counterparty is homeowner)
            for chat in trader_chats:
                counterparty_info = get_homeowner_counterparty_info(chat.homeowner_id, chat.job_id)
                all_chats.append({
                    "conversation_id": chat.conversation_id,
                    "job_id": chat.job_id,
                    "user_role": "trader",
                    "status": chat.status,
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "message_count": int(chat.message_count) if chat.message_count else 0,
                    "created_at": chat.created_at.isoformat(),
                    "counterparty": counterparty_info
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


class GetConversationById(Resource):
    @auth.login_required
    def get(self, job_id):
        try:
            current_user = auth.current_user()
            user_id = str(current_user.id)
            print('show me the user_id', user_id)
            print('show me the job_id', job_id)
            # Search for conversation by job_id and trader_id
            conversation = Conversation.objects(job_id=job_id, trader_id=user_id).first()
            
            if not conversation:
                return {"error": "Conversation not found"}, 404
            
            # Convert conversation to JSON-serializable format
            conversation_data = {
                "conversation_id": conversation.conversation_id,
                "job_id": conversation.job_id,
                "homeowner_id": conversation.homeowner_id,
                "trader_id": conversation.trader_id,
                "status": conversation.status,
                "can_view_phone": conversation.can_view_phone,
                "can_view_email": conversation.can_view_email,
                "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                "message_count": int(conversation.message_count) if conversation.message_count else 0,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }
            
            return {
                "success": True,
                "conversation": conversation_data
            }, 200
            
        except Exception as e:
            print(f"Error getting conversation by id: {str(e)}")
            return {"error": f"Failed to get conversation by id: {str(e)}"}, 500


class ChatSummary(Resource):
    @auth.login_required
    def get(self):
        try:
            user_id = str(auth.current_user().id)

            # Find all participant rows for this user (one per conversation)
            parts = list(ConversationParticipant.objects(user_id=user_id))

            # Map: conversation_id -> unread_count (int) + last_read_at if needed
            part_map = {
                p.conversation_id: {
                    "unread_count": int(p.unread_count or '0'),
                    "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None
                }
                for p in parts
            }

            # Fetch those conversations (both roles) and keep only open ones
            conv_ids = list(part_map.keys())
            conversations = Conversation.objects(
                conversation_id__in=conv_ids, status='open'
            ).order_by('-last_message_at')

            conversation_list = []
            unread_total = 0

            for conv in conversations:
                uc = part_map.get(conv.conversation_id, {}).get('unread_count', 0)
                unread_total += uc
                conversation_list.append({
                    "conversation_id": conv.conversation_id,
                    "job_id": conv.job_id,
                    "homeowner_id": conv.homeowner_id,
                    "trader_id": conv.trader_id,
                    "status": conv.status,
                    "can_view_phone": conv.can_view_phone,
                    "can_view_email": conv.can_view_email,
                    "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                    "message_count": int(conv.message_count) if conv.message_count else 0,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "unread_count": uc, 
                })
            res = {
                "success": True,
                "user_id": user_id,
                "conversations": conversation_list,
                "count": len(conversation_list),
                "unread_total": unread_total,   
                "has_chats": len(conversation_list) > 0
            }

            return res, 200

        except Exception as e:
            print(f"Error getting chat summary: {str(e)}")
            return {"error": f"Failed to get chat summary: {str(e)}"}, 500


class MarkConversationRead(Resource):
    @auth.login_required
    def get(self, conversation_id):
        """Mark conversation as read for the authenticated user"""
        try:
            current_user = auth.current_user()
            user_id = str(current_user.id)
            
            # Find the participant for this user
            participant = ConversationParticipant.objects(
                conversation_id=conversation_id, 
                user_id=user_id
            ).first()
            
            if not participant:
                return {"error": "Participant not found"}, 404
            
            # Mark the participant as read using the model method
            participant.mark_as_read()
            
            return {
                "success": True, 
                "message": "Conversation marked as read",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "unread_count": participant.unread_count,
                "last_read_at": participant.last_read_at.isoformat()
            }, 200
            
        except Exception as e:
            print(f"Error marking conversation as read: {str(e)}")
            return {"error": f"Failed to mark conversation as read: {str(e)}"}, 500
            