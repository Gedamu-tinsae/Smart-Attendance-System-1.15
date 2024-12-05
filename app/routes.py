from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, abort, session,Response
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import RegistrationForm, LoginForm, UploadForm,CompleteRegistrationForm
from .models import User, AttendanceRecord, ScheduleEntry, Student, Teacher, Class, AttendanceStatus, FeatureToggle
from . import db
from datetime import datetime
import os
import cv2
import numpy as np
import base64
from werkzeug.utils import secure_filename
from .utils import calculate_attendance_percentage, get_attendance_details, is_within_school
from app.facial_recognition import train_model as train_model_function
from app.facial_recognition import train_model, get_model_directory, recognize_face
import io
from PIL import Image
import logging
from sqlalchemy import and_
from sqlalchemy.orm import aliased
from app import oauth  # Import the initialized oauth object
import secrets
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')  # Use a non-interactive backend
from .utils2 import get_attendance_by_course, get_attendance_by_department, get_low_attendance_students,get_attendance_and_students,aggregate_course_attendance,calculate_course_attendance_percentage,aggregate_department_attendance,calculate_department_attendance_percentage,feature_usage_analysis,analyze_attendance_by_distance,get_courses_by_attendance,get_attendance_trend,flag_low_attendance_students,project_attendance,flag_low_attendance_courses,    compare_class_attendance,teacher_attendance_analysis,peak_attendance_times,department_wise_attendance,get_late_comers,  get_department_attendance,get_batch_attendance,get_student_attendance,get_class_attendance,get_teacher_classes_attendance,get_attendance_by_location,is_attendance_allowed,get_teacher_attendance_summary,get_frequent_absentees,correlate_attendance_with_performance,get_students_by_course_attendance



# Define the main blueprint
main = Blueprint('main', __name__)


@main.route('/toggle_manual_attendance_all', methods=['POST'])
@login_required
def toggle_manual_attendance_for_all():
    is_enabled = request.form.get('is_enabled') == 'on'  # Check if the checkbox is checked

    # Log the current state of the feature
    current_app.logger.debug(f"Global Manual Attendance Enabled: {is_enabled}")

    # Enable or disable manual attendance based on the checkbox state
    if is_enabled:
        Student.query.update({Student.manual_attendance_enabled: True})
        current_app.logger.debug("Enabled manual attendance for all students globally.")
    else:
        Student.query.update({Student.manual_attendance_enabled: False})
        current_app.logger.debug("Disabled manual attendance for all students globally.")

    # Commit the changes
    db.session.commit()
    flash('Manual attendance settings updated for all students!', 'success')

    return redirect(url_for('main.teacher_options'))


@main.route('/toggle_manual_attendance_selected', methods=['POST'])
@login_required
def toggle_manual_attendance_for_selected():
    student_ids = request.form.getlist('student_ids')  # Get selected student IDs
    current_app.logger.debug(f"Raw Selected Student IDs from form: {student_ids}")

    # Convert student_ids to integers if needed
    try:
        student_ids = [int(student_id) for student_id in student_ids]
        current_app.logger.debug(f"Converted Student IDs: {student_ids}")
    except ValueError as e:
        current_app.logger.error(f"Error converting student IDs: {e}")
        flash('Error processing selected student IDs!', 'danger')
        return redirect(url_for('main.teacher_options'))

    # Log the current state of students in the database
    all_students = Student.query.all()
    all_student_ids = [student.id for student in all_students]
    current_app.logger.debug(f"All Student IDs in the database: {all_student_ids}")

    if student_ids:
        # Enable manual attendance for the selected students
        Student.query.filter(Student.id.in_(student_ids)).update(
            {Student.manual_attendance_enabled: True}, synchronize_session=False
        )
        current_app.logger.debug(f"Enabled manual attendance for selected students: {student_ids}")

        # Disable manual attendance for students not in the selected list
        Student.query.filter(~Student.id.in_(student_ids)).update(
            {Student.manual_attendance_enabled: False}, synchronize_session=False
        )
        current_app.logger.debug("Disabled manual attendance for students not selected.")
    else:
        # If no students are selected, disable manual attendance for all students
        Student.query.update({Student.manual_attendance_enabled: False}, synchronize_session=False)
        current_app.logger.debug("No students selected, disabled manual attendance for all students.")

    # Commit the changes
    db.session.commit()
    flash('Manual attendance settings updated for selected students!', 'success')

    return redirect(url_for('main.teacher_options'))


@main.route('/')
def index():
    if current_user.is_authenticated:
        # If the user is authenticated, they can view the homepage
        return render_template('index.html')  # This renders your main homepage

    # If the user is not logged in, they still see the homepage but can navigate to the login page
    return render_template('index.html')  # Load the homepage even for unauthenticated users


@main.route('/student_options')
@login_required
def student_options():
    # Check if the user is a student and has completed registration
    student = Student.query.filter_by(user_id=current_user.id).first()

    if not student:
        flash('Please complete your registration first!', 'warning')
        return redirect(url_for('main.complete_registration'))

    # Proceed with fetching data for registered students
    try:
        train_model_toggle = FeatureToggle.query.filter_by(feature_name='train_model').first()
        train_model_enabled = train_model_toggle.is_enabled if train_model_toggle else False

        attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).all()
        schedule_entries = ScheduleEntry.query.filter_by(student_id=student.id).all()

        # Fetch all AttendanceStatus records for the days and periods of the student's schedule
        attendance_statuses = AttendanceStatus.query.filter(
            AttendanceStatus.day.in_([entry.day_of_week for entry in schedule_entries]),
            AttendanceStatus.period.in_([f"{entry.time_start}-{entry.time_end}" for entry in schedule_entries])
        ).all()

        # Check if any attendance status indicates the student can take attendance
        can_take_attendance = any(status.status for status in attendance_statuses)

    except Exception as e:
        flash('An error occurred while fetching your options. Please try again later.', 'danger')
        return redirect(url_for('main.index'))  # Redirect to a safe page

    return render_template(
        'student_options.html',
        student=student,
        attendance_records=attendance_records,
        can_take_attendance=can_take_attendance,
        train_model_enabled=train_model_enabled
    )


@main.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('main.login'))

    train_model_toggle = FeatureToggle.query.filter_by(feature_name='train_model').first()

    if request.method == 'POST':
        if train_model_toggle:
            train_model_toggle.is_enabled = not train_model_toggle.is_enabled
        else:
            train_model_toggle = FeatureToggle(feature_name='train_model', is_enabled=True)
            db.session.add(train_model_toggle)
        
        db.session.commit()
        flash('Train Model feature toggle updated!', 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin_dashboard.html', train_model_toggle=train_model_toggle)


@main.route('/teacher-options', methods=['GET', 'POST'])
@login_required
def teacher_options():
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['08:00-09:00', '09:00-10:00', '10:00-11:00', '12:00-01:00']

    # Prepare a schedule dictionary
    schedule = {day: {period: None for period in periods} for day in days}

    if current_user.is_teacher:
        # Fetch the teacher's profile
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        if not teacher:
            flash('Teacher profile not found.', 'danger')
            return redirect(url_for('main.index'))

        # Fetch all schedule entries for the teacher
        schedule_entries = ScheduleEntry.query.filter_by(teacher_id=teacher.id).all()

        for entry in schedule_entries:
            period_key = f"{entry.time_start}-{entry.time_end}"
            schedule[entry.day_of_week][period_key] = entry.classroom

        # Fetch all students related to the teacher's department
        related_students = Student.query.filter_by(department=teacher.department).all()

        # Check if any student has manual attendance enabled
        any_student_enabled = any(student.manual_attendance_enabled for student in related_students)

        # Log the related students for debugging
        current_app.logger.info("Related Students: %s", [student.name for student in related_students])

        # Fetch the manual attendance feature toggle status
        manual_attendance_feature = FeatureToggle.query.filter_by(feature_name='manual_attendance').first()
    else:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    return render_template('teacher_options.html',
                           days=days,
                           periods=periods,
                           schedule=schedule,
                           manual_attendance_feature=manual_attendance_feature,
                           students=related_students,
                           any_student_enabled=any_student_enabled)


@main.route('/toggle_attendance', methods=['POST'])
@login_required
def toggle_attendance():
    day = request.form['day']
    period = request.form['period']
    status = request.form['status']

    # Logic to toggle attendance status
    attendance = AttendanceStatus.query.filter_by(day=day, period=period).first()
    if not attendance:
        attendance = AttendanceStatus(day=day, period=period, status=(status == 'ON'))
        db.session.add(attendance)
    else:
        attendance.status = (status == 'ON')

    db.session.commit()

    flash('Attendance status updated successfully!', 'success')
    return redirect(url_for('main.view_schedule_teacher'))


@main.route('/attendance_control', methods=['GET', 'POST'])
@login_required
def attendance_control():
    if not current_user.is_teacher:
        abort(403)  # Forbidden if the user is not a teacher

    if request.method == 'POST':
        # Extract form data
        day = request.form.get('day')
        period = request.form.get('period')
        status = request.form.get('status') == 'ON'

        # Update or create attendance status
        attendance_status = AttendanceStatus.query.filter_by(day=day, period=period).first()
        if not attendance_status:
            attendance_status = AttendanceStatus(day=day, period=period, status=status)
            db.session.add(attendance_status)
        else:
            attendance_status.status = status
        db.session.commit()

        flash('Attendance control updated!', 'success')
        return redirect(url_for('main.attendance_control'))

    # Default state or fetch state from database
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    attendance = {day: {period: False for period in periods} for day in days}

    # Fetch current attendance status from the database
    for day in days:
        for period in periods:
            status = AttendanceStatus.query.filter_by(day=day, period=period).first()
            if status:
                attendance[day][period] = status.status

    return render_template('attendance_control.html', days=days, periods=periods, attendance=attendance)


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    # Handle Google login (redirect to Google OAuth login page)
    if request.form.get('register_type') == 'google':
        print("register_type is ", request.form.get('register_type'))
        return redirect(url_for('main.google_login'))

    # Handle email registration
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            email=form.email.data,
            password=hashed_password,
            is_teacher=form.user_type.data == 'teacher',
            is_admin=form.user_type.data == 'admin',
            is_registered=True  # Mark as registered upon successful registration
        )
        db.session.add(user)
        db.session.commit()

        # Create student or teacher entries based on user type
        if form.user_type.data == 'student':
            student = Student(
                user_id=user.id,
                student_id=form.student_id.data,
                name=form.student_name.data,
                department=form.student_department.data,
                semester=form.student_semester.data,
                batch=form.student_batch.data
            )
            db.session.add(student)

        elif form.user_type.data == 'teacher':
            teacher = Teacher(
                user_id=user.id,
                teacher_id=form.teacher_id.data,
                name=form.teacher_name.data,
                department=form.teacher_department.data
            )
            db.session.add(teacher)

        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    # Clear session to remove any old messages (like 'You have been logged out')
    # Clear session only if it's a GET request (initial page load)
    if request.method == 'GET':
        session.clear()
    # If the user is already authenticated, redirect based on their user type
    if current_user.is_authenticated:
        current_app.logger.debug(f"Already authenticated: User ID = {current_user.id}, Is Teacher = {current_user.is_teacher}, Is Admin = {current_user.is_admin}")
        
        if current_user.is_teacher:
            return redirect(url_for('main.teacher_options'))
        elif current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.student_options'))

    form = LoginForm()

    # Handle email/password login
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            current_app.logger.info(f"User {user.email} logged in successfully.")

            # Redirect based on user type
            if user.is_teacher:
                return redirect(url_for('main.teacher_options'))
            elif user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.student_options'))
        else:
            #session.clear()  # Clears all session data, including flashed messages
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', form=form)


@main.route('/google_login')
def google_login():
    session['nonce'] = secrets.token_urlsafe(16)
    redirect_uri = url_for('main.google_callback', _external=True)
    current_app.logger.debug(f'Redirecting to Google with redirect_uri: {redirect_uri}')
    return oauth.google.authorize_redirect(redirect_uri, nonce=session['nonce'], prompt='select_account')

@main.route('/google_callback')
def google_callback():
    try:
        # Get the token and parse user information
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token, nonce=session.get('nonce'))
        current_app.logger.debug(f'Token: {token}')

        # Verify nonce
        if user_info['nonce'] != session.get('nonce'):
            raise ValueError('Invalid nonce')

        current_app.logger.debug(f'User info: {user_info}')  # Log user info for debugging

    except Exception as e:
        current_app.logger.error(f'Google login failed: {e}')  # Log the error
        flash("Google login failed. Please try again.", 'danger')
        return redirect(url_for('main.login'))

    # Check if the user already exists
    user = User.query.filter_by(email=user_info['email']).first()

    if user:
        # Log in existing user
        login_user(user)
        current_app.logger.info(f'User {user.email} logged in successfully.')

        # Redirect based on user type and registration status
        if user.is_teacher:
            if not user.is_registered:  # Check if the teacher has completed registration
                return redirect(url_for('main.complete_registration'))
            return redirect(url_for('main.teacher_options'))
        
        elif user.is_admin:
            if not user.is_registered:  # Check if the admin has completed registration
                return redirect(url_for('main.complete_registration'))
            return redirect(url_for('main.admin_dashboard'))
        
        else:  # Assuming this is a student
            if not user.is_registered:  # Check if the student has completed registration
                return redirect(url_for('main.complete_registration'))
            return redirect(url_for('main.student_options'))

    else:
        # Prepare new user information
        new_user_info = {
            'email': user_info['email'],
            'google_id': user_info['sub'],  # Store Google OAuth ID
            'is_teacher': False,  # Default values
            'is_admin': False
        }

        # Log the new user's email for debugging
        current_app.logger.info(f'New user {new_user_info["email"]} needs to complete registration.')
        print("New User Info:", new_user_info)

        # Set session variable to indicate user needs to complete registration
        session['new_user'] = True
        session['new_user_info'] = new_user_info  # Store the new user info temporarily

        return redirect(url_for('main.complete_registration'))  # Redirect to complete registration


@main.route('/complete_registration', methods=['GET', 'POST'])
def complete_registration():
    form = CompleteRegistrationForm()
    current_app.logger.debug(f"Session before registration: {session}")

    # Check if the user is new
    if 'new_user' in session:
        # If the form is submitted and valid
        if form.validate_on_submit():
            # Retrieve the new user info from the session
            new_user_info = session.get('new_user_info')
            print("New User Info:", new_user_info)

            # Create a new User instance with the retrieved info
            new_user = User(
                email=new_user_info['email'],
                google_id=new_user_info['google_id'],
                is_teacher=new_user_info.get('is_teacher', False),
                is_admin=new_user_info.get('is_admin', False),
                is_registered=True,  # Mark as registered upon completion
            )

            # Save the new user to the database
            db.session.add(new_user)
            db.session.commit()  # Commit to get the new user's ID

            # Now create the associated student or teacher entry
            if form.user_type.data == 'student':
                student = Student(
                    user_id=new_user.id,  # This is now correctly set
                    student_id=form.student_id.data,
                    name=form.student_name.data,
                    department=form.student_department.data,
                    semester=form.student_semester.data,
                    batch=form.student_batch.data
                )
                db.session.add(student)
            elif form.user_type.data == 'teacher':
                teacher = Teacher(
                    user_id=new_user.id,  # This is now correctly set
                    teacher_id=form.teacher_id.data,
                    name=form.teacher_name.data,
                    department=form.teacher_department.data
                )
                db.session.add(teacher)

            # Commit again to save the associated records
            db.session.commit()

            # Log in the new user
            login_user(new_user)

            # Cleanup session variable
            session.pop('new_user', None)
            session.pop('new_user_info', None)

            # Redirect to the appropriate dashboard based on user type
            if new_user.is_teacher:
                return redirect(url_for('main.teacher_options'))
            elif new_user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.student_options'))

        # Render the registration form if the user is new and the form hasn't been submitted
        return render_template('complete_registration.html', form=form)

    # If user is not new, redirect to the login page or wherever appropriate
    return redirect(url_for('main.google_login'))

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')  # Optional flash message
    
    return redirect(url_for('main.login'))


#-> Passed image_paths instead of images to train_model().
@main.route('/train_model', methods=['GET', 'POST'])
@login_required
def train_model_route():
    form = UploadForm()
    training_complete = False

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('photos')  # List of FileStorage objects
        student_id = form.student_id.data

        if not student_id:
            flash('Student ID is required.', 'danger')
            return redirect(url_for('main.train_model_route'))

        image_paths = []
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    file.save(file_path)
                    image_paths.append(file_path)
                except Exception as e:
                    flash(f'Error processing file {filename}: {str(e)}', 'danger')
                    continue

        if image_paths:
            flash('Photos uploaded. Training in progress...', 'info')
            db.session.commit()  # Ensure any previous changes are committed

            # Get model directory dynamically
            model_directory = get_model_directory()

            # Train the model using the CNN approach
            try:
                success = train_model(student_id, image_paths, model_directory)  # Pass model_directory
                if success:
                    flash('Model trained successfully!', 'success')
                    training_complete = True
                    return redirect(url_for('main.test_model'))
                else:
                    flash('Failed to train model. Please try again.', 'danger')
            except Exception as e:
                flash(f'Error during model training: {str(e)}', 'danger')
        else:
            flash('No valid images uploaded.', 'danger')

    return render_template('train_model.html', form=form, training_complete=training_complete)


@main.route('/view_schedule_teacher')
@login_required
def view_schedule_teacher():
    if not current_user.is_teacher:
        abort(403)  # Forbidden if the user is not a teacher

    # Define days and periods
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']

    # Query schedule entries for the teacher
    schedule_entries = ScheduleEntry.query.filter_by(teacher_id=current_user.teacher_profile.id).all()
    
    # Initialize the schedule dictionary
    schedule = {day: {period: None for period in periods} for day in days}

    for entry in schedule_entries:
        period_key = f"{entry.time_start}-{entry.time_end}"
        if period_key in schedule[entry.day_of_week]:
            schedule[entry.day_of_week][period_key] = entry.classroom

    # Query attendance status for the teacher's schedule
    attendance_entries = AttendanceStatus.query.all()
    attendance_status = {(entry.day, entry.period): entry.status for entry in attendance_entries}

    return render_template(
        'view_schedule_teacher.html', 
        days=days, 
        periods=periods, 
        schedule=schedule,
        attendance_status=attendance_status
    )


@main.route('/view_schedule_student/<student_id>', methods=['GET', 'POST'])
@login_required
def view_schedule_student(student_id):
    # Fetch student by student_id
    current_student = Student.query.filter_by(student_id=student_id).first()

    if not current_student:
        abort(404)  # Student not found

    # Check if the user is allowed to view the schedule
    if not (current_user.is_admin or 
            (current_user.is_teacher and current_student.user_id == current_user.id) or
            (current_user.id == current_student.user_id)):
        abort(403)  # Forbidden

    if request.method == 'POST':
        # Handle location check
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        if latitude and longitude:
            if not is_within_school(float(latitude), float(longitude)):
                return jsonify({'status': 'error', 'message': 'You are not within the school premises.'})
        return jsonify({'status': 'success'})

    # Fetch the student's schedule entries based on department, batch, and semester
    schedule_entries = ScheduleEntry.query.filter(
        ScheduleEntry.department == current_student.department,
        ScheduleEntry.batch == current_student.batch,
        ScheduleEntry.semester == current_student.semester
    ).all()

    # Initialize schedule dictionary
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']

    schedule = {day: {period: None for period in periods} for day in days}

    for entry in schedule_entries:
        day = entry.day_of_week
        period = f"{entry.time_start}-{entry.time_end}"
        if day in schedule and period in schedule[day]:
            schedule[day][period] = entry

    # Fetch attendance status for the student's schedule
    attendance_entries = AttendanceStatus.query.all()
    attendance_status = {(entry.day, entry.period): entry.status for entry in attendance_entries}

    # Fetch the manual attendance feature toggle status
    manual_attendance_feature = FeatureToggle.query.filter_by(feature_name='manual_attendance').first()
    manual_attendance_enabled = manual_attendance_feature.is_enabled if manual_attendance_feature else False

    return render_template(
        'view_schedule_student.html', 
        schedule=schedule, 
        days=days, 
        periods=periods, 
        student_id=student_id, 
        student_name=current_student.name,
        attendance_status=attendance_status,
        manual_attendance_enabled=manual_attendance_enabled,  # Use the boolean instead
        student=current_student
    )


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# @main.route('/admin_view_schedules', methods=['GET', 'POST'])
# @login_required
# def admin_view_schedules():
#     if not current_user.is_admin:
#         abort(403)  # Forbidden if the user is not an admin

#     # Retrieve distinct filter options
#     departments = [dept[0] for dept in db.session.query(Teacher.department).distinct()]
#     semesters = [sem[0] for sem in db.session.query(Student.semester).distinct()]
#     batches = [batch[0] for batch in db.session.query(Student.batch).distinct()]
#     teachers = [teacher.id for teacher in Teacher.query.all()]

#     # Get filter values from request arguments
#     filters = {
#         'department': request.args.get('department'),
#         'semester': request.args.get('semester'),
#         'batch': request.args.get('batch'),
#         'teacher_id': request.args.get('teacher_id')
#     }

#     # Log filter values
#     logger.info(f"Filters applied: {filters}")

#     # Build query based on filters
#     schedule_entries = ScheduleEntry.query

#     # Create table aliases
#     StudentAlias = aliased(Student)
#     TeacherAlias = aliased(Teacher)

#     if filters['department']:
#         schedule_entries = schedule_entries.join(TeacherAlias).filter(TeacherAlias.department == filters['department'])
#     if filters['semester'] or filters['batch']:
#         schedule_entries = schedule_entries.join(StudentAlias).filter(
#             and_(
#                 (StudentAlias.semester == filters['semester']) if filters['semester'] else True,
#                 (StudentAlias.batch == filters['batch']) if filters['batch'] else True
#             )
#         )
#     if filters['teacher_id']:
#         schedule_entries = schedule_entries.filter(ScheduleEntry.teacher_id == filters['teacher_id'])

#     # Log the generated SQL query
#     query_str = str(schedule_entries.statement.compile(compile_kwargs={"literal_binds": True}))
#     logger.info(f"Generated SQL query: {query_str}")

#     schedule_entries = schedule_entries.all()

#     # Initialize the schedule dictionary
#     days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
#     periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
#     schedule = {day: {period: [] for period in periods} for day in days}

#     for entry in schedule_entries:
#         period_key = f"{entry.time_start}-{entry.time_end}"
#         if period_key in schedule[entry.day_of_week]:
#             schedule[entry.day_of_week][period_key].append({
#                 'id': entry.id,
#                 'classroom': entry.classroom,
#                 'teacher_id': entry.teacher_id
#             })

#     return render_template('admin_view_schedules.html', days=days, periods=periods, schedule=schedule,
#                            departments=departments, semesters=semesters, batches=batches, teachers=teachers)





@main.route('/admin_view_schedules', methods=['GET', 'POST'])
@login_required
def admin_view_schedules():
    if not current_user.is_admin:
        abort(403)

    # Retrieve distinct filter options
    departments = [dept[0] for dept in db.session.query(Teacher.department).distinct()]
    semesters = [sem[0] for sem in db.session.query(Student.semester).distinct()]
    batches = [batch[0] for batch in db.session.query(Student.batch).distinct()]
    teachers = [teacher.id for teacher in Teacher.query.all()]

    # Get filter values from request arguments
    filters = {
        'department': request.args.get('department'),
        'semester': request.args.get('semester'),
        'batch': request.args.get('batch'),
        'teacher_id': request.args.get('teacher_id')
    }

    # Build query based on filters
    schedule_entries = ScheduleEntry.query

    if filters['department']:
        schedule_entries = schedule_entries.join(Teacher).filter(Teacher.department == filters['department'])
    if filters['semester']:
        schedule_entries = schedule_entries.join(Student).filter(Student.semester == filters['semester'])
    if filters['batch']:
        schedule_entries = schedule_entries.join(Student).filter(Student.batch == filters['batch'])
    if filters['teacher_id']:
        schedule_entries = schedule_entries.filter(ScheduleEntry.teacher_id == filters['teacher_id'])

    # Fetch and deduplicate schedule entries
    schedule_entries = schedule_entries.distinct().all()

    # Initialize the schedule dictionary
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    schedule = {day: {period: [] for period in periods} for day in days}

    # Track seen entries to avoid duplicates
    seen_entries = set()

    for entry in schedule_entries:
        period_key = f"{entry.time_start}-{entry.time_end}"
        entry_key = (entry.day_of_week, entry.time_start, entry.time_end, entry.classroom, entry.teacher_id, entry.course_name)

        if period_key in schedule[entry.day_of_week] and entry_key not in seen_entries:
            schedule[entry.day_of_week][period_key].append({
                'id': entry.id,
                'classroom': entry.classroom,
                'teacher_id': entry.teacher_id
            })
            seen_entries.add(entry_key)  # Mark this entry as processed

    return render_template('admin_view_schedules.html',
                           days=days, periods=periods, schedule=schedule,
                           departments=departments, semesters=semesters,
                           batches=batches, teachers=teachers)






@main.route('/edit_schedule/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(entry_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden if the user is not an admin

    entry = ScheduleEntry.query.get(entry_id)
    if not entry:
        abort(404)  # Schedule entry not found

    departments = Student.query.with_entities(Student.department).distinct().all()
    semesters = [str(i) for i in range(1, 9)]
    batches = [chr(i) for i in range(ord('A'), ord('G') + 1)]
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '5:00-6:00']
    teachers = Teacher.query.all()

    if request.method == 'POST':
        day_of_week = request.form['day_of_week']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        classroom = request.form['classroom']
        teacher_id = request.form['teacher_id']
        department = request.form['department']
        semester = request.form['semester']
        batch = request.form['batch']
        course_name = request.form['course_name']

        # Dynamically insert or find the class in the Class table
        schedule_str = f"{day_of_week} {time_start}-{time_end}"
        existing_class = Class.query.filter_by(name=course_name, teacher_id=teacher_id, schedule=schedule_str).first()

        if not existing_class:
            new_class = Class(name=course_name, teacher_id=teacher_id, schedule=schedule_str)
            db.session.add(new_class)
            db.session.commit()
            class_id = new_class.id
        else:
            class_id = existing_class.id

        # Update the schedule entry with the new information
        entry.day_of_week = day_of_week
        entry.time_start = time_start
        entry.time_end = time_end
        entry.classroom = classroom
        entry.teacher_id = teacher_id
        entry.department = department
        entry.semester = semester
        entry.batch = batch
        entry.course_name = course_name

        db.session.commit()
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('main.admin_view_schedules'))

    return render_template('edit_schedule.html',
                           entry=entry,
                           departments=departments, 
                           semesters=semesters, 
                           batches=batches, 
                           days=days, 
                           periods=periods, 
                           teachers=teachers)


@main.route('/delete_schedule/<int:entry_id>')
@login_required
def delete_schedule(entry_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden if the user is not an admin

    entry = ScheduleEntry.query.get(entry_id)
    if not entry:
        abort(404)  # Schedule entry not found

    db.session.delete(entry)
    db.session.commit()
    flash('Schedule deleted successfully!', 'success')
    return redirect(url_for('main.admin_view_schedules'))


@main.route('/recognize_face', methods=['POST'])
def recognize_face_route():
    data = request.get_json()
    image_data = data.get('image')
    student_id = data.get('student_id')
       
    if not image_data or not student_id:
        return jsonify({'error': 'Invalid request'}), 400

    model_directory = get_model_directory()  # Get the model directory

    try:
        # Recognize face
        recognized_id = recognize_face(image_data, student_id, model_directory)
        if recognized_id:
            return jsonify({'student_id': recognized_id})
        else:
            return jsonify({'error': 'No student recognized'})
    except Exception as e:
        logging.error(f"Error during face recognition: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred. Check the log for details.'}), 500


@main.route('/test_model')
@login_required
def test_model():
    student_profile = current_user.student_profile

    if student_profile:
        student_id = student_profile.student_id
        return render_template('test_model.html', student_id=student_id)
    else:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('main.train_model_route'))
    

@main.route('/process_attendance', methods=['POST'])
@login_required
def process_attendance():
    logging.debug(f"Current user: {current_user}")

    try:
        data = request.json
        image_data = data.get('image_data')
        student_id = data.get('student_id')
        course_name = data.get('course_name')  # Use course_name instead of classroom

        logging.debug(f"Received image data length: {len(image_data) if image_data else 'None'}")
        logging.debug(f"Received student ID: {student_id}")
        logging.debug(f"Received course name: {course_name}")

        if image_data and student_id and course_name:
            model_directory = get_model_directory()
            recognized_id = recognize_face(image_data, student_id, model_directory)

            if recognized_id:
                logging.debug(f"Face recognized. Recording attendance for student ID: {student_id}")

                # Fetch student record using student_id
                student = Student.query.filter_by(student_id=student_id).first()

                if student:
                    # Fetch the corresponding Class instance using course_name
                    class_instance = Class.query.filter_by(name=course_name).first()

                    if class_instance:
                        # Create attendance record
                        attendance_record = AttendanceRecord(
                            student_id=student.id,  # Use student.id for the record
                            class_id=class_instance.id,  # Use the ID of the class instance
                            timestamp=datetime.utcnow(),
                            present=True
                        )
                        db.session.add(attendance_record)
                        db.session.commit()

                        # Fetch the student name for response
                        student_name = student.name
                        return jsonify({'success': True, 'student_name': student_name}), 200
                    else:
                        return jsonify({'success': False, 'error': 'Class not found.'}), 400
                else:
                    return jsonify({'success': False, 'error': 'Student not found.'}), 400
            else:
                return jsonify({'success': False, 'error': 'Face not recognized.'}), 400
        else:
            return jsonify({'success': False, 'error': 'No image data, student ID, or course name received.'}), 400
    except Exception as e:
        logging.error(f"Error processing attendance: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while processing attendance.'}), 500


@main.route('/attendance') #for student
@login_required
def attendance():
    # Fetch the student based on the current user
    student = Student.query.filter_by(user_id=current_user.id).first()

    if student:
        # Fetch attendance records for the student, including related Class data
        attendance_records = (
            AttendanceRecord.query
            .filter_by(student_id=student.id)
            .join(Class)  # Join the Class model
            .all()
        )
    else:
        attendance_records = []

    # Check if there are no attendance records
    if not attendance_records:
        flash('No attendance records found. Please take attendance first.', 'info')
        return redirect(url_for('main.student_options'))

    course_attendance = {}

    # Create a dictionary to store course names from the Class table
    classes = Class.query.all()
    logging.debug(f"Fetched Classes: {classes}")
    for cls in classes:
        logging.debug(f"Class ID: {cls.id}, Name: {cls.name}")

    schedule_entry_map = {cls.id: cls.name for cls in classes}

    # Debugging output to verify the mapping
    logging.debug("Class Entry Map: %s", schedule_entry_map)

    for record in attendance_records:
        # Fetch the course name from class entry map using the class_id
        course_name = schedule_entry_map.get(record.class_id, 'Unknown Course')
        logging.debug(f"Record ID: {record.id}, Class ID: {record.class_id}, Course Name: {course_name}")

        if course_name not in course_attendance:
            course_attendance[course_name] = {
                'total_classes': 0,
                'attended_classes': 0
            }
        course_attendance[course_name]['total_classes'] += 1
        if record.present:
            course_attendance[course_name]['attended_classes'] += 1

    # Print out the course attendance for debugging
    print("Course Attendance Data:", course_attendance)

    # Calculate attendance percentage for each course
    for course, data in course_attendance.items():
        total_classes = data['total_classes']
        attended_classes = data['attended_classes']
        if total_classes > 0:
            data['attendance_percentage'] = int((attended_classes / total_classes) * 100)
        else:
            data['attendance_percentage'] = 0

    return render_template('attendance.html', attendance_records=attendance_records, course_attendance=course_attendance)


@main.route('/admin/view_all_student_attendance', methods=['GET'])
@login_required
def view_all_student_attendance():
    if not current_user.is_admin:
        return "Access denied", 403

    semester = request.args.get('semester')
    batch = request.args.get('batch')
    department = request.args.get('department')
    student_id = request.args.get('student_id')

    # Filter students based on provided criteria
    query = Student.query

    if semester:
        query = query.filter_by(semester=semester)
    if batch:
        query = query.filter_by(batch=batch)
    if department:
        query = query.filter_by(department=department)
    if student_id:
        query = query.filter_by(student_id=student_id)

    students = query.all()
    student_ids = [student.id for student in students]
    attendance_records = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(student_ids)).all()

    student_data = []
    for student in students:
        records = [rec for rec in attendance_records if rec.student_id == student.id]
        total_classes = len(records)
        attended_classes = sum(rec.present for rec in records)
        attendance_percentage = int((attended_classes / total_classes) * 100) if total_classes > 0 else 0

        student_data.append({
            'student_id': student.student_id,
            'student_name': student.name,
            'total_classes': total_classes,
            'attended_classes': attended_classes,
            'attendance_percentage': attendance_percentage
        })

    # Get unique semesters, batches, and departments for filtering
    semesters = Student.query.with_entities(Student.semester).distinct().all()
    batches = Student.query.with_entities(Student.batch).distinct().all()
    departments = Student.query.with_entities(Student.department).distinct().all()

    return render_template('admin_all_student_attendance.html',
                           attendance_records=student_data,
                           semesters=[sem[0] for sem in semesters],
                           batches=[bat[0] for bat in batches],
                           departments=[dept[0] for dept in departments])


@main.route('/admin/attendance_visualizations', methods=['GET'])
@login_required
def attendance_visualizations():
    if not current_user.is_admin:
        return "Access denied", 403

    # Query Attendance Records and Student Data
    attendance_records, students = get_attendance_and_students()

    # Aggregating Attendance Data
    course_attendance = aggregate_course_attendance(attendance_records)
    courses, attendance_percentages = calculate_course_attendance_percentage(course_attendance)

    department_attendance = aggregate_department_attendance(students, attendance_records)
    departments, dept_attendance_percentages = calculate_department_attendance_percentage(department_attendance)

    # Low Attendance Data
    low_attendance_data = get_low_attendance_students(attendance_records, students)

    # Generate URLs for attendance plots
    course_plot_url = get_attendance_by_course(attendance_records)
    department_plot_url = get_attendance_by_department(attendance_records, students)

          # Additional Analytics and Projections
    max_distance = 50  # Example maximum distance in kilometers

    # Geolocation analysis based on a fixed school location (for POST requests)
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    if request.method == 'POST' and latitude and longitude:
        try:
            school_location = (float(latitude), float(longitude))
            attendance_by_distance = analyze_attendance_by_distance(school_location, max_distance)
        except ValueError:
            # Handle the case where conversion to float fails
            flash('Invalid latitude or longitude values provided', 'danger')
            attendance_by_distance = None
    else:
        attendance_by_distance = None  # Default value for GET requests or missing form data

    # GPS-Based Attendance (POST request, with latitude and longitude provided)
    if request.method == 'POST' and latitude and longitude:
        try:
            gps_attendance = get_attendance_by_location(
                student_id=1, latitude=float(latitude), longitude=float(longitude), max_distance_km=max_distance)
        except ValueError:
            gps_attendance = None  # Handle error gracefully
    else:
        gps_attendance = None  # Default value if no coordinates are provided



    # Feature Usage Insights
    feature_usage = feature_usage_analysis()

    # Sort Courses by Attendance (Optional filters for department, batch, semester)
    sorted_courses = get_courses_by_attendance(department='CS', batch=2024, semester=1)

    # Class Attendance Comparison
    class_attendance_comparison = compare_class_attendance()

    # Teacher Performance Analysis
    teacher_performance = teacher_attendance_analysis()

    # Peak Attendance Times
    peak_times = peak_attendance_times()

    # Department-Wise Attendance
    department_wise_attendance_data = department_wise_attendance()

    # Student Punctuality (Late Comers)
    late_comers = get_late_comers()

    # Historical attendance trend (Provide date range)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 10, 1)
    attendance_trend = get_attendance_trend(start_date, end_date)

    # Attendance projections (Predict for future days for a course)
    projected_attendance = project_attendance(class_id=1, days_in_future=30)

    # Flagging low attendance students and courses
    low_attendance_students = flag_low_attendance_students(threshold=60)
    low_attendance_courses = flag_low_attendance_courses(threshold=70)

    # === New Functions Integration ===

    # Pie Chart for Department-Wise Attendance
    department_attendance_pie = get_department_attendance()

    # Batch-Wise Attendance Toggle for Department
    batch_attendance = get_batch_attendance(department='CS')

    # Attendance by Student, Class, Teacher
    student_attendance = get_student_attendance(student_id=1)  # Example student_id
    class_attendance = get_class_attendance(class_id=1)  # Example class_id
    teacher_classes_attendance = get_teacher_classes_attendance(teacher_id=1)  # Example teacher_id

    # Attendance Status by Day/Period
    attendance_status = is_attendance_allowed(day='Monday', period='09:00')  # Example values

    # Teacher Attendance Summary
    teacher_attendance_summary = get_teacher_attendance_summary(teacher_id=1, day='Monday', period='09:00')

    # Frequent Absentees
    frequent_absentees = get_frequent_absentees(threshold=0.7)

    # Attendance and Performance Correlation
    student_performance = {1: 'A+', 2: 'B'}  # Example performance data
    attendance_performance_correlation = correlate_attendance_with_performance(student_id=1, performance_data=student_performance)

    # Students Attendance by Course
    students_by_course_attendance = get_students_by_course_attendance(class_id=1)

    # Ensure data is not None before rendering
    return render_template(
        'admin_attendance_visualizations.html',
        courses=courses or [],
        attendance_percentages=attendance_percentages or [],
        departments=departments or [],
        dept_attendance_percentages=dept_attendance_percentages or [],
        low_attendance_data=low_attendance_data or [],
        course_plot_url=course_plot_url,
        department_plot_url=department_plot_url,
        class_attendance_comparison=class_attendance_comparison,  # Class Attendance Comparison
        teacher_performance=teacher_performance,  # Teacher Performance Analysis
        peak_times=peak_times,  # Peak Attendance Times
        department_wise_attendance=department_wise_attendance_data,  # Department-Wise Attendance
        late_comers=late_comers,  # Student Punctuality
        attendance_by_distance=attendance_by_distance or {},  # Geolocation analysis
        feature_usage=feature_usage or [],  # Feature usage insights
        sorted_courses=sorted_courses or [],  # Courses sorted by attendance
        attendance_trend=attendance_trend or [],  # Historical attendance trend
        projected_attendance=projected_attendance or 0,  # Attendance projection
        low_attendance_students=low_attendance_students or [],  # Low attendance students
        low_attendance_courses=low_attendance_courses or [],  # Low attendance courses
        max_distance=max_distance,

        # New Data for Pie Charts and Toggles
        department_attendance_pie=department_attendance_pie or [],
        batch_attendance=batch_attendance or [],
        student_attendance=student_attendance or [],
        class_attendance=class_attendance or [],
        teacher_classes_attendance=teacher_classes_attendance or [],
        gps_attendance=gps_attendance or [],
        attendance_status=attendance_status or [],
        teacher_attendance_summary=teacher_attendance_summary or [],
        frequent_absentees=frequent_absentees or [],
        attendance_performance_correlation=attendance_performance_correlation or [],
        students_by_course_attendance=students_by_course_attendance or []

    )


@main.route('/view_student_attendance', methods=['GET']) #for teacher
@login_required
def view_student_attendance():
    # Fetch the teacher profile based on the current user
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        return "Teacher profile not found", 404

    # Fetch filter parameters from the request
    semester = request.args.get('semester')
    batch = request.args.get('batch')
    department = request.args.get('department')
    student_id = request.args.get('student_id')

    # Fetch all classes for the teacher
    classes = Class.query.filter_by(teacher_id=teacher.id).all()

    # Initialize the list to store attendance records
    filtered_attendance_records = []

    # Iterate over each class
    for cls in classes:
        # Fetch attendance records for the class, applying filters
        query = AttendanceRecord.query.join(Student).filter(AttendanceRecord.class_id == cls.id)

        if semester:
            query = query.filter(Student.semester == semester)
        if batch:
            query = query.filter(Student.batch == batch)
        if department:
            query = query.filter(Student.department == department)
        if student_id:
            query = query.filter(Student.id == student_id)

        records = query.all()

        for record in records:
            student = record.student
            # Find or create the attendance summary for this student in this class
            attendance_summary = next((item for item in filtered_attendance_records 
                                       if item['student_id'] == student.id and item['class_name'] == cls.name), None)
            if attendance_summary is None:
                attendance_summary = {
                    'student_id': student.id,
                    'student_name': student.name,
                    'class_name': cls.name,
                    'total_classes': 0,
                    'attended_classes': 0,
                }
                filtered_attendance_records.append(attendance_summary)

            # Update attendance summary
            attendance_summary['total_classes'] += 1
            if record.present:
                attendance_summary['attended_classes'] += 1

    # Calculate attendance percentage for each record
    for summary in filtered_attendance_records:
        summary['attendance_percentage'] = (summary['attended_classes'] / summary['total_classes']) * 100 if summary['total_classes'] > 0 else 0

    # Fetch unique semesters, batches, and departments for filters
    semesters = Student.query.with_entities(Student.semester).distinct().all()
    batches = Student.query.with_entities(Student.batch).distinct().all()
    departments = Student.query.with_entities(Student.department).distinct().all()

    return render_template(
        'view_student_attendance.html', 
        attendance_records=filtered_attendance_records, 
        semesters=[s.semester for s in semesters],
        batches=[b.batch for b in batches],
        departments=[d.department for d in departments]
    )

@main.route('/create_schedule', methods=['GET', 'POST'])
@login_required
def create_schedule(): #the schedule inconsistency bug is fixed
    if not current_user.is_admin:
        abort(403)

    departments = Student.query.with_entities(Student.department).distinct().all()
    semesters = [str(i) for i in range(1, 9)]
    batches = [chr(i) for i in range(ord('A'), ord('G') + 1)]
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '5:00-6:00']
    teachers = Teacher.query.all()

    if request.method == 'POST':
        day_of_week = request.form['day_of_week']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        classroom = request.form['classroom']
        teacher_id = request.form['teacher_id']
        department = request.form['department']
        semester = request.form['semester']
        batch = request.form['batch']
        course_name = request.form['course_name']  # New field

        # Dynamically insert or find the class in the Class table
        schedule_str = f"{day_of_week} {time_start}-{time_end}"
        existing_class = Class.query.filter_by(name=course_name, teacher_id=teacher_id, schedule=schedule_str).first()

        if not existing_class:
            new_class = Class(name=course_name, teacher_id=teacher_id, schedule=schedule_str)
            db.session.add(new_class)
            db.session.commit()
            class_id = new_class.id
        else:
            class_id = existing_class.id

        # Handle teacher schedule entry
        if teacher_id:
            existing_entry = ScheduleEntry.query.filter_by(
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                time_start=time_start,
                time_end=time_end
            ).first()
            if existing_entry:
                existing_entry.classroom = classroom
                existing_entry.course_name = course_name  # Set course name
                existing_entry.department = None
                existing_entry.batch = None
                existing_entry.semester = None
            else:
                new_entry = ScheduleEntry(
                    teacher_id=teacher_id,
                    day_of_week=day_of_week,
                    time_start=time_start,
                    time_end=time_end,
                    classroom=classroom,
                    course_name=course_name  # Set course name
                )
                db.session.add(new_entry)

        # Handle student schedule entry
        if department or semester or batch:
            students = Student.query.filter_by(department=department, semester=semester, batch=batch).all()
            print(f"Students found: {[student.id for student in students]}")
            for student in students:
                existing_entry = ScheduleEntry.query.filter_by(
                    student_id=student.id,
                    day_of_week=day_of_week,
                    time_start=time_start,
                    time_end=time_end
                ).first()
                if existing_entry:
                    existing_entry.classroom = classroom
                    existing_entry.teacher_id = teacher_id
                    existing_entry.course_name = course_name  # Set course name
                    existing_entry.department = department
                    existing_entry.batch = batch
                    existing_entry.semester = semester
                else:
                    new_entry = ScheduleEntry(
                        student_id=student.id,
                        day_of_week=day_of_week,
                        time_start=time_start,
                        time_end=time_end,
                        classroom=classroom,
                        teacher_id=teacher_id,
                        course_name=course_name,  # Set course name
                        department=department,
                        batch=batch,
                        semester=semester
                    )
                    db.session.add(new_entry)

            # Commit once after both teacher and student schedules are handled
            db.session.commit()

            #flash('Student schedule updated successfully!', 'success')

            flash('Schedule updated successfully!', 'success')
            return redirect(url_for('main.create_schedule'))

    return render_template('create_schedule.html', 
                           departments=departments, 
                           semesters=semesters, 
                           batches=batches, 
                           days=days, 
                           periods=periods, 
                           teachers=teachers)

@main.route('/take_attendance', methods=['GET'])
@login_required
def take_attendance():
    day = request.args.get('day')
    period = request.args.get('period')
    student_id = request.args.get('student_id')

    # Check if the current user is a student or a teacher
    if not current_user.is_teacher and not current_user.student_profile:
        abort(403)

    # Get student_id from the current user if not provided
    if not student_id:
        student_profile = current_user.student_profile
        student_id = student_profile.student_id if student_profile else None

    if not student_id:
        flash('Student ID not found.', 'error')
        return render_template('take_attendance.html', day=day, period=period, student_id=None, classroom=None)

    # Retrieve student profile to get department, batch, and semester
    student_profile = Student.query.filter_by(student_id=student_id).first()
    if not student_profile:
        flash('Student profile not found.', 'error')
        return render_template('take_attendance.html', day=day, period=period, student_id=student_id, classroom=None)
    
    department = student_profile.department
    batch = student_profile.batch
    semester = student_profile.semester

    # Debugging: Log the parameters
    logging.debug(f"Searching for schedule entry with Day: {day}, Period: {period}, Department: {department}, Batch: {batch}, Semester: {semester}")

    # Check if period is provided
    if not period:
        logging.error("Period is not provided.")
        flash('Period is required.', 'error')
        return render_template('take_attendance.html', day=day, period=period, student_id=student_id, classroom=None)

    # Split period into start and end times
    try:
        period_start, period_end = period.split('-')
        period_start = period_start.strip()
        period_end = period_end.strip()
    except ValueError:
        logging.error(f"Error splitting period: {period}")
        flash('Invalid period format.', 'error')
        return render_template('take_attendance.html', day=day, period=period, student_id=student_id, classroom=None)

    # Find the course name using day, period, and student profile attributes
    schedule_entries = ScheduleEntry.query.filter_by(
        day_of_week=day,
        time_start=period_start,
        time_end=period_end,
        department=department,
        batch=batch,
        semester=semester
    ).all()

    logging.debug(f"Schedule Entries Found: {len(schedule_entries)}")
    
    course_name = None
    for entry in schedule_entries:
        logging.debug(f"Checking Entry: Course Name: {entry.course_name}")
        # Assuming that if any entry matches, it should be used
        if entry.course_name:
            course_name = entry.course_name
            break

    if not course_name:
        flash('No schedule entry found for the given details.', 'error')
        return render_template('take_attendance.html', day=day, period=period, student_id=student_id, classroom=None)
    
    return render_template('take_attendance.html', day=day, period=period, student_id=student_id, classroom=course_name)


@main.route('/update_location', methods=['POST'])
@login_required
def update_location():
    latitude = request.form['latitude']
    longitude = request.form['longitude']

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student:
        student.latitude = float(latitude)
        student.longitude = float(longitude)
        db.session.commit()

    flash('Location updated successfully!', 'success')
    return redirect(url_for('main.view_schedule_student'))


@main.route('/check_student_location', methods=['POST'])
def check_student_location():
    try:
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))

        current_app.logger.debug(f"Received data(from browser) - Latitude: {latitude}, Longitude: {longitude}")

        checked_val =  is_within_school(latitude, longitude)
        if checked_val:
            return jsonify({'status': 'success'})
        else:
            current_app.logger.debug(f"checked val :{checked_val}")
            
            return jsonify({'status': 'error', 'message': 'You are not within the allowed area to take attendance.'})

    except Exception as e:
        current_app.logger.error(f"Exception occurred: {e}")
        return jsonify({'status': 'error', 'message': 'An error occurred.'})


@main.route('/view_filtered_student_attendance', methods=['GET'])
@login_required
def view_filtered_student_attendance():
    semester = request.args.get('semester')
    batch = request.args.get('batch')
    department = request.args.get('department')
    student_id = request.args.get('student_id')

    # Fetch all students for the current teacher
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        return "Teacher profile not found", 404

    classes = Class.query.filter_by(teacher_id=teacher.id).all()
    class_ids = [cls.id for cls in classes]

    # Filter students based on class assignments and other criteria
    query = Student.query.filter(Student.id.in_(
        AttendanceRecord.query.filter(AttendanceRecord.class_id.in_(class_ids)).with_entities(AttendanceRecord.student_id)
    ))

    if semester:
        query = query.filter_by(semester=semester)
    if batch:
        query = query.filter_by(batch=batch)
    if department:
        query = query.filter_by(department=department)
    if student_id:
        query = query.filter_by(student_id=student_id)
    
    students = query.all()

    # Fetch attendance records for these students
    student_ids = [student.id for student in students]
    attendance_records = AttendanceRecord.query.filter(AttendanceRecord.student_id.in_(student_ids)).all()

    # Create a dictionary to map class IDs to class names
    class_dict = {}
    for record in attendance_records:
        class_ = Class.query.get(record.class_id)
        if class_:
            class_dict[class_.id] = class_.name

    # Prepare data for the template
    student_data = []
    for student in students:
        records = [rec for rec in attendance_records if rec.student_id == student.id]
        total_classes = len(records)
        attended_classes = sum(rec.present for rec in records)
        attendance_percentage = int((attended_classes / total_classes) * 100) if total_classes > 0 else 0

        # Fetch class names for each student
        classes = set()
        for rec in records:
            class_name = class_dict.get(rec.class_id, 'Unknown')
            classes.add(class_name)
        
        student_data.append({
            'student_id': student.student_id,
            'student_name': student.name,
            'class_name': ', '.join(classes),  # Join class names if multiple
            'total_classes': total_classes,
            'attended_classes': attended_classes,
            'attendance_percentage': attendance_percentage
        })

    # Get unique semesters, batches, and departments for filtering
    semesters = Student.query.with_entities(Student.semester).distinct().all()
    batches = Student.query.with_entities(Student.batch).distinct().all()
    departments = Student.query.with_entities(Student.department).distinct().all()

    return render_template('view_student_attendance.html', 
                           attendance_records=student_data,
                           semesters=[sem[0] for sem in semesters],
                           batches=[bat[0] for bat in batches],
                           departments=[dept[0] for dept in departments])


@main.route('/student_attendance/<int:student_id>', methods=['GET'])
@login_required
def student_attendance(student_id):
    # Fetch attendance details for the student
    student = Student.query.get_or_404(student_id)
    # Assuming you have a method to get detailed attendance records
    records = get_attendance_details(student)
    return render_template('student_attendance.html', student=student, records=records)


@main.route('/attendance_records', methods=['GET'])
@login_required
def attendance_records():
    students = Student.query.all()
    # Calculate attendance percentage for each student
    # You should have a method to compute this
    student_data = [{'id': student.id, 'attendance_percentage': calculate_attendance_percentage(student)} for student in students]
    return render_template('attendance_records.html', students=student_data)