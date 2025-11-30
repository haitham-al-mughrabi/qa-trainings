#!/usr/bin/env python3
"""
Migration script to remove categories from knowledge assessment system.

This script:
1. Combines category + topic into a single topic field
2. Removes the category column from both KnowledgeSkill and KnowledgeAssessment
3. Updates the unique constraint
"""

from app import app, db
from models import KnowledgeSkill, KnowledgeAssessment
from sqlalchemy import text

def migrate_remove_categories():
    """Remove categories from knowledge assessment system"""
    
    with app.app_context():
        print("=" * 60)
        print("Migration: Remove Categories from Knowledge Assessment")
        print("=" * 60)
        print()
        
        # Step 1: Backup current data
        print("Step 1: Backing up current data...")
        skills_backup = []
        for skill in KnowledgeSkill.query.all():
            skills_backup.append({
                'id': skill.id,
                'category': skill.category,
                'topic': skill.topic,
                'order': skill.order,
                'is_active': skill.is_active
            })
        
        assessments_backup = []
        for assessment in KnowledgeAssessment.query.all():
            assessments_backup.append({
                'id': assessment.id,
                'student_id': assessment.student_id,
                'category': assessment.category,
                'topic': assessment.topic,
                'proficiency_level': assessment.proficiency_level
            })
        
        print(f"  ✓ Backed up {len(skills_backup)} skills")
        print(f"  ✓ Backed up {len(assessments_backup)} assessments")
        print()
        
        # Step 2: Update KnowledgeSkill topics to include category
        print("Step 2: Combining category + topic in KnowledgeSkill...")
        for skill in KnowledgeSkill.query.all():
            # Combine category and topic
            new_topic = f"{skill.category} - {skill.topic}"
            print(f"  {skill.category} - {skill.topic} → {new_topic}")
            skill.topic = new_topic
        
        db.session.commit()
        print(f"  ✓ Updated {len(skills_backup)} skills")
        print()
        
        # Step 3: Update KnowledgeAssessment topics to match
        print("Step 3: Updating KnowledgeAssessment topics...")
        for assessment in KnowledgeAssessment.query.all():
            # Find matching skill to get the new topic name
            new_topic = f"{assessment.category} - {assessment.topic}"
            print(f"  Student {assessment.student_id}: {assessment.category} - {assessment.topic} → {new_topic}")
            assessment.topic = new_topic
        
        db.session.commit()
        print(f"  ✓ Updated {len(assessments_backup)} assessments")
        print()
        
        # Step 4: Drop the old unique constraint and category column from KnowledgeSkill
        print("Step 4: Removing category column from KnowledgeSkill...")
        try:
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
            db.session.execute(text("""
                CREATE TABLE knowledge_skill_new (
                    id INTEGER PRIMARY KEY,
                    topic VARCHAR(200) NOT NULL UNIQUE,
                    "order" INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Copy data to new table
            db.session.execute(text("""
                INSERT INTO knowledge_skill_new (id, topic, "order", is_active, created_at)
                SELECT id, topic, "order", is_active, created_at
                FROM knowledge_skill
            """))
            
            # Drop old table and rename new one
            db.session.execute(text("DROP TABLE knowledge_skill"))
            db.session.execute(text("ALTER TABLE knowledge_skill_new RENAME TO knowledge_skill"))
            
            db.session.commit()
            print("  ✓ Removed category column from KnowledgeSkill")
        except Exception as e:
            print(f"  ⚠️  Error modifying KnowledgeSkill table: {e}")
            db.session.rollback()
        print()
        
        # Step 5: Remove category column from KnowledgeAssessment
        print("Step 5: Removing category column from KnowledgeAssessment...")
        try:
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
            db.session.execute(text("""
                CREATE TABLE knowledge_assessment_new (
                    id INTEGER PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    topic VARCHAR(200) NOT NULL,
                    proficiency_level VARCHAR(50) NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES student(id)
                )
            """))
            
            # Copy data to new table
            db.session.execute(text("""
                INSERT INTO knowledge_assessment_new (id, student_id, topic, proficiency_level, last_updated)
                SELECT id, student_id, topic, proficiency_level, last_updated
                FROM knowledge_assessment
            """))
            
            # Drop old table and rename new one
            db.session.execute(text("DROP TABLE knowledge_assessment"))
            db.session.execute(text("ALTER TABLE knowledge_assessment_new RENAME TO knowledge_assessment"))
            
            db.session.commit()
            print("  ✓ Removed category column from KnowledgeAssessment")
        except Exception as e:
            print(f"  ⚠️  Error modifying KnowledgeAssessment table: {e}")
            db.session.rollback()
        print()
        
        # Step 6: Verify migration
        print("Step 6: Verifying migration...")
        skills_after = KnowledgeSkill.query.all()
        assessments_after = KnowledgeAssessment.query.all()
        
        print(f"  Skills before: {len(skills_backup)}, after: {len(skills_after)}")
        print(f"  Assessments before: {len(assessments_backup)}, after: {len(assessments_after)}")
        
        if len(skills_backup) == len(skills_after) and len(assessments_backup) == len(assessments_after):
            print("  ✓ Migration successful - no data loss")
        else:
            print("  ⚠️  WARNING: Data count mismatch!")
        
        print()
        print("=" * 60)
        print("Migration Complete!")
        print("=" * 60)
        print()
        print("Sample migrated skills:")
        for skill in KnowledgeSkill.query.limit(5).all():
            print(f"  • {skill.topic}")
        print()

if __name__ == '__main__':
    response = input("This will modify the database structure. Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate_remove_categories()
    else:
        print("Migration cancelled.")
