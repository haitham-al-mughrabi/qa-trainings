#!/usr/bin/env python3
"""
Knowledge Assessment Data Verification Script

This script verifies the integrity of knowledge assessment data by:
1. Checking for orphaned assessments (assessments with no matching skill)
2. Identifying active skills with no assessments
3. Reporting data consistency issues
"""

from app import app, db
from models import KnowledgeSkill, KnowledgeAssessment, Student

def verify_knowledge_data():
    """Verify knowledge assessment data integrity"""
    
    with app.app_context():
        print("=" * 60)
        print("Knowledge Assessment Data Verification")
        print("=" * 60)
        print()
        
        # Get all active skills
        active_skills = KnowledgeSkill.query.filter_by(is_active=True).all()
        print(f"📊 Total Active Skills: {len(active_skills)}")
        
        # Get all assessments
        all_assessments = KnowledgeAssessment.query.all()
        print(f"📊 Total Assessments: {len(all_assessments)}")
        
        # Get all students
        all_students = Student.query.all()
        print(f"📊 Total Students: {len(all_students)}")
        print()
        
        # Create a set of valid topics from active skills
        valid_skills = {skill.topic for skill in active_skills}
        
        # Check for orphaned assessments
        print("-" * 60)
        print("Checking for Orphaned Assessments...")
        print("-" * 60)
        
        orphaned_assessments = []
        for assessment in all_assessments:
            if assessment.topic not in valid_skills:
                orphaned_assessments.append(assessment)
        
        if orphaned_assessments:
            print(f"⚠️  Found {len(orphaned_assessments)} orphaned assessment(s):")
            print()
            for assessment in orphaned_assessments:
                student = Student.query.get(assessment.student_id)
                student_name = student.name if student else "Unknown Student"
                print(f"  • ID: {assessment.id}")
                print(f"    Student: {student_name} (ID: {assessment.student_id})")
                print(f"    Topic: {assessment.topic}")
                print(f"    Proficiency: {assessment.proficiency_level}")
                print()
        else:
            print("✅ No orphaned assessments found!")
        print()
        
        # Check for skills with no assessments
        print("-" * 60)
        print("Checking for Skills Without Assessments...")
        print("-" * 60)
        
        skills_without_assessments = []
        for skill in active_skills:
            assessment_count = KnowledgeAssessment.query.filter_by(
                topic=skill.topic
            ).count()
            
            if assessment_count == 0:
                skills_without_assessments.append(skill)
        
        if skills_without_assessments:
            print(f"ℹ️  Found {len(skills_without_assessments)} skill(s) with no assessments:")
            print()
            for skill in skills_without_assessments:
                print(f"  • Category: {skill.category}")
                print(f"    Topic: {skill.topic}")
                print()
        else:
            print("✅ All active skills have at least one assessment!")
        print()
        
        # Summary of all skills
        print("-" * 60)
        print("All Active Skills")
        print("-" * 60)
        
        for skill in active_skills:
            assessment_count = KnowledgeAssessment.query.filter_by(
                topic=skill.topic
            ).count()
            print(f"\n📌 {skill.topic}")
            print(f"   Assessments: {assessment_count}")
        
        print()
        print("=" * 60)
        print("Verification Complete")
        print("=" * 60)
        
        # Return summary
        return {
            'total_skills': len(active_skills),
            'total_assessments': len(all_assessments),
            'orphaned_assessments': len(orphaned_assessments),
            'skills_without_assessments': len(skills_without_assessments)
        }

if __name__ == '__main__':
    summary = verify_knowledge_data()
    
    # Exit with error code if issues found
    if summary['orphaned_assessments'] > 0:
        print("\n⚠️  WARNING: Orphaned assessments detected!")
        exit(1)
    else:
        print("\n✅ All data integrity checks passed!")
        exit(0)
