from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Training, Topic, Student, Attendance, Progress, KnowledgeAssessment, KnowledgeSkill, Instructor, Certificate, training_instructors
import uuid
import os
import re
from datetime import datetime

app = Flask(__name__, static_folder='statics', static_url_path='/statics')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'trainings.db')
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
    instructors = Instructor.query.filter_by(is_active=True).limit(3).all()
    return render_template('index.html', trainings=trainings, instructors=instructors)

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
    
    # Get skills from database as a flat list
    skills = KnowledgeSkill.query.filter_by(is_active=True).order_by(KnowledgeSkill.order).all()
    
    proficiency_levels = ['Beginner', 'Intermediate', 'Advance', 'Expert']
    
    # Get all assessments and organize by student + topic
    assessments = KnowledgeAssessment.query.all()
    assessment_map = {}
    for assessment in assessments:
        key = f"{assessment.student_id}_{assessment.topic}"
        assessment_map[key] = assessment
    
    return render_template('knowledge_assessment.html',
                         students=students,
                         skills=skills,
                         proficiency_levels=proficiency_levels,
                         assessment_map=assessment_map)

# API endpoint to get assessments for a student
@app.route('/api/knowledge-assessment/student/<int:student_id>')
def get_student_assessments(student_id):
    assessments = KnowledgeAssessment.query.filter_by(student_id=student_id).all()
    return jsonify([{
        'id': a.id,
        'topic': a.topic,
        'proficiency_level': a.proficiency_level,
        'last_updated': a.last_updated.isoformat() if a.last_updated else None
    } for a in assessments])

# API endpoint to update/create assessment
@app.route('/api/knowledge-assessment', methods=['POST'])
def update_assessment():
    data = request.json
    student_id = data.get('student_id')
    topic = data.get('topic')
    proficiency_level = data.get('proficiency_level')
    
    # Check if assessment exists
    assessment = KnowledgeAssessment.query.filter_by(
        student_id=student_id,
        topic=topic
    ).first()
    
    if assessment:
        assessment.proficiency_level = proficiency_level
    else:
        assessment = KnowledgeAssessment(
            student_id=student_id,
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
    skills = KnowledgeSkill.query.order_by(KnowledgeSkill.order).all()
    return jsonify([{
        'id': s.id,
        'topic': s.topic,
        'order': s.order,
        'is_active': s.is_active
    } for s in skills])

# Add new skill
@app.route('/api/skills', methods=['POST'])
def add_skill():
    data = request.json
    topic = data.get('topic')
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400
    
    # Check if skill already exists
    existing = KnowledgeSkill.query.filter_by(topic=topic).first()
    if existing:
        if not existing.is_active:
            # Reactivate if it was deactivated
            existing.is_active = True
            db.session.commit()
            return jsonify({'success': True, 'id': existing.id, 'reactivated': True})
        return jsonify({'success': False, 'error': 'Skill already exists'}), 400
    
    # Get max order
    max_order = db.session.query(db.func.max(KnowledgeSkill.order)).scalar() or 0
    
    skill = KnowledgeSkill(
        topic=topic,
        order=max_order + 1
    )
    db.session.add(skill)
    db.session.commit()
    
    return jsonify({'success': True, 'id': skill.id})

# Update skill
@app.route('/api/skills/<int:skill_id>', methods=['PUT'])
def update_skill(skill_id):
    try:
        skill = KnowledgeSkill.query.get_or_404(skill_id)
        data = request.json
        
        old_topic = skill.topic
        new_topic = data.get('topic', skill.topic)
        
        # Validate input
        if not new_topic:
            return jsonify({'success': False, 'error': 'Topic is required'}), 400
        
        # Check if another skill with the new topic already exists
        if old_topic != new_topic:
            existing = KnowledgeSkill.query.filter_by(
                topic=new_topic
            ).filter(KnowledgeSkill.id != skill_id).first()
            
            if existing:
                return jsonify({'success': False, 'error': 'A skill with this topic already exists'}), 400
        
        # Update skill
        skill.topic = new_topic
        
        # Update all related assessments using bulk update
        updated_count = 0
        if old_topic != new_topic:
            # Use synchronize_session=False and expire_all to ensure fresh data
            updated_count = KnowledgeAssessment.query.filter_by(
                topic=old_topic
            ).update({
                'topic': new_topic
            }, synchronize_session=False)
        
        # Commit all changes
        db.session.commit()
        
        # Expire all cached objects to ensure fresh reads
        db.session.expire_all()
        
        # Verify the update was successful
        final_count = KnowledgeAssessment.query.filter_by(
            topic=new_topic
        ).count()
        
        return jsonify({
            'success': True, 
            'updated_assessments': updated_count,
            'total_assessments': final_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating skill: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to update skill: {str(e)}'}), 500

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
    
    # Get assessments as a simple list (no category grouping)
    assessments_list = knowledge_assessments
    
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
                         assessments_list=assessments_list)

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
    instructors_count = Instructor.query.filter_by(is_active=True).count()
    return render_template('admin_dashboard.html', 
                         trainings=trainings, 
                         topics=topics, 
                         students=students,
                         instructors_count=instructors_count)

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
    
    # Delete related records to avoid foreign key constraint errors
    Attendance.query.filter_by(topic_id=topic_id).delete()
    Progress.query.filter_by(topic_id=topic_id).delete()
    
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
    
    # Delete related records to avoid foreign key constraint errors
    KnowledgeAssessment.query.filter_by(student_id=student_id).delete()
    Attendance.query.filter_by(student_id=student_id).delete()
    Progress.query.filter_by(student_id=student_id).delete()
    Certificate.query.filter_by(student_id=student_id).delete()
    
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ============================================
# INSTRUCTOR ROUTES
# ============================================

# Public Routes
@app.route('/instructors')
def instructors_list():
    instructors = Instructor.query.filter_by(is_active=True).order_by(Instructor.name).all()
    return render_template('instructors.html', instructors=instructors)

@app.route('/instructor/<int:instructor_id>')
def instructor_profile(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    # Get trainings for this instructor
    trainings = instructor.trainings.all()
    return render_template('instructor_profile.html', instructor=instructor, trainings=trainings)

# Admin Routes
@app.route('/admin/instructors')
def admin_instructors():
    instructors = Instructor.query.order_by(Instructor.is_active.desc(), Instructor.name).all()
    return render_template('admin_instructors.html', instructors=instructors)

@app.route('/admin/instructors/add', methods=['GET', 'POST'])
def admin_add_instructor():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        bio = request.form.get('bio')
        expertise = request.form.get('expertise')
        email = request.form.get('email')
        photo_url = request.form.get('photo_url')
        
        instructor = Instructor(
            name=name,
            role=role,
            bio=bio,
            expertise=expertise,
            email=email,
            photo_url=photo_url
        )
        db.session.add(instructor)
        db.session.commit()
        
        # Handle training linkages
        training_ids = request.form.getlist('training_ids')
        primary_training_id = request.form.get('primary_training_id')
        
        for training_id in training_ids:
            training = Training.query.get(int(training_id))
            if training:
                instructor.trainings.append(training)
                
                # Set primary flag if this is the primary training
                if primary_training_id and int(training_id) == int(primary_training_id):
                    # Update the association table to set is_primary
                    db.session.execute(
                        training_instructors.update().where(
                            (training_instructors.c.training_id == int(training_id)) &
                            (training_instructors.c.instructor_id == instructor.id)
                        ).values(is_primary=True)
                    )
        
        db.session.commit()
        
        return redirect(url_for('admin_instructors'))
    
    trainings = Training.query.all()
    return render_template('admin_instructor_form.html', instructor=None, trainings=trainings)

@app.route('/admin/instructors/<int:instructor_id>/edit', methods=['GET', 'POST'])
def admin_edit_instructor(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    
    if request.method == 'POST':
        instructor.name = request.form.get('name')
        instructor.role = request.form.get('role')
        instructor.bio = request.form.get('bio')
        instructor.expertise = request.form.get('expertise')
        instructor.email = request.form.get('email')
        instructor.photo_url = request.form.get('photo_url')
        
        # Clear existing training linkages
        instructor.trainings = []
        db.session.commit()
        
        # Handle training linkages
        training_ids = request.form.getlist('training_ids')
        primary_training_id = request.form.get('primary_training_id')
        
        for training_id in training_ids:
            training = Training.query.get(int(training_id))
            if training:
                instructor.trainings.append(training)
        
        db.session.commit()
        
        # Update primary flags
        if primary_training_id:
            # First, clear all primary flags for this instructor
            db.session.execute(
                training_instructors.update().where(
                    training_instructors.c.instructor_id == instructor.id
                ).values(is_primary=False)
            )
            
            # Then set the primary flag for the selected training
            db.session.execute(
                training_instructors.update().where(
                    (training_instructors.c.training_id == int(primary_training_id)) &
                    (training_instructors.c.instructor_id == instructor.id)
                ).values(is_primary=True)
            )
            
            db.session.commit()
        
        return redirect(url_for('admin_instructors'))
    
    trainings = Training.query.all()
    # Get current training IDs for this instructor
    current_training_ids = [t.id for t in instructor.trainings.all()]
    
    # Get primary training ID
    primary_training_id = None
    result = db.session.execute(
        db.select(training_instructors.c.training_id).where(
            (training_instructors.c.instructor_id == instructor.id) &
            (training_instructors.c.is_primary == True)
        )
    ).first()
    if result:
        primary_training_id = result[0]
    
    return render_template('admin_instructor_form.html', 
                         instructor=instructor, 
                         trainings=trainings,
                         current_training_ids=current_training_ids,
                         primary_training_id=primary_training_id)

@app.route('/admin/instructors/<int:instructor_id>/delete', methods=['POST'])
def admin_delete_instructor(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    # Soft delete
    instructor.is_active = False
    db.session.commit()
    return redirect(url_for('admin_instructors'))

@app.route('/admin/instructors/<int:instructor_id>/activate', methods=['POST'])
def admin_activate_instructor(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    instructor.is_active = True
    db.session.commit()
    return redirect(url_for('admin_instructors'))

# API Routes for Training Linkage
@app.route('/api/instructors/<int:instructor_id>/link-training', methods=['POST'])
def api_link_instructor_training(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    data = request.json
    training_id = data.get('training_id')
    is_primary = data.get('is_primary', False)
    
    training = Training.query.get_or_404(training_id)
    
    # Check if already linked
    if training not in instructor.trainings.all():
        instructor.trainings.append(training)
        db.session.commit()
    
    # Update primary flag if needed
    if is_primary:
        db.session.execute(
            training_instructors.update().where(
                (training_instructors.c.training_id == training_id) &
                (training_instructors.c.instructor_id == instructor_id)
            ).values(is_primary=True)
        )
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/instructors/<int:instructor_id>/unlink-training', methods=['POST'])
def api_unlink_instructor_training(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    data = request.json
    training_id = data.get('training_id')
    
    training = Training.query.get_or_404(training_id)
    
    if training in instructor.trainings.all():
        instructor.trainings.remove(training)
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/instructors/<int:instructor_id>/trainings')
def api_get_instructor_trainings(instructor_id):
    instructor = Instructor.query.get_or_404(instructor_id)
    trainings = instructor.trainings.all()
    
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'description': t.description
    } for t in trainings])

# Certificate Management
@app.route('/admin/certificates')
def admin_certificates():
    certificates = Certificate.query.order_by(Certificate.issue_date.desc()).all()
    return render_template('admin_certificates.html', certificates=certificates)

@app.route('/admin/certificates/add', methods=['GET', 'POST'])
def admin_add_certificate():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        training_id = request.form.get('training_id')
        
        # Get student and training details for defaults if not provided
        student = Student.query.get(student_id)
        training = Training.query.get(training_id) if training_id else None
        
        certificate = Certificate(
            student_id=student_id,
            training_id=training_id if training_id else None,
            certificate_title=request.form.get('certificate_title', "CERTIFICATE OF COMPLETION"),
            student_name=request.form.get('student_name') or student.name,
            course_name=request.form.get('course_name') or (training.name if training else "QA Training"),
            certificate_text=request.form.get('certificate_text', "has successfully completed the comprehensive training program in"),
            completion_date=datetime.strptime(request.form.get('completion_date'), '%Y-%m-%d').date(),
            signature_1_name=request.form.get('signature_1_name'),
            signature_1_title=request.form.get('signature_1_title'),
            signature_2_name=request.form.get('signature_2_name'),
            signature_2_title=request.form.get('signature_2_title'),
            signature_3_name=request.form.get('signature_3_name'),
            signature_3_title=request.form.get('signature_3_title'),
            seal_text=request.form.get('seal_text', "OFFICIAL\nSEAL"),
            unique_code=str(uuid.uuid4())[:8].upper(),
            is_issued=True
        )
        
        db.session.add(certificate)
        db.session.commit()
        return redirect(url_for('admin_certificates'))
        
    students = Student.query.all()
    trainings = Training.query.all()
    return render_template('admin_certificate_form.html', students=students, trainings=trainings, today=datetime.now().date())

@app.route('/admin/certificates/<int:id>/edit', methods=['GET', 'POST'])
def admin_edit_certificate(id):
    certificate = Certificate.query.get_or_404(id)
    
    if request.method == 'POST':
        certificate.student_id = request.form.get('student_id')
        certificate.training_id = request.form.get('training_id') if request.form.get('training_id') else None
        certificate.certificate_title = request.form.get('certificate_title')
        certificate.student_name = request.form.get('student_name')
        certificate.course_name = request.form.get('course_name')
        certificate.certificate_text = request.form.get('certificate_text')
        certificate.completion_date = datetime.strptime(request.form.get('completion_date'), '%Y-%m-%d').date()
        certificate.signature_1_name = request.form.get('signature_1_name')
        certificate.signature_1_title = request.form.get('signature_1_title')
        certificate.signature_2_name = request.form.get('signature_2_name')
        certificate.signature_2_title = request.form.get('signature_2_title')
        certificate.signature_3_name = request.form.get('signature_3_name')
        certificate.signature_3_title = request.form.get('signature_3_title')
        certificate.seal_text = request.form.get('seal_text')
        
        db.session.commit()
        return redirect(url_for('admin_certificates'))
        
    students = Student.query.all()
    trainings = Training.query.all()
    return render_template('admin_certificate_form.html', certificate=certificate, students=students, trainings=trainings)

@app.route('/admin/certificates/<int:id>/delete', methods=['POST'])
def admin_delete_certificate(id):
    certificate = Certificate.query.get_or_404(id)
    db.session.delete(certificate)
    db.session.commit()
    return redirect(url_for('admin_certificates'))

@app.route('/admin/certificates/<int:id>/preview')
def admin_preview_certificate(id):
    certificate = Certificate.query.get_or_404(id)
    return render_template('certificate_view.html', certificate=certificate, preview=True)

@app.route('/certificate/<unique_code>')
def view_certificate(unique_code):
    certificate = Certificate.query.filter_by(unique_code=unique_code).first_or_404()
    return render_template('certificate_view.html', certificate=certificate)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=6501,debug=True)
