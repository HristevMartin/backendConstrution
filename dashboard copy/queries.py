from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict

class DashboardQueries:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27018/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client.travelDB
        self.page_visits = self.db.page_visits
    
    def get_total_visits(self) -> int:
        """Get total number of page visits"""
        return self.page_visits.count_documents({})
    
    def get_unique_visitors(self) -> int:
        """Get count of unique IP addresses"""
        unique_ips = self.page_visits.distinct("ip_address")
        return len(unique_ips) if unique_ips else 0
    
    def get_visits_by_page(self) -> pd.DataFrame:
        """Get visit count grouped by page"""
        pipeline = [
            {"$group": {
                "_id": "$page",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['page', 'count'])
        
        return pd.DataFrame(results).rename(columns={"_id": "page"})
    
    def get_visits_over_time(self, days: int = 7) -> pd.DataFrame:
        """Get visits grouped by date"""
        start_date = datetime.now() - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "created_at": {"$gte": start_date}
            }},
            {"$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at"
                    }
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['date', 'count'])
        
        df = pd.DataFrame(results).rename(columns={"_id": "date"})
        df['date'] = pd.to_datetime(df['date'])
        return df

    def get_device_breakdown(self) -> pd.DataFrame:
        """Get visits grouped by device type"""
        pipeline = [
            {"$group": {
                "_id": "$device_type",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['device_type', 'count'])
        
        return pd.DataFrame(results).rename(columns={"_id": "device_type"})
    
    def get_browser_breakdown(self) -> pd.DataFrame:
        """Get visits grouped by browser"""
        pipeline = [
            {"$group": {
                "_id": "$browser",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['browser', 'count'])
        
        return pd.DataFrame(results).rename(columns={"_id": "browser"})
    
    def get_os_breakdown(self) -> pd.DataFrame:
        """Get visits grouped by operating system"""
        pipeline = [
            {"$group": {
                "_id": "$os",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['os', 'count'])
        
        return pd.DataFrame(results).rename(columns={"_id": "os"})
    
    def get_top_referrers(self, limit: int = 10) -> pd.DataFrame:
        """Get top referrer sources"""
        pipeline = [
            {"$match": {
                "referrer": {"$exists": True, "$ne": ""}
            }},
            {"$group": {
                "_id": "$referrer",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['referrer', 'count'])
        
        return pd.DataFrame(results).rename(columns={"_id": "referrer"})
    
    def get_recent_visits(self, limit: int = 50) -> pd.DataFrame:
        """Get most recent visits"""
        visits = list(self.page_visits.find().sort("created_at", -1).limit(limit))
        
        if not visits:
            return pd.DataFrame(columns=['page', 'url', 'device_type', 'browser', 'os', 'created_at'])
        
        return pd.DataFrame(visits)

    def get_unique_ips_by_page(self, page: str = "home") -> pd.DataFrame:
        """Get unique IP addresses that visited a specific page with their visit counts"""
        pipeline = [
            {"$match": {"page": page}},
            {"$group": {
                "_id": "$ip_address",
                "visit_count": {"$sum": 1},
                "last_visit": {"$max": "$created_at"},
                "first_visit": {"$min": "$created_at"}
            }},
            {"$sort": {"visit_count": -1}}
        ]
        results = list(self.page_visits.aggregate(pipeline))
        
        if not results:
            return pd.DataFrame(columns=['ip_address', 'visit_count', 'last_visit', 'first_visit'])
        
        return pd.DataFrame(results).rename(columns={"_id": "ip_address"})

    def get_visitor_details_by_ip(self, ip_address: str) -> pd.DataFrame:
        """Get all visits from a specific IP address"""
        visits = list(self.page_visits.find(
            {"ip_address": ip_address}
        ).sort("created_at", -1))
        
        if not visits:
            return pd.DataFrame(columns=['page', 'url', 'device_type', 'browser', 'os', 'created_at'])
        
        return pd.DataFrame(visits)