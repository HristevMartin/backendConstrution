#!/usr/bin/env python3
"""
Utility script to pre-cache geolocation data for all IPs in the database.
This can be run periodically or before using the dashboard to improve performance.
"""

from queries import DashboardQueries
import time

def batch_geolocate_ips():
    """
    Fetch and cache geolocation data for all unique IPs in the database.
    """
    print("🌍 Starting batch IP geolocation...")
    
    queries = DashboardQueries()
    
    # Get all unique IPs
    unique_ips = queries.page_visits.distinct("ip_address")
    total_ips = len(unique_ips)
    
    print(f"Found {total_ips} unique IP addresses")
    
    # Check which ones are already cached
    cached_ips = set()
    for doc in queries.ip_cache.find({}, {"ip_address": 1}):
        cached_ips.add(doc["ip_address"])
    
    uncached_ips = [ip for ip in unique_ips if ip not in cached_ips]
    
    print(f"Already cached: {len(cached_ips)}")
    print(f"Need to fetch: {len(uncached_ips)}")
    
    if not uncached_ips:
        print("✅ All IPs are already cached!")
        return
    
    # Process uncached IPs
    print(f"\n🔄 Fetching geolocation data...")
    
    for i, ip in enumerate(uncached_ips, 1):
        print(f"[{i}/{len(uncached_ips)}] Processing {ip}...", end=" ")
        
        try:
            geo_data = queries.get_ip_geolocation(ip)
            
            if geo_data.get('country', 'Unknown') != 'Unknown':
                print(f"✅ {geo_data['city']}, {geo_data['country']}")
            else:
                print("⚠️  Location unknown")
            
            # Rate limiting: 45 requests per minute = ~1.3s between requests
            # Using 1.5s to be safe
            time.sleep(1.5)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print(f"\n✅ Batch geolocation complete!")
    print(f"Total IPs cached: {len(cached_ips) + len(uncached_ips)}")

def show_geolocation_stats():
    """
    Display statistics about cached geolocation data.
    """
    queries = DashboardQueries()
    
    print("\n📊 Geolocation Cache Statistics")
    print("=" * 50)
    
    # Total cached IPs
    total_cached = queries.ip_cache.count_documents({})
    print(f"Total cached IPs: {total_cached}")
    
    # Countries
    countries = queries.ip_cache.distinct("country")
    print(f"Unique countries: {len([c for c in countries if c != 'Unknown'])}")
    
    # Top countries
    pipeline = [
        {"$match": {"country": {"$ne": "Unknown"}}},
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    top_countries = list(queries.ip_cache.aggregate(pipeline))
    
    if top_countries:
        print("\nTop 10 countries:")
        for i, country in enumerate(top_countries, 1):
            print(f"  {i}. {country['_id']}: {country['count']} IPs")
    
    # ISPs
    isps = queries.ip_cache.distinct("isp")
    print(f"\nUnique ISPs: {len([i for i in isps if i != 'Unknown'])}")
    
    # Show sample
    print("\n📋 Sample cached entries:")
    for doc in queries.ip_cache.find().limit(5):
        print(f"  {doc['ip_address']}: {doc['city']}, {doc['country']} ({doc['isp']})")

def clear_cache():
    """
    Clear all cached geolocation data. Use with caution!
    """
    queries = DashboardQueries()
    
    response = input("⚠️  Are you sure you want to clear all cached geolocation data? (yes/no): ")
    
    if response.lower() == 'yes':
        result = queries.ip_cache.delete_many({})
        print(f"✅ Cleared {result.deleted_count} cached entries")
    else:
        print("❌ Cache clear cancelled")

if __name__ == "__main__":
    import sys
    
    print("""
╔══════════════════════════════════════════════════════════╗
║        IP Geolocation Cache Utility                      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "batch":
            batch_geolocate_ips()
        elif command == "stats":
            show_geolocation_stats()
        elif command == "clear":
            clear_cache()
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python geo_utils.py batch   - Pre-cache all IPs")
            print("  python geo_utils.py stats   - Show cache statistics")
            print("  python geo_utils.py clear   - Clear all cache (careful!)")
    else:
        print("Choose an action:")
        print("1. Batch geolocate all IPs")
        print("2. Show cache statistics")
        print("3. Clear cache")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ")
        
        if choice == "1":
            batch_geolocate_ips()
        elif choice == "2":
            show_geolocation_stats()
        elif choice == "3":
            clear_cache()
        elif choice == "4":
            print("Goodbye!")
        else:
            print("Invalid choice")
