import pandas as pd
from app import app
from models import db, Student, KnowledgeAssessment

def import_knowledge_assessments():
    """Import knowledge assessments from QA Training Roadmap.xlsx"""
    
    # Read the Excel file
    df = pd.read_excel('QA Training Roadmap.xlsx', sheet_name='Sheet1')
    
    # Column mapping for each category and topic (0-indexed)
    # Structure: Category -> Topic -> [Beginner_col, Intermediate_col, Advance_col, Expert_col]
    column_mapping = {
        'Automation': {
            'Python - Testing level': [2, 3, 4, 5],  # Columns C, D, E, F
            'Robot Framework': [6, 7, 8, 9]           # Columns G, H, I, J
        },
        'Performance': {
            'Javascript - Testing level': [10, 11, 12, 13],  # Columns K, L, M, N
            'K6': [14, 15, 16, 17]                            # Columns O, P, Q, R
        },
        'API': {
            'Postman': [18, 19, 20, 21],   # Columns S, T, U, V
            'Mocking': [22, 23, 24, 25]    # Columns W, X, Y, Z
        },
        'Database': {
            'SQL': [26, 27, 28]  # Columns AA, AB, AC (only 3 columns in Excel)
        }
    }
    
    level_names = ['Beginner', 'Intermediate', 'Advance', 'Expert']
    
    with app.app_context():
        # Clear existing assessments
        KnowledgeAssessment.query.delete()
        db.session.commit()
        
        print("Importing knowledge assessments from Excel...")
        print(f"Total rows in Excel: {len(df)}")
        
        # Skip header rows (first 2 rows)
        imported_count = 0
        for idx, row in df.iterrows():
            if idx < 2:  # Skip header rows
                continue
                
            student_name = row.iloc[0]  # First column is Team Member
            
            if pd.isna(student_name) or str(student_name).strip() == '':
                continue
            
            # Find or create student
            student = Student.query.filter_by(name=student_name).first()
            if not student:
                print(f"\nCreating student: {student_name}")
                student = Student(name=student_name)
                db.session.add(student)
                db.session.flush()  # Get the ID
            else:
                print(f"\nProcessing student: {student_name}")
            
            # Process each category and topic
            for category, topics in column_mapping.items():
                for topic, col_indices in topics.items():
                    # Check which level is True for this student/topic
                    for level_idx, col_idx in enumerate(col_indices):
                        try:
                            value = row.iloc[col_idx]
                            
                            # Check if this level is marked as True
                            if value == True or str(value).lower() == 'true':
                                # Handle case where Database might only have 3 levels
                                if level_idx < len(level_names):
                                    proficiency_level = level_names[level_idx]
                                    
                                    # Create assessment
                                    assessment = KnowledgeAssessment(
                                        student_id=student.id,
                                        category=category,
                                        topic=topic,
                                        proficiency_level=proficiency_level
                                    )
                                    db.session.add(assessment)
                                    print(f"  ✓ {category}/{topic}: {proficiency_level}")
                                    imported_count += 1
                                    break  # Only one level should be True per topic
                        except IndexError:
                            # Column doesn't exist, skip
                            continue
        
        db.session.commit()
        print("\n" + "="*50)
        print("✅ Import completed successfully!")
        print("="*50)
        
        # Print summary
        total_assessments = KnowledgeAssessment.query.count()
        total_students = Student.query.count()
        print(f"\nSummary:")
        print(f"  Total students: {total_students}")
        print(f"  Total assessments imported: {imported_count}")
        print(f"  Total assessments in DB: {total_assessments}")

if __name__ == '__main__':
    import_knowledge_assessments()

