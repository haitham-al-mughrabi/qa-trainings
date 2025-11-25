from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Training, Topic, Student, Attendance, Progress, KnowledgeAssessment, KnowledgeSkill
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
    
    # Calculate basic attendance summary for the form
    summary = {}
    for student in students:
        total = Attendance.query.filter_by(student_id=student.id).count()
        present = Attendance.query.filter_by(student_id=student.id, status='Present').count()
        summary[student.id] = {
            'total': total,
            'present': present,
            'percentage': int((present / total) * 100) if total > 0 else 0
        }
    
    # Build hierarchical attendance data structure for analytics
    attendance_data = {}
    
    for training in trainings:
        training_stats = {
            'name': training.name,
            'id': training.id,
            'phases': {},
            'total_topics': len(training.topics),
            'students': {}
        }
        
        # Group topics by phase
        for topic in training.topics:
            phase_key = topic.phase or 'No Phase'
            if phase_key not in training_stats['phases']:
                training_stats['phases'][phase_key] = {
                    'topics': [],
                    'students': {}
                }
            
            # Get attendance for this topic (most recent record per student)
            topic_attendance = {}
            for student in students:
                # Get the most recent attendance record for this student and topic
                attendance_record = Attendance.query.filter_by(
                    student_id=student.id, 
                    topic_id=topic.id
                ).order_by(Attendance.date.desc()).first()
                
                status = attendance_record.status if attendance_record else None
                topic_attendance[student.id] = status
                
                # Aggregate to phase level
                if student.id not in training_stats['phases'][phase_key]['students']:
                    training_stats['phases'][phase_key]['students'][student.id] = {
                        'present': 0, 'absent': 0, 'excused': 0, 'total': 0, 'percentage': 0
                    }
                
                training_stats['phases'][phase_key]['students'][student.id]['total'] += 1
                if status == 'Present':
                    training_stats['phases'][phase_key]['students'][student.id]['present'] += 1
                elif status == 'Absent':
                    training_stats['phases'][phase_key]['students'][student.id]['absent'] += 1
                elif status == 'Excused':
                    training_stats['phases'][phase_key]['students'][student.id]['excused'] += 1
                
                # Calculate percentage for phase
                phase_stats = training_stats['phases'][phase_key]['students'][student.id]
                if phase_stats['total'] > 0:
                    phase_stats['percentage'] = int((phase_stats['present'] / phase_stats['total']) * 100)
                
                # Aggregate to training level
                if student.id not in training_stats['students']:
                    training_stats['students'][student.id] = {
                        'present': 0, 'absent': 0, 'excused': 0, 'total': 0, 'percentage': 0
                    }
                
                training_stats['students'][student.id]['total'] += 1
                if status == 'Present':
                    training_stats['students'][student.id]['present'] += 1
                elif status == 'Absent':
                    training_stats['students'][student.id]['absent'] += 1
                elif status == 'Excused':
                    training_stats['students'][student.id]['excused'] += 1
                
                # Calculate percentage for training
                training_student_stats = training_stats['students'][student.id]
                if training_student_stats['total'] > 0:
                    training_student_stats['percentage'] = int((training_student_stats['present'] / training_student_stats['total']) * 100)
            
            training_stats['phases'][phase_key]['topics'].append({
                'id': topic.id,
                'name': topic.name,
                'attendance': topic_attendance
            })
        
        attendance_data[training.id] = training_stats
    
    return render_template('attendance.html', 
                         students=students, 
                         trainings=trainings, 
                         summary=summary,
                         attendance_data=attendance_data,
                         students_json=[{'id': s.id, 'name': s.name} for s in students])

@app.route('/progress')
def progress():
    trainings = Training.query.all()
    students = Student.query.all()
    
    # Build hierarchical data structure
    progress_data = {}
    
    for training in trainings:
        training_stats = {
            'name': training.name,
            'id': training.id,
            'phases': {},
            'total_topics': len(training.topics),
            'students': {}
        }
        
        # Group topics by phase
        for topic in training.topics:
            phase_key = topic.phase or 'No Phase'
            if phase_key not in training_stats['phases']:
                training_stats['phases'][phase_key] = {
                    'topics': [],
                    'students': {}
                }
            
            # Get progress for this topic
            topic_progress = {}
            for student in students:
                prog = Progress.query.filter_by(student_id=student.id, topic_id=topic.id).first()
                status = prog.status if prog else 'Not Started'
                topic_progress[student.id] = status
                
                # Aggregate to phase level
                if student.id not in training_stats['phases'][phase_key]['students']:
                    training_stats['phases'][phase_key]['students'][student.id] = {
                        'completed': 0, 'in_progress': 0, 'not_started': 0, 'total': 0
                    }
                
                training_stats['phases'][phase_key]['students'][student.id]['total'] += 1
                if status == 'Completed':
                    training_stats['phases'][phase_key]['students'][student.id]['completed'] += 1
                elif status == 'In Progress':
                    training_stats['phases'][phase_key]['students'][student.id]['in_progress'] += 1
                else:
                    training_stats['phases'][phase_key]['students'][student.id]['not_started'] += 1
                
                # Aggregate to training level
                if student.id not in training_stats['students']:
                    training_stats['students'][student.id] = {
                        'completed': 0, 'in_progress': 0, 'not_started': 0, 'total': 0
                    }
                
                training_stats['students'][student.id]['total'] += 1
                if status == 'Completed':
                    training_stats['students'][student.id]['completed'] += 1
                elif status == 'In Progress':
                    training_stats['students'][student.id]['in_progress'] += 1
                else:
                    training_stats['students'][student.id]['not_started'] += 1
            
            training_stats['phases'][phase_key]['topics'].append({
                'id': topic.id,
                'name': topic.name,
                'progress': topic_progress
            })
        
        progress_data[training.id] = training_stats
    
    return render_template('progress.html', 
                         trainings=trainings,
                         students=[{'id': s.id, 'name': s.name} for s in students],
                         progress_data=progress_data)

# ============================================
# KNOWLEDGE ASSESSMENT ROUTES
# ============================================


@app.route('/knowledge-assessment')
def knowledge_assessment():
    students = Student.query.all()
    
    # Get skills from database, grouped by category
    skills = KnowledgeSkill.query.filter_by(is_active=True).order_by(KnowledgeSkill.category, KnowledgeSkill.order).all()
    
    # Build knowledge structure from database
    knowledge_structure = {}
    for skill in skills:
        if skill.category not in knowledge_structure:
            knowledge_structure[skill.category] = []
        knowledge_structure[skill.category].append(skill.topic)
    
    # If no skills exist, initialize with default structure
    if not knowledge_structure:
        knowledge_structure = {
            'Automation': ['Python - Testing level', 'Robot Framework'],
            'Performance': ['Javascript - Testing level', 'K6'],
            'API': ['Postman', 'Mocking'],
            'Database': ['SQL']
        }
        # Save default skills to database
        order = 0
        for category, topics in knowledge_structure.items():
            for topic in topics:
                skill = KnowledgeSkill(category=category, topic=topic, order=order)
                db.session.add(skill)
                order += 1
        db.session.commit()
    
    proficiency_levels = ['Beginner', 'Intermediate', 'Advance', 'Expert']
    
    # Get all assessments and organize by student
    assessments = KnowledgeAssessment.query.all()
    assessment_map = {}
    for assessment in assessments:
        key = f"{assessment.student_id}_{assessment.category}_{assessment.topic}"
        assessment_map[key] = assessment
    
    # Get all categories for management
    all_skills = KnowledgeSkill.query.order_by(KnowledgeSkill.category, KnowledgeSkill.order).all()
    
    return render_template('knowledge_assessment.html',
                         students=students,
                         knowledge_structure=knowledge_structure,
                         proficiency_levels=proficiency_levels,
                         assessment_map=assessment_map,
                         all_skills=all_skills)

# API endpoint to get assessments for a student
@app.route('/api/knowledge-assessment/student/<int:student_id>')
def get_student_assessments(student_id):
    assessments = KnowledgeAssessment.query.filter_by(student_id=student_id).all()
    return jsonify([{
        'id': a.id,
        'category': a.category,
        'topic': a.topic,
        'proficiency_level': a.proficiency_level,
        'last_updated': a.last_updated.isoformat() if a.last_updated else None
    } for a in assessments])

# API endpoint to update/create assessment
@app.route('/api/knowledge-assessment', methods=['POST'])
def update_assessment():
    data = request.json
    student_id = data.get('student_id')
    category = data.get('category')
    topic = data.get('topic')
    proficiency_level = data.get('proficiency_level')
    
    # Check if assessment exists
    assessment = KnowledgeAssessment.query.filter_by(
        student_id=student_id,
        category=category,
        topic=topic
    ).first()
    
    if assessment:
        assessment.proficiency_level = proficiency_level
    else:
        assessment = KnowledgeAssessment(
            student_id=student_id,
            category=category,
            topic=topic,
            proficiency_level=proficiency_level
        )
        db.session.add(assessment)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': assessment.id,
        'last_updated': assessment.last_updated.isoformat() if assessment.last_updated else None
    })

# API endpoint to delete assessment
@app.route('/api/knowledge-assessment/<int:assessment_id>', methods=['DELETE'])
def delete_assessment(assessment_id):
    assessment = KnowledgeAssessment.query.get_or_404(assessment_id)
    db.session.delete(assessment)
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================
# SKILL MANAGEMENT API ENDPOINTS
# ============================================

# Get all skills
@app.route('/api/skills')
def get_all_skills():
    skills = KnowledgeSkill.query.order_by(KnowledgeSkill.category, KnowledgeSkill.order).all()
    return jsonify([{
        'id': s.id,
        'category': s.category,
        'topic': s.topic,
        'order': s.order,
        'is_active': s.is_active
    } for s in skills])

# Add new skill
@app.route('/api/skills', methods=['POST'])
def add_skill():
    data = request.json
    category = data.get('category')
    topic = data.get('topic')
    
    if not category or not topic:
        return jsonify({'success': False, 'error': 'Category and topic are required'}), 400
    
    # Check if skill already exists
    existing = KnowledgeSkill.query.filter_by(category=category, topic=topic).first()
    if existing:
        if not existing.is_active:
            # Reactivate if it was deactivated
            existing.is_active = True
            db.session.commit()
            return jsonify({'success': True, 'id': existing.id, 'reactivated': True})
        return jsonify({'success': False, 'error': 'Skill already exists'}), 400
    
    # Get max order for this category
    max_order = db.session.query(db.func.max(KnowledgeSkill.order)).filter_by(category=category).scalar() or 0
    
    skill = KnowledgeSkill(
        category=category,
        topic=topic,
        order=max_order + 1
    )
    db.session.add(skill)
    db.session.commit()
    
    return jsonify({'success': True, 'id': skill.id})

# Update skill
@app.route('/api/skills/<int:skill_id>', methods=['PUT'])
def update_skill(skill_id):
    skill = KnowledgeSkill.query.get_or_404(skill_id)
    data = request.json
    
    old_category = skill.category
    old_topic = skill.topic
    
    new_category = data.get('category', skill.category)
    new_topic = data.get('topic', skill.topic)
    
    # Update skill
    skill.category = new_category
    skill.topic = new_topic
    
    # Update all related assessments
    assessments = KnowledgeAssessment.query.filter_by(
        category=old_category,
        topic=old_topic
    ).all()
    
    for assessment in assessments:
        assessment.category = new_category
        assessment.topic = new_topic
    
    db.session.commit()
    
    return jsonify({'success': True, 'updated_assessments': len(assessments)})

# Delete skill (soft delete)
@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    skill = KnowledgeSkill.query.get_or_404(skill_id)
    
    # Soft delete - just mark as inactive
    skill.is_active = False
    db.session.commit()
    
    # Optionally, also delete related assessments
    # KnowledgeAssessment.query.filter_by(category=skill.category, topic=skill.topic).delete()
    # db.session.commit()
    
    return jsonify({'success': True})




@app.route('/student/<int:student_id>')
def student_profile(student_id):
    student = Student.query.get_or_404(student_id)
    
    # Get all attendance records for this student
    attendance_records = Attendance.query.filter_by(student_id=student_id).all()
    
    # Get all progress records for this student
    progress_records = Progress.query.filter_by(student_id=student_id).all()
    
    # Get knowledge assessments for this student
    knowledge_assessments = KnowledgeAssessment.query.filter_by(student_id=student_id).all()
    
    # Organize assessments by category
    assessments_by_category = {}
    for assessment in knowledge_assessments:
        if assessment.category not in assessments_by_category:
            assessments_by_category[assessment.category] = []
        assessments_by_category[assessment.category].append(assessment)
    
    # Get unique trainings the student is enrolled in (based on attendance or progress)
    attended_topic_ids = set([a.topic_id for a in attendance_records])
    progress_topic_ids = set([p.topic_id for p in progress_records])
    all_topic_ids = attended_topic_ids.union(progress_topic_ids)
    
    topics = Topic.query.filter(Topic.id.in_(all_topic_ids)).all() if all_topic_ids else []
    training_ids = set([t.training_id for t in topics])
    trainings = Training.query.filter(Training.id.in_(training_ids)).all() if training_ids else []
    
    # Calculate statistics
    total_topics = len(topics)
    attended_count = len([a for a in attendance_records if a.status == 'Present'])
    completed_count = len([p for p in progress_records if p.status == 'Completed'])
    
    # Create attendance map
    attendance_map = {a.topic_id: a for a in attendance_records}
    progress_map = {p.topic_id: p for p in progress_records}
    
    stats = {
        'total_trainings': len(trainings),
        'total_topics': total_topics,
        'attendance_rate': int((attended_count / total_topics * 100)) if total_topics > 0 else 0,
        'completion_rate': int((completed_count / total_topics * 100)) if total_topics > 0 else 0,
        'total_skills': len(knowledge_assessments)
    }
    
    return render_template('student_profile.html', 
                         student=student, 
                         trainings=trainings,
                         topics=topics,
                         attendance_map=attendance_map,
                         progress_map=progress_map,
                         stats=stats,
                         assessments_by_category=assessments_by_category)

@app.route('/students')
def students_list():
    students = Student.query.order_by(Student.name).all()
    return render_template('students.html', students=students)

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
        
        # Generate slug from name
        slug = name.lower().replace(' ', '-').replace('&', 'and')
        # Remove special characters
        import string
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        training = Training(name=name, slug=slug, description=description)
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
        
        # Update slug from name
        slug = training.name.lower().replace(' ', '-').replace('&', 'and')
        import string
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        training.slug = slug
        
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
