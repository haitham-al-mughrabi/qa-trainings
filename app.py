from flask import Flask, render_template, request, redirect, url_for
from models import db, Training, Topic, Student, Attendance, Progress
import os
import re
from datetime import datetime

app = Flask(__name__, static_folder='statics', static_url_path='/statics')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trainings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Add custom Jinja2 filter for regex replacement
@app.template_filter('regex_replace')
def regex_replace(s, pattern, replacement):
    return re.sub(pattern, replacement, s)

# Add context processor for current datetime
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

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

# ============================================
# ADMIN ROUTES
# ============================================

@app.route('/admin')
def admin_dashboard():
    trainings = Training.query.all()
    topics = Topic.query.all()
    students = Student.query.all()
    return render_template('admin_dashboard.html', 
                         trainings=trainings, 
                         topics=topics, 
                         students=students)

# Training Management
@app.route('/admin/trainings/add', methods=['GET', 'POST'])
def admin_add_training():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        training = Training(name=name, description=description)
        db.session.add(training)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_training_form.html', training=None)

@app.route('/admin/trainings/<int:training_id>/edit', methods=['GET', 'POST'])
def admin_edit_training(training_id):
    training = Training.query.get_or_404(training_id)
    
    if request.method == 'POST':
        training.name = request.form.get('name')
        training.description = request.form.get('description')
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_training_form.html', training=training)

@app.route('/admin/trainings/<int:training_id>/delete', methods=['POST'])
def admin_delete_training(training_id):
    training = Training.query.get_or_404(training_id)
    db.session.delete(training)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Topic Management
@app.route('/admin/topics/add', methods=['GET', 'POST'])
def admin_add_topic():
    if request.method == 'POST':
        training_id = request.form.get('training_id')
        name = request.form.get('name')
        phase = request.form.get('phase')
        instructor = request.form.get('instructor')
        video_url = request.form.get('video_url')
        description = request.form.get('description')
        order = request.form.get('order', 0)
        
        topic = Topic(
            training_id=training_id,
            name=name,
            phase=phase,
            instructor=instructor,
            video_url=video_url,
            description=description,
            order=order
        )
        db.session.add(topic)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    trainings = Training.query.all()
    return render_template('admin_topic_form.html', topic=None, trainings=trainings)

@app.route('/admin/topics/<int:topic_id>/edit', methods=['GET', 'POST'])
def admin_edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    if request.method == 'POST':
        topic.training_id = request.form.get('training_id')
        topic.name = request.form.get('name')
        topic.phase = request.form.get('phase')
        topic.instructor = request.form.get('instructor')
        topic.video_url = request.form.get('video_url')
        topic.description = request.form.get('description')
        topic.order = request.form.get('order', 0)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    trainings = Training.query.all()
    return render_template('admin_topic_form.html', topic=topic, trainings=trainings)

@app.route('/admin/topics/<int:topic_id>/delete', methods=['POST'])
def admin_delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    db.session.delete(topic)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Student Management
@app.route('/admin/students/add', methods=['GET', 'POST'])
def admin_add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        
        student = Student(name=name)
        db.session.add(student)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_student_form.html', student=None)

@app.route('/admin/students/<int:student_id>/edit', methods=['GET', 'POST'])
def admin_edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    if request.method == 'POST':
        student.name = request.form.get('name')
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_student_form.html', student=student)

@app.route('/admin/students/<int:student_id>/delete', methods=['POST'])
def admin_delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
