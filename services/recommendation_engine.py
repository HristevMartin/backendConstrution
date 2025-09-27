# File: services/recommendation_service.py

from datetime import datetime, timedelta
import requests
from collections import defaultdict

class ProjectRecommendationEngine:
    """
    Handles all project recommendation logic including:
    - Geographic proximity calculations
    - User preference matching
    - Project categorization and ranking
    """
    
    def __init__(self, postcode_api_key=None):
        self.postcode_api_key = postcode_api_key
        self.base_postcode_url = "http://api.postcodes.io"
    
    def get_postcode_distance(self, postcode1, postcode2):
        """Calculate distance between two UK postcodes using Postcodes.io API"""
        try:
            # Normalize postcodes (remove spaces, uppercase)
            pc1 = postcode1.replace(" ", "").upper()
            pc2 = postcode2.replace(" ", "").upper()
            
            if pc1 == pc2:
                return 0
                
            # Get coordinates for both postcodes
            url = f"{self.base_postcode_url}/postcodes/{pc1}"
            response1 = requests.get(url, timeout=2)
            url = f"{self.base_postcode_url}/postcodes/{pc2}"
            response2 = requests.get(url, timeout=2)
            
            if response1.status_code == 200 and response2.status_code == 200:
                coord1 = response1.json()['result']
                coord2 = response2.json()['result']
                
                # Calculate distance using Haversine formula
                from math import radians, sin, cos, sqrt, atan2
                
                lat1, lon1 = radians(coord1['latitude']), radians(coord1['longitude'])
                lat2, lon2 = radians(coord2['latitude']), radians(coord2['longitude'])
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance_km = 6371 * c
                distance_miles = distance_km * 0.621371
                
                return round(distance_miles, 2)
        except Exception as e:
            print(f"Error calculating distance: {e}")
            # Fallback: simple postcode area matching
            area1 = postcode1.replace(" ", "")[:4].upper()
            area2 = postcode2.replace(" ", "")[:4].upper()
            return 0 if area1 == area2 else 50  # Assume 50 miles if different areas
        
        return 999  # Unknown distance
    
    def get_user_recommendations(self, user_postcode, projects_list, user_preferences=None):
        """
        Generate personalized recommendations based on user location and preferences
        """
        # Set default radius preferences
        default_preferences = {
            'max_radius_miles': 25,
            'preferred_radius_miles': 10,
        }
        
        # Merge user preferences with defaults
        prefs = {**default_preferences, **(user_preferences or {})}
        
        recommendations = {
            'immediate_nearby': []
        }
        
        # Process each project
        for project in projects_list:
            project_copy = project.copy()
            
            # Calculate distance
            distance = self.get_postcode_distance(user_postcode, project.get('postcode', ''))
            project_copy['distance_miles'] = distance
            
            # Skip projects outside max radius
            if distance > prefs['max_radius_miles']:
                continue
            
            # Categorize projects
            self._categorize_project(project_copy, recommendations, distance, prefs)
        
        # Sort and return all results
        return self._sort_and_limit_recommendations(recommendations)
    
    def _categorize_project(self, project, recommendations, distance, preferences):
        """Categorize a single project into recommendation buckets"""
        preferred_radius = preferences['preferred_radius_miles']
        
        # Immediate nearby (within preferred radius)
        if distance <= preferred_radius:
            recommendations['immediate_nearby'].append(project)
    
    def _sort_and_limit_recommendations(self, recommendations):
        """Sort recommendation category and return all results"""
        recommendations['immediate_nearby'] = sorted(
            recommendations['immediate_nearby'], 
            key=lambda x: x['distance_miles']  # Sort by distance only
        )  # No limit - return all projects
        
        return recommendations


class UserService:
    """
    Handles user-related business logic for recommendations
    """
    
    @staticmethod
    def get_user_preferences(trader_profile):
        """Extract user preferences from trader profile"""
        # Convert radiusKm to miles (1 km = 0.621371 miles)
        radius_km = float(getattr(trader_profile, 'radiusKm', 15))  # Default 15km if not set
        radius_miles = round(radius_km * 0.621371, 1)
        
        return {
            'max_radius_miles': radius_miles,
            'preferred_radius_miles': radius_miles,  # Use same value for both
        }
    
    @staticmethod
    def get_recommendation_explanations(user_postcode, preferences):
        """Generate user-friendly explanations for each recommendation category"""
        return {
            'immediate_nearby': f"Projects within {preferences['preferred_radius_miles']} miles of {user_postcode}",
        }