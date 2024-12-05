from app.models import AttendanceRecord, Student, Class  # Import necessary models
from app import db
from geopy.distance import geodesic
from flask import current_app as app



def is_within_school(latitude, longitude):
    student_coords = (latitude, longitude)
    
    for school_coords in app.config['SCHOOL_LOCATIONS']:
        distance = geodesic(school_coords, student_coords).meters

        app.logger.debug(f"Received GPS location: {student_coords}")
        app.logger.debug(f"Saved school location: {school_coords}")
        app.logger.debug(f"Distance to school: {distance} meters")
        app.logger.debug(f"Allowed radius: {app.config['ALLOWED_RADIUS']}")

        if distance <= app.config['ALLOWED_RADIUS']:
            return True  # The user is within the allowed radius of this school location

    return False  # The user is not within the allowed radius of any school location


def calculate_attendance_percentage(student):
    # Calculate the attendance percentage for a given student
    total_classes = db.session.query(AttendanceRecord).filter_by(student_id=student.id).count()
    attended_classes = db.session.query(AttendanceRecord).filter_by(student_id=student.id, present=True).count()
    if total_classes == 0:
        return 0
    return (attended_classes / total_classes) * 100

def get_attendance_details(student):
    # Fetch detailed attendance records for the given student
    records = db.session.query(AttendanceRecord).filter_by(student_id=student.id).all()
    return records

