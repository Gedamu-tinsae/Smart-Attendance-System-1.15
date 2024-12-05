from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from . import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=True) # Allow nullable for OAuth
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)

    # Add a column to store Google OAuth ID for future reference
    google_id = db.Column(db.String(100), nullable=True, unique=True)

    # New column to track registration status
    is_registered = db.Column(db.Boolean, default=False)  # Default to False
    
    # Relationship fields
    student_profile = db.relationship('Student', uselist=False, back_populates='user')
    teacher_profile = db.relationship('Teacher', uselist=False, back_populates='user')

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    batch = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    manual_attendance_enabled = db.Column(db.Boolean, default=False)  # New column

    user = db.relationship('User', back_populates='student_profile')
    attendance_records = db.relationship('AttendanceRecord', back_populates='student')
    schedule_entries = db.relationship('ScheduleEntry', back_populates='student')

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)

    user = db.relationship('User', back_populates='teacher_profile')
    classes = db.relationship('Class', back_populates='teacher')
    schedule_entries = db.relationship('ScheduleEntry', back_populates='teacher')

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    schedule = db.Column(db.String(150), nullable=False)

    teacher = db.relationship('Teacher', back_populates='classes')
    attendance_records = db.relationship('AttendanceRecord', back_populates='class_')

class ScheduleEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)  # Optional for student schedules
    day_of_week = db.Column(db.String(20), nullable=False)
    time_start = db.Column(db.String(10), nullable=False)
    time_end = db.Column(db.String(10), nullable=False)
    classroom = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=True)  # Added
    batch = db.Column(db.String(50), nullable=True)  # Added
    semester = db.Column(db.String(50), nullable=True)  # Added
    course_name = db.Column(db.String(150), nullable=False)  # Added

    teacher = db.relationship('Teacher', back_populates='schedule_entries')
    student = db.relationship('Student', back_populates='schedule_entries')  # Optional for student schedules


class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    present = db.Column(db.Boolean, default=False)

    student = db.relationship('Student', back_populates='attendance_records')
    class_ = db.relationship('Class', back_populates='attendance_records')

class AttendanceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    period = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Boolean, default=False)  # True if attendance is allowed, False otherwise

class FeatureToggle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    feature_name = db.Column(db.String(50), unique=True, nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)

