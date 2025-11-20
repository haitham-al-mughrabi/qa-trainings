import pandas as pd
from app import app, db
from models import Training, Topic, Student

def seed_database():
    file_path = '/Users/TKM-h.almughrabi-c/Downloads/qa-trainings/QA Training Plan.xlsx'
    xls = pd.ExcelFile(file_path)
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Extract Students from 'Python Training' sheet
        # Row 1 (index 1) contains student names
        df_python = pd.read_excel(xls, sheet_name='Python Training', header=None)
        student_row = df_python.iloc[1]
        student_names = [name for name in student_row if pd.notna(name) and isinstance(name, str) and name.strip() != 'Team Members']
        
        print(f"Found students: {student_names}")
        for name in student_names:
            if not Student.query.filter_by(name=name).first():
                db.session.add(Student(name=name))
        
        db.session.commit()
        
        # Process Sheets
        for sheet_name in xls.sheet_names:
            if sheet_name == 'Trainings':
                continue
                
            print(f"Processing sheet: {sheet_name}")
            training = Training(name=sheet_name, slug=sheet_name.lower().replace(' ', '-'), description=f"Training for {sheet_name}")
            db.session.add(training)
            db.session.commit()
            
            # Determine header row based on sheet name
            header_row = 2
            if sheet_name == 'Database Sessions':
                header_row = 3  # Based on inspection, data starts later
            elif sheet_name == 'Mocking Sessions':
                # Check if sheet has enough rows
                df_check = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                if len(df_check) <= 3:
                    print(f"Skipping {sheet_name}: Sheet appears empty or has insufficient data.")
                    continue
                header_row = 3
            
            # Read topics
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
                
                # Rename columns to ensure we can access them
                # Col 0: Phases, Col 1: Topics, Col 2: Instructor, Col 3: Video URL
                if len(df.columns) >= 4:
                    df.rename(columns={
                        df.columns[0]: 'Phases', 
                        df.columns[1]: 'Topics', 
                        df.columns[2]: 'Instructor',
                        df.columns[3]: 'Video_URL'
                    }, inplace=True)
                elif len(df.columns) >= 3:
                    df.rename(columns={
                        df.columns[0]: 'Phases', 
                        df.columns[1]: 'Topics',
                        df.columns[2]: 'Instructor'
                    }, inplace=True)
                elif len(df.columns) >= 2:
                    df.rename(columns={df.columns[0]: 'Phases', df.columns[1]: 'Topics'}, inplace=True)
                
                # Forward-fill phase values (handles merged cells in Excel)
                if 'Phases' in df.columns:
                    df['Phases'] = df['Phases'].ffill()
                
                # Check if 'Phases' and 'Topics' columns exist
                if 'Phases' in df.columns and 'Topics' in df.columns:
                    for index, row in df.iterrows():
                        if pd.notna(row['Topics']):
                            topic = Topic(
                                training_id=training.id,
                                name=row['Topics'],
                                phase=row['Phases'] if pd.notna(row['Phases']) else None,
                                instructor=row['Instructor'] if 'Instructor' in df.columns and pd.notna(row['Instructor']) else None,
                                video_url=row['Video_URL'] if 'Video_URL' in df.columns and pd.notna(row['Video_URL']) else None,
                                order=index
                            )
                            db.session.add(topic)
                else:
                    print(f"Skipping {sheet_name}: Could not map columns. Columns: {df.columns}")
            except Exception as e:
                print(f"Error processing {sheet_name}: {e}")
                
            db.session.commit()
            
    print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
