from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association table for many-to-many relationship between Training and Instructor
training_instructors = db.Table('training_instructors',
    db.Column('training_id', db.Integer, db.ForeignKey('training.id'), primary_key=True),
    db.Column('instructor_id', db.Integer, db.ForeignKey('instructor.id'), primary_key=True),
    db.Column('is_primary', db.Boolean, default=False)
)

class Training(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=True)  # Made nullable
    description = db.Column(db.Text, nullable=True)
    topics = db.relationship('Topic', backref='training', lazy=True, cascade='all, delete-orphan')
    instructors = db.relationship('Instructor', secondary=training_instructors, backref=db.backref('trainings', lazy='dynamic'))

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    phase = db.Column(db.String(50))
    instructor = db.Column(db.String(100))
    video_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    order = db.Column(db.Integer)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(200))  # e.g., "Senior QA Engineer"
    bio = db.Column(db.Text)
    expertise = db.Column(db.Text)  # Comma-separated tags or JSON
    email = db.Column(db.String(100))
    photo_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    date = db.Column(db.Date)
    status = db.Column(db.String(20))  # Present, Absent, Excused

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    status = db.Column(db.String(20))  # Not Started, In Progress, Completed

class KnowledgeAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # e.g., "Automation", "Performance", "API", "Database"
    topic = db.Column(db.String(200), nullable=False)  # e.g., "Python - Testing level", "Robot Framework"
    proficiency_level = db.Column(db.String(50), nullable=False)  # Beginner, Intermediate, Advance, Expert
    last_updated = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    student = db.relationship('Student', backref='knowledge_assessments', lazy=True)

class KnowledgeSkill(db.Model):
    """Defines available skills/topics that can be assessed"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    # Ensure unique combination of category and topic
    __table_args__ = (db.UniqueConstraint('category', 'topic', name='unique_category_topic'),)

class Certificate(db.Model):
    """Certificates issued to students upon training completion"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    training_id = db.Column(db.Integer, db.ForeignKey('training.id'), nullable=True)
    
    # Customizable Certificate Fields
    certificate_title = db.Column(db.String(200), default="CERTIFICATE OF COMPLETION")
    student_name = db.Column(db.String(200), nullable=False)  # Can override student.name
    course_name = db.Column(db.String(300), nullable=False)
    certificate_text = db.Column(db.Text, default="has successfully completed the comprehensive training program in")
    
    # Dates
    completion_date = db.Column(db.Date, nullable=False)
    issue_date = db.Column(db.DateTime, default=db.func.now())
    
    # Signatures (up to 3)
    signature_1_name = db.Column(db.String(100))
    signature_1_title = db.Column(db.String(200))
    signature_2_name = db.Column(db.String(100))
    signature_2_title = db.Column(db.String(200))
    signature_3_name = db.Column(db.String(100))
    signature_3_title = db.Column(db.String(200))
    
    # Seal
    seal_text = db.Column(db.String(100), default="OFFICIAL\\nSEAL")
    
    # Verification
    unique_code = db.Column(db.String(50), unique=True, nullable=False)
    is_issued = db.Column(db.Boolean, default=False)
    
    # Relationships
    student = db.relationship('Student', backref='certificates', lazy=True)
    training = db.relationship('Training', backref='certificates', lazy=True)

