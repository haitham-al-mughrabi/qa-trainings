from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Training(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    topics = db.relationship('Topic', backref='training', lazy=True)

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
