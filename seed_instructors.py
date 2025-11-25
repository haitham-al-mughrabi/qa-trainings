"""
Seed initial instructor data for the QA Training platform.
Run this script to populate the database with sample instructors.

Usage:
    python seed_instructors.py
"""

from app import app, db
from models import Instructor, Training

def seed_instructors():
    """Create sample instructor data"""
    
    with app.app_context():
        # Check if instructors already exist
        existing_count = Instructor.query.count()
        if existing_count > 0:
            print(f"⚠️  Database already has {existing_count} instructor(s). Skipping seed.")
            print("   Delete instructors from admin panel or database to re-seed.")
            return
        
        # Sample instructors
        instructors_data = [
            {
                'name': 'Haitham Al Mughrabi',
                'role': 'Senior QA Engineer & Testing Specialist',
                'bio': 'Experienced QA professional with over 10 years in software testing, automation, and performance engineering. Specializes in building robust test frameworks and mentoring QA teams.',
                'expertise': 'Python, Robot Framework, Postman, API Testing, Performance Testing, Test Automation, Mocking',
                'email': 'haitham@takamol-qa.com',
                'is_active': True
            },
            {
                'name': 'Basma Hassan',
                'role': 'Performance Engineer & k6 Specialist',
                'bio': 'Performance testing expert with deep knowledge of k6, load testing strategies, and performance optimization. Passionate about teaching scalable testing practices.',
                'expertise': 'k6, Performance Testing, Load Testing, GitLab CI/CD, Monitoring, Grafana',
                'email': 'basma@takamol-qa.com',
                'is_active': True
            },
            {
                'name': 'Lina Osman',
                'role': 'Database & SQL for QA',
                'bio': 'Database specialist focused on test data management, SQL for testers, and database verification strategies. Helps QA teams master data-driven testing.',
                'expertise': 'PostgreSQL, MySQL, SQL, Test Data Management, Database Testing, Data Validation',
                'email': 'lina@takamol-qa.com',
                'is_active': True
            }
        ]
        
        created_instructors = []
        for data in instructors_data:
            instructor = Instructor(**data)
            db.session.add(instructor)
            created_instructors.append(instructor)
        
        db.session.commit()
        
        print(f"✅ Successfully created {len(created_instructors)} instructors:")
        for instructor in created_instructors:
            print(f"   - {instructor.name} ({instructor.role})")
        
        # Optionally link to trainings if they exist
        trainings = Training.query.all()
        if trainings:
            print(f"\n📚 Found {len(trainings)} training(s). You can link instructors via the admin panel.")
        else:
            print("\n💡 No trainings found. Create trainings first, then link instructors via admin panel.")

if __name__ == '__main__':
    print("🌱 Seeding instructor data...\n")
    seed_instructors()
    print("\n✨ Done! Visit http://localhost:6500/admin/instructors to manage instructors.")
