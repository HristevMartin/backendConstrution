
from datetime import datetime
from flask import request, jsonify
from flask_restful import Resource
from models.page_visit import PageVisit
import user_agents


class SimplePageTrackingResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            
            if not data:
                return {'status': 'error', 'message': 'No data provided'}, 400

            print('track visit data is', data)
            
            # Get real IP address
            def get_real_ip():
                if request.headers.get('X-Forwarded-For'):
                    return request.headers.get('X-Forwarded-For').split(',')[0].strip()
                elif request.headers.get('X-Real-IP'):
                    return request.headers.get('X-Real-IP')
                else:
                    return request.remote_addr
            
            ip_address = get_real_ip()
            user_agent_string = data.get('userAgent') or request.headers.get('User-Agent', '')
            
            # Parse user agent for device/browser info
            ua = user_agents.parse(user_agent_string)
            device_type = 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'desktop'
            
            # Parse timestamp from frontend or use current time
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                try:
                    # Assuming ISO format from frontend
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            # Create PageVisit record
            page_visit = PageVisit(
                page=data.get('page', ''),
                url=data.get('url', ''),
                ip_address=ip_address,
                user_agent=user_agent_string,
                timestamp=timestamp,
                referrer=data.get('referrer') or request.headers.get('Referer'),
                session_id=data.get('sessionId'),
                device_type=device_type,
                browser=f"{ua.browser.family} {ua.browser.version_string}" if ua.browser.family else None,
                os=f"{ua.os.family} {ua.os.version_string}" if ua.os.family else None
            )
            
            # Save to database
            page_visit.save()
            
            # Log all the data we received (keep for debugging)
            print("=" * 50)
            print("PAGE VISIT TRACKED & SAVED TO DB")
            print("=" * 50)
            print(f"Record ID: {page_visit.id}")
            print(f"IP Address: {ip_address}")
            print(f"Page: {data.get('page')}")
            print(f"Timestamp: {timestamp}")
            print(f"User Agent: {user_agent_string}")
            print(f"URL: {data.get('url')}")
            print(f"Device Type: {device_type}")
            print(f"Browser: {page_visit.browser}")
            print(f"OS: {page_visit.os}")
            print("=" * 50)
            
            return {
                'status': 'success', 
                'id': str(page_visit.id),
                'ip_captured': ip_address,
                'device_type': device_type,
                'message': 'Visit tracked and saved to database successfully'
            }, 200
            
        except Exception as e:
            print(f"Tracking error: {e}")
            return {'status': 'error', 'message': str(e)}, 500


class GetPageVisits(Resource):
    """Resource to retrieve page visit analytics"""
    
    def get(self):
        try:
            # Get query parameters for filtering
            page = request.args.get('page')
            limit = int(request.args.get('limit', 100))
            skip = int(request.args.get('skip', 0))
            
            # Build query
            query = {}
            if page:
                query['page'] = page
                
            # Get visits with pagination
            visits = PageVisit.objects(**query).order_by('-timestamp').skip(skip).limit(limit)
            
            # Convert to list of dictionaries
            visits_data = [visit.to_dict() for visit in visits]
            
            # Get total count for pagination
            total_count = PageVisit.objects(**query).count()
            
            return {
                'status': 'success',
                'data': visits_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'skip': skip,
                    'has_more': (skip + limit) < total_count
                }
            }, 200
            
        except Exception as e:
            print(f"Error retrieving page visits: {e}")
            return {'status': 'error', 'message': str(e)}, 500