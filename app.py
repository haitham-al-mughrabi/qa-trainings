from flask import Flask, render_template, request, redirect, url_for
from models import db, Training, Topic, Student, Attendance, Progress
import os
import re

app = Flask(__name__, static_folder='statics', static_url_path='/statics')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trainings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Add custom Jinja2 filter for regex replacement
@app.template_filter('regex_replace')
def regex_replace(s, pattern, replacement):
    return re.sub(pattern, replacement, s)

@app.route('/')
def index():
    trainings = Training.query.all()
    return render_template('index.html', trainings=trainings)

@app.route('/trainings')
def trainings():
    trainings_list = Training.query.all()
    return render_template('trainings.html', trainings=trainings_list)


@app.route('/training/<int:training_id>')
def training_detail(training_id):
    training = Training.query.get_or_404(training_id)
    topics = Topic.query.filter_by(training_id=training_id).order_by(Topic.order).all()
    
    # Group topics by phase
    from collections import OrderedDict
    phases = OrderedDict()
    for topic in topics:
        phase = topic.phase if topic.phase else 'Other'
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(topic)
    
    return render_template('training.html', training=training, phases=phases)

@app.route('/topic/<int:topic_id>', methods=['GET', 'POST'])
def topic_detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'attendance':
            date = request.form.get('date')
            for key, value in request.form.items():
                if key.startswith('student_'):
                    student_id = int(key.split('_')[1])
                    status = value
                    
                    attendance_record = Attendance.query.filter_by(student_id=student_id, topic_id=topic_id, date=date).first()
                    if attendance_record:
                        attendance_record.status = status
                    else:
                        new_record = Attendance(student_id=student_id, topic_id=topic_id, date=date, status=status)
                        db.session.add(new_record)
            db.session.commit()
            
        elif action == 'progress':
            for key, value in request.form.items():
                if key.startswith('student_'):
                    student_id = int(key.split('_')[1])
                    status = value
                    
                    progress_record = Progress.query.filter_by(student_id=student_id, topic_id=topic_id).first()
                    if progress_record:
                        progress_record.status = status
                    else:
                        new_record = Progress(student_id=student_id, topic_id=topic_id, status=status)
                        db.session.add(new_record)
            db.session.commit()
            
        return redirect(url_for('topic_detail', topic_id=topic_id))

    students = Student.query.all()
    
    # Get progress for this topic to pre-fill form
    progress_map = {}
    progress_records = Progress.query.filter_by(topic_id=topic_id).all()
    for record in progress_records:
        progress_map[record.student_id] = record.status
        
    return render_template('topic.html', topic=topic, students=students, progress_map=progress_map)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        topic_id = request.form.get('topic_id')
        date = request.form.get('date')
        
        # Clear existing attendance for this topic/date to avoid duplicates (simplified logic)
        # In a real app, we might want to update instead of delete/insert
        # For now, let's just add new records
        
        for key, value in request.form.items():
            if key.startswith('student_'):
                student_id = int(key.split('_')[1])
                status = value
                
                # Check if exists
                attendance_record = Attendance.query.filter_by(student_id=student_id, topic_id=topic_id, date=date).first()
                if attendance_record:
                    attendance_record.status = status
                else:
                    new_record = Attendance(student_id=student_id, topic_id=topic_id, date=date, status=status)
                    db.session.add(new_record)
        
        db.session.commit()
        return redirect(url_for('attendance'))

    students = Student.query.all()
    trainings = Training.query.all()
    
    # Calculate attendance summary
    summary = {}
    for student in students:
        total = Attendance.query.filter_by(student_id=student.id).count()
        present = Attendance.query.filter_by(student_id=student.id, status='Present').count()
        summary[student.id] = {
            'total': total,
            'present': present,
            'percentage': int((present / total) * 100) if total > 0 else 0
        }
        
    return render_template('attendance.html', students=students, trainings=trainings, summary=summary)

@app.route('/progress', methods=['GET', 'POST'])
def progress():
    if request.method == 'POST':
        topic_id = request.form.get('topic_id')
        
        for key, value in request.form.items():
            if key.startswith('student_'):
                student_id = int(key.split('_')[1])
                status = value
                
                progress_record = Progress.query.filter_by(student_id=student_id, topic_id=topic_id).first()
                if progress_record:
                    progress_record.status = status
                else:
                    new_record = Progress(student_id=student_id, topic_id=topic_id, status=status)
                    db.session.add(new_record)
        
        db.session.commit()
        return redirect(url_for('progress'))

    students = Student.query.all()
    trainings = Training.query.all()
    
    # Calculate progress summary
    summary = {}
    total_topics = Topic.query.count()
    for student in students:
        completed = Progress.query.filter_by(student_id=student.id, status='Completed').count()
        summary[student.id] = {
            'completed': completed,
            'total': total_topics,
            'percentage': int((completed / total_topics) * 100) if total_topics > 0 else 0
        }
        
    return render_template('progress.html', students=students, trainings=trainings, summary=summary)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
