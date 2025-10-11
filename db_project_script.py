"""
Script to ingest 50 mock client projects with different locations across England
This helps test the performance of the recommendation engine endpoint
"""

import sys
from datetime import datetime, timedelta
import random
import uuid
from app import create_app, db
from models.ClientProject import ClientProject

# UK Cities and their postcodes for realistic test data
UK_LOCATIONS = [
    {"city": "London", "postcodes": ["SW1A1AA", "E14 5AB", "NW1 6XE", "SE1 7PB", "W1D 3QU"]},
    {"city": "Manchester", "postcodes": ["M1 1AD", "M2 3DE", "M3 4FP", "M4 5JD", "M5 3EQ"]},
    {"city": "Birmingham", "postcodes": ["B1 1AA", "B2 4QA", "B3 1JJ", "B4 6AT", "B5 5SE"]},
    {"city": "Leeds", "postcodes": ["LS1 1BA", "LS2 7EY", "LS3 1AB", "LS4 2DD", "LS5 3BN"]},
    {"city": "Liverpool", "postcodes": ["L1 0AB", "L2 2DH", "L3 9AG", "L4 0TH", "L5 9SJ"]},
    {"city": "Bristol", "postcodes": ["BS1 4DJ", "BS2 0JA", "BS3 4AL", "BS4 3QY", "BS5 6XR"]},
    {"city": "Newcastle", "postcodes": ["NE1 1EE", "NE2 1JS", "NE3 1HH", "NE4 5TQ", "NE5 2EL"]},
    {"city": "Sheffield", "postcodes": ["S1 1DA", "S2 4SU", "S3 8PH", "S4 7WZ", "S5 6HF"]},
    {"city": "Nottingham", "postcodes": ["NG1 5AW", "NG2 3NG", "NG3 1AL", "NG4 2GP", "NG5 1PR"]},
    {"city": "Leicester", "postcodes": ["LE1 1QA", "LE2 0AL", "LE3 5FP", "LE4 0PA", "LE5 4QF"]},
    {"city": "Brighton", "postcodes": ["BN1 1AL", "BN2 1AA", "BN3 1DH", "BN41 1AF", "BN50 9PQ"]},
    {"city": "Southampton", "postcodes": ["SO14 0AA", "SO15 2JU", "SO16 4GX", "SO17 1BJ", "SO18 1GF"]},
    {"city": "Oxford", "postcodes": ["OX1 1AY", "OX2 0DP", "OX3 7LF", "OX4 1SL", "OX5 1GB"]},
    {"city": "Cambridge", "postcodes": ["CB1 1PT", "CB2 0AE", "CB3 0AX", "CB4 1LN", "CB5 8BS"]},
    {"city": "York", "postcodes": ["YO1 7LZ", "YO10 3FB", "YO23 1ND", "YO24 1AB", "YO31 7EB"]},
]

# Service categories for variety
SERVICE_CATEGORIES = [
    "Electrical",
    "Plumbing",
    "Carpentry",
    "Painting & Decorating",
    "Kitchen Fitting",
    "Bathroom Installation",
    "Roofing",
    "Plastering",
    "Tiling",
    "Flooring",
    "Building & Extensions",
    "Heating & Gas",
]

# Job titles corresponding to service categories
JOB_TITLES = {
    "Electrical": [
        "Rewiring 3-bedroom house",
        "Install new lighting fixtures",
        "Electrical fault finding",
        "Replace consumer unit",
        "Install electric car charging point",
    ],
    "Plumbing": [
        "Fix leaking tap",
        "Install new boiler",
        "Bathroom plumbing work",
        "Central heating repair",
        "Radiator installation",
    ],
    "Carpentry": [
        "Build custom wardrobe",
        "Install kitchen cabinets",
        "Repair wooden flooring",
        "Build garden deck",
        "Install new doors",
    ],
    "Painting & Decorating": [
        "Paint interior walls",
        "Exterior house painting",
        "Wallpaper installation",
        "Ceiling painting",
        "Feature wall decoration",
    ],
    "Kitchen Fitting": [
        "Full kitchen installation",
        "Replace kitchen worktops",
        "Install new kitchen units",
        "Kitchen refurbishment",
        "Fit integrated appliances",
    ],
    "Bathroom Installation": [
        "Full bathroom renovation",
        "Install new shower",
        "Replace bathroom suite",
        "Fit new bath",
        "Bathroom tiling",
    ],
    "Roofing": [
        "Roof repair",
        "Replace roof tiles",
        "Flat roof installation",
        "Gutter cleaning and repair",
        "Chimney work",
    ],
    "Plastering": [
        "Plaster living room walls",
        "Ceiling plastering",
        "Repair cracked plaster",
        "Skim coat walls",
        "Artex removal",
    ],
    "Tiling": [
        "Kitchen wall tiling",
        "Bathroom floor tiling",
        "Replace broken tiles",
        "Splash back tiling",
        "Tile grouting",
    ],
    "Flooring": [
        "Install laminate flooring",
        "Lay hardwood floor",
        "Vinyl flooring installation",
        "Carpet fitting",
        "Floor sanding",
    ],
    "Building & Extensions": [
        "Single storey extension",
        "Loft conversion",
        "Garage conversion",
        "Conservatory build",
        "Garden room construction",
    ],
    "Heating & Gas": [
        "Boiler service",
        "Install new radiators",
        "Gas safety check",
        "Underfloor heating",
        "Heating system repair",
    ],
}

# Budget ranges
BUDGETS = [
    "Under £500",
    "£500 - £1000",
    "£1000 - £2000",
    "£2000 - £5000",
    "£5000 - £10000",
    "£10000+",
    "Need quote",
]

# Urgency levels
URGENCIES = ["asap", "this_week", "this_month", "flexible"]

# Contact methods
CONTACT_METHODS = ["email", "phone", "whatsapp"]

# First names for variety
FIRST_NAMES = [
    "John", "Sarah", "Michael", "Emma", "David", "Jessica", "James", "Emily",
    "Robert", "Sophie", "William", "Olivia", "Thomas", "Charlotte", "Daniel",
    "Amelia", "Matthew", "Lily", "Andrew", "Grace", "Christopher", "Mia",
    "Joshua", "Ella", "Alexander", "Lucy", "Benjamin", "Sophia", "Jack", "Isabella",
]


def generate_mock_project(index):
    """Generate a single mock project with realistic data"""
    
    # Select location
    location_data = random.choice(UK_LOCATIONS)
    city = location_data["city"]
    postcode = random.choice(location_data["postcodes"]).replace(" ", "")
    
    # Select service and job title
    service_category = random.choice(SERVICE_CATEGORIES)
    job_title = random.choice(JOB_TITLES[service_category])
    
    # Generate user data
    first_name = random.choice(FIRST_NAMES)
    email = f"{first_name.lower()}.test{index}@example.com"
    phone = f"07{random.randint(100000000, 999999999)}"
    
    # Generate project data
    project_data = {
        "project_id": str(uuid.uuid4()),
        "user_id": f"test_user_{uuid.uuid4().hex[:24]}",
        "first_name": first_name,
        "email": email,
        "phone": phone,
        "contact_method": random.choice(CONTACT_METHODS),
        "job_title": job_title,
        "job_description": f"Looking for a reliable professional to {job_title.lower()}. " +
                          f"Property is located in {city}. " +
                          "Please provide a quote with timeline and references.",
        "location": city,
        "postcode": postcode,
        "budget": random.choice(BUDGETS),
        "urgency": random.choice(URGENCIES),
        "country": "GB",
        "service_category": service_category,
        "image_urls": [],
        "image_count": 0,
        "created_at": datetime.utcnow() - timedelta(days=random.randint(0, 30)),
        "updated_at": datetime.utcnow(),
        "status": random.choice(["pending", "contacted", "quoted"]),
        "is_deleted": False,
        "gdpr_consent": True,
        "additional_data": {
            "source": "mock_data_script",
            "test_project": True,
        }
    }
    
    return project_data


def ingest_mock_projects(count=50):
    """Ingest mock projects into the database"""
    
    print(f"\n{'='*60}")
    print(f"Starting to generate {count} mock projects...")
    print(f"{'='*60}\n")
    
    created_count = 0
    failed_count = 0
    
    for i in range(1, count + 1):
        try:
            project_data = generate_mock_project(i)
            
            # Create project using the model
            project = ClientProject(**project_data)
            project.save()
            
            created_count += 1
            print(f"✓ [{i}/{count}] Created: {project_data['job_title'][:40]} | "
                  f"{project_data['location']} ({project_data['postcode']})")
            
        except Exception as e:
            failed_count += 1
            print(f"✗ [{i}/{count}] Failed: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"Ingestion Complete!")
    print(f"{'='*60}")
    print(f"✓ Successfully created: {created_count} projects")
    if failed_count > 0:
        print(f"✗ Failed: {failed_count} projects")
    print(f"{'='*60}\n")
    
    # Show some statistics
    print("\nProject Distribution by City:")
    for location in UK_LOCATIONS:
        count = ClientProject.objects(
            location=location["city"], 
            additional_data__test_project=True
        ).count()
        if count > 0:
            print(f"  {location['city']}: {count} projects")
    
    print("\nProject Distribution by Service Category:")
    for category in SERVICE_CATEGORIES:
        count = ClientProject.objects(
            service_category=category,
            additional_data__test_project=True
        ).count()
        if count > 0:
            print(f"  {category}: {count} projects")


def cleanup_test_projects():
    """Remove all test projects created by this script"""
    print("\nCleaning up test projects...")
    
    try:
        result = ClientProject.objects(additional_data__test_project=True).delete()
        print(f"✓ Removed {result} test projects")
    except Exception as e:
        print(f"✗ Error during cleanup: {str(e)}")


def main():
    """Main execution function"""
    
    # Initialize Flask app and database
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("Mock Project Ingestion Script")
        print("="*60)
        
        # Check if user wants to clean up first
        if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
            cleanup_test_projects()
            return
        
        # Get count from command line or use default
        count = 50
        if len(sys.argv) > 1:
            try:
                count = int(sys.argv[1])
            except ValueError:
                print("Invalid count provided. Using default: 50")
        
        # Show existing test project count
        existing_count = ClientProject.objects(additional_data__test_project=True).count()
        if existing_count > 0:
            print(f"\n⚠ Warning: Found {existing_count} existing test projects")
            response = input("Do you want to remove them first? (y/n): ")
            if response.lower() == 'y':
                cleanup_test_projects()
                print()
        
        # Ingest projects
        ingest_mock_projects(count)
        
        # Total count
        total_projects = ClientProject.objects(is_deleted=False).count()
        print(f"\nTotal projects in database: {total_projects}")
        print("\n✓ Script completed successfully!")
        print("\nTo cleanup test projects, run:")
        print("  python db_project_script.py --cleanup\n")


if __name__ == "__main__":
    main()
