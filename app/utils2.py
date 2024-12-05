from .models import User, AttendanceRecord, ScheduleEntry, Student, Teacher, Class, AttendanceStatus, FeatureToggle
from . import db
import base64
import matplotlib
import matplotlib.pyplot as plt
import io
import logging
import base64


matplotlib.use('Agg')  # Use a non-interactive backend

# Disable debug logging for Matplotlib
logging.getLogger('matplotlib').setLevel(logging.WARNING)


def get_attendance_by_course(attendance_records):
    # Aggregating attendance data by course
    course_attendance = {}
    for record in attendance_records:
        course = record.class_.name  # Assuming the course name is stored in the related Class model
        if course not in course_attendance:
            course_attendance[course] = {'total': 0, 'attended': 0}
        course_attendance[course]['total'] += 1
        if record.present:
            course_attendance[course]['attended'] += 1

    # Preparing data for plotting
    courses = list(course_attendance.keys())
    attendance_percentages = [(course_attendance[course]['attended'] / course_attendance[course]['total']) * 100
                              if course_attendance[course]['total'] > 0 else 0
                              for course in courses]

    # Generating plot
    img_course = io.BytesIO()
    plt.figure(figsize=(6, 4), facecolor='lightgray')  # Change 'lightgray' to your desired background color
    ax = plt.gca()  # Get current axes
    ax.set_facecolor('#FFFFFF')  # Change 'white' to your desired axes background color
    plt.figure(figsize=(6, 4))
    plt.bar(courses, attendance_percentages, color='skyblue')
    plt.title('Attendance by Course')
    plt.xlabel('Course')
    plt.ylabel('Attendance Percentage (%)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(img_course, format='png')
    img_course.seek(0)
    plt.close()

    # Returning base64-encoded plot
    return base64.b64encode(img_course.getvalue()).decode('utf-8')



def get_attendance_by_department(attendance_records, students):
    # Aggregating attendance data by department
    department_attendance = {}
    for student in students:
        department = student.department
        if department not in department_attendance:
            department_attendance[department] = {'total': 0, 'attended': 0}

        student_records = [rec for rec in attendance_records if rec.student_id == student.id]
        total_records = len(student_records)
        attended_classes = sum(rec.present for rec in student_records)

        department_attendance[department]['total'] += total_records
        department_attendance[department]['attended'] += attended_classes

    # Preparing data for plotting
    departments = list(department_attendance.keys())
    dept_attendance_percentages = [(department_attendance[dept]['attended'] / department_attendance[dept]['total']) * 100
                                   if department_attendance[dept]['total'] > 0 else 0
                                   for dept in departments]

    # Generating plot
    '''
    Axes Background Color: Set to #FFFFFF for white. You can change it to any valid color.

    Bar Colors: Used '#87CEEB' for sky blue in the course attendance and '#FF7F50' for coral in the department attendance.
    '''
    img_department = io.BytesIO()
    plt.figure(figsize=(6, 4), facecolor='lightgray')  # Change 'lightgray' to your desired background color
    ax = plt.gca()  # Get current axes
    ax.set_facecolor('#FFFFFF')  # Change to white or another valid color
    plt.bar(departments, dept_attendance_percentages, color='#FF7F50')
    plt.title('Attendance by Department')
    plt.xlabel('Department')
    plt.ylabel('Attendance Percentage (%)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(img_department, format='png')
    img_department.seek(0)
    plt.close()

    # Returning base64-encoded plot
    return base64.b64encode(img_department.getvalue()).decode('utf-8')


def get_low_attendance_students(attendance_records, students):
    # Aggregating individual student attendance
    student_attendance = {}
    for student in students:
        student_records = [rec for rec in attendance_records if rec.student_id == student.id]
        total_records = len(student_records)
        attended_classes = sum(rec.present for rec in student_records)
        attendance_percentage = (attended_classes / total_records) * 100 if total_records > 0 else 0
        student_attendance[student.id] = {'name': student.name, 'attendance_percentage': attendance_percentage}

    # Sorting students by lowest attendance
    low_attendance_students = sorted(student_attendance.items(), key=lambda x: x[1]['attendance_percentage'])[:10]  # Bottom 10

    # Generating data for the table
    return [
        {
            'student_id': student_id,
            'name': student_data['name'],
            'attendance_percentage': student_data['attendance_percentage']
        }
        for student_id, student_data in low_attendance_students
    ]


'''
-------------------------------------------------------
'''


# Visualization & Dashboards
# For all these features, you can integrate visual tools like:

# Pie Charts: Show department-wise or course-wise attendance distribution.
# Line Graphs: Visualize trends over time (for departments, courses, or batches).
# Bar Charts: Display students or courses based on attendance levels.
# Chart.js or Plotly

#Query Attendance and Student Data
def get_attendance_and_students():
    attendance_records = AttendanceRecord.query.all()
    students = Student.query.all()
    return attendance_records, students

# Aggregating Attendance Data by Course
def aggregate_course_attendance(attendance_records):
    course_attendance = {}
    for record in attendance_records:
        course = record.class_.name  # Assuming you want to use the class name as the course name
        if course not in course_attendance:
            course_attendance[course] = {'total': 0, 'attended': 0}
        course_attendance[course]['total'] += 1
        if record.present:
            course_attendance[course]['attended'] += 1
    return course_attendance


#Calculate Attendance Percentages for Courses
def calculate_course_attendance_percentage(course_attendance):
    courses = list(course_attendance.keys())
    attendance_percentages = []
    
    for course in courses:
        total = course_attendance[course]['total']
        attended = course_attendance[course]['attended']
        attendance_percentage = (attended / total) * 100 if total > 0 else 0  # Avoid division by zero
        attendance_percentages.append(attendance_percentage)
    
    return courses, attendance_percentages



#Aggregating Attendance Data by Department
def aggregate_department_attendance(students, attendance_records):
    department_attendance = {}
    for student in students:
        department = student.department
        if department not in department_attendance:
            department_attendance[department] = {'total': 0, 'attended': 0}

        student_records = [rec for rec in attendance_records if rec.student_id == student.id]
        total_records = len(student_records)
        attended_classes = sum(rec.present for rec in student_records)

        department_attendance[department]['total'] += total_records
        department_attendance[department]['attended'] += attended_classes
    
    return department_attendance

# Calculate Attendance Percentages for Departments
def calculate_department_attendance_percentage(department_attendance):
    departments = list(department_attendance.keys())
    dept_attendance_percentages = []
    
    for dept in departments:
        total = department_attendance[dept]['total']
        attended = department_attendance[dept]['attended']
        attendance_percentage = (attended / total) * 100 if total > 0 else 0
        dept_attendance_percentages.append(attendance_percentage)
    
    return departments, dept_attendance_percentages

'''
-------------------------------------------------------
'''

#Feature Usage Insights
def feature_usage_analysis():
    return FeatureToggle.query.all()

#Geolocation Analysis
from geopy.distance import geodesic

def analyze_attendance_by_distance(school_location, max_distance):
    students = Student.query.all()
    attendance_by_distance = {}
    
    for student in students:
        if student.latitude and student.longitude:
            student_location = (student.latitude, student.longitude)
            distance = geodesic(school_location, student_location).km
            
            if distance <= max_distance:
                attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).count()
                present_records = AttendanceRecord.query.filter_by(student_id=student.id, present=True).count()
                attendance_by_distance[student.name] = (present_records / attendance_records) * 100 if attendance_records > 0 else 0
                
    return attendance_by_distance

#Sorting Courses by Attendance
def get_courses_by_attendance(department=None, batch=None, semester=None):
    query = db.session.query(Class, db.func.count(AttendanceRecord.id).label('attendance_count')).join(AttendanceRecord).join(Student)
    
    if department:
        query = query.filter(Student.department == department)
    if batch:
        query = query.filter(Student.batch == batch)
    if semester:
        query = query.filter(Student.semester == semester)
    
    return query.group_by(Class.id).order_by(db.desc('attendance_count')).all()

#Historical Trends
from datetime import datetime

def get_attendance_trend(start_date, end_date, department=None, course=None):
    query = db.session.query(AttendanceRecord.timestamp, db.func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.timestamp.between(start_date, end_date)
    )
    
    if department:
        query = query.join(Student).filter(Student.department == department)
    
    if course:
        query = query.join(Class).filter(Class.name == course)
    
    return query.group_by(db.func.date(AttendanceRecord.timestamp)).all()


# Alerts for Low Attendance
def flag_low_attendance_students(threshold=60):  # threshold as percentage
    students = Student.query.all()
    low_attendance_students = []
    
    for student in students:
        total_records = AttendanceRecord.query.filter_by(student_id=student.id).count()
        present_records = AttendanceRecord.query.filter_by(student_id=student.id, present=True).count()
        attendance_rate = (present_records / total_records) * 100 if total_records > 0 else 0
        
        if attendance_rate < threshold:
            low_attendance_students.append({"student": student, "attendance_rate": attendance_rate})
    
    return low_attendance_students

# Attendance Projections
from sklearn.linear_model import LinearRegression
import numpy as np

def project_attendance(class_id, days_in_future):
    attendance_records = db.session.query(AttendanceRecord.timestamp, AttendanceRecord.present).filter_by(class_id=class_id).all()
    
    if not attendance_records:
        return None  # No data to project
    
    timestamps = np.array([record.timestamp.timestamp() for record in attendance_records]).reshape(-1, 1)
    attendance = np.array([record.present for record in attendance_records])
    
    model = LinearRegression()
    model.fit(timestamps, attendance)
    
    future_timestamp = datetime.now().timestamp() + (days_in_future * 24 * 3600)
    future_prediction = model.predict([[future_timestamp]])
    
    return future_prediction[0]  # Projected attendance rate

#Flagging Low-Attendance Courses
def flag_low_attendance_courses(threshold=70):  # threshold as percentage
    classes = Class.query.all()
    low_attendance_courses = []
    
    for cls in classes:
        total_records = AttendanceRecord.query.filter_by(class_id=cls.id).count()
        present_records = AttendanceRecord.query.filter_by(class_id=cls.id, present=True).count()
        attendance_rate = (present_records / total_records) * 100 if total_records > 0 else 0
        
        if attendance_rate < threshold:
            low_attendance_courses.append({"class": cls, "attendance_rate": attendance_rate})
    
    return low_attendance_courses

'''
-------------------------------------------------------
'''

from datetime import datetime, timedelta

def get_late_comers():
    schedule_entries = ScheduleEntry.query.all()
    late_comers = {}
    
    for entry in schedule_entries:
        # Convert time_start from string to time object
        time_start = datetime.strptime(entry.time_start, "%H:%M").time()
        
        class_attendance = AttendanceRecord.query.filter_by(class_id=entry.id).all()
        for record in class_attendance:
            # Assuming the record.timestamp is a datetime object, compare times
            if record.timestamp.time() > (datetime.combine(record.timestamp.date(), time_start) + timedelta(minutes=10)).time():
                student = Student.query.get(record.student_id)
                if student.name not in late_comers:
                    late_comers[student.name] = 0
                late_comers[student.name] += 1
                
    return late_comers


#Class Attendance Comparison
def compare_class_attendance():
    classes = Class.query.all()
    class_attendance = {}
    for cls in classes:
        total_students = AttendanceRecord.query.filter_by(class_id=cls.id).count()
        present_students = AttendanceRecord.query.filter_by(class_id=cls.id, present=True).count()
        class_attendance[cls.name] = (present_students / total_students) * 100 if total_students > 0 else 0
    return class_attendance


#Teacher Performance Analysis
def teacher_attendance_analysis():
    teachers = Teacher.query.all()
    teacher_performance = {}
    
    for teacher in teachers:
        total_classes = Class.query.filter_by(teacher_id=teacher.id).all()
        total_attendance = 0
        class_count = 0
        
        for cls in total_classes:
            class_count += 1
            total_records = AttendanceRecord.query.filter_by(class_id=cls.id).count()
            present_records = AttendanceRecord.query.filter_by(class_id=cls.id, present=True).count()
            total_attendance += (present_records / total_records) * 100 if total_records > 0 else 0
            
        teacher_performance[teacher.name] = total_attendance / class_count if class_count > 0 else 0
        
    return teacher_performance

# Peak Attendance Times
def peak_attendance_times():
    # Get all schedule entries
    schedule_entries = ScheduleEntry.query.all()
    
    attendance_by_period = {}
    
    for entry in schedule_entries:
        # Create the period key based on day and time
        period = f'{entry.day_of_week} {entry.time_start}-{entry.time_end}'
        
        # Initialize the attendance count for this period if not already present
        if period not in attendance_by_period:
            attendance_by_period[period] = 0
        
        # Query attendance records where conditions match the schedule entry
        total_students = AttendanceRecord.query.join(Class).join(ScheduleEntry, ScheduleEntry.course_name == Class.name).filter(
            ScheduleEntry.teacher_id == entry.teacher_id,
            ScheduleEntry.day_of_week == entry.day_of_week,
            ScheduleEntry.time_start == entry.time_start,
        ).count()
        
        # Update the attendance count for this period
        attendance_by_period[period] += total_students

    # Convert the dictionary to a list of dictionaries or tuples for the template
    peak_times = [{'slot': period, 'count': count} for period, count in attendance_by_period.items()]
    
    return peak_times



# Department-Wise Attendance
def department_wise_attendance():
    departments = Student.query.with_entities(Student.department).distinct().all()
    department_attendance = {}
    
    for dept in departments:
        students = Student.query.filter_by(department=dept[0]).all()
        total_attendance = 0
        total_records = 0
        
        for student in students:
            attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).count()
            present_records = AttendanceRecord.query.filter_by(student_id=student.id, present=True).count()
            total_attendance += present_records
            total_records += attendance_records
            
        department_attendance[dept[0]] = (total_attendance / total_records) * 100 if total_records > 0 else 0
        
    return department_attendance

'''
-------------------------------------------------------
'''

#Batch-wise Attendance Toggle for Each Department
def get_batch_attendance(department):
    query = db.session.query(Student.batch, db.func.count(AttendanceRecord.id).label('attendance_count')).join(AttendanceRecord).filter(
        Student.department == department).group_by(Student.batch).order_by(db.desc('attendance_count')).all()
    return query


# Get Attendance by Student
def get_student_attendance(student_id):
    return AttendanceRecord.query.filter_by(student_id=student_id).all()

#Get Attendance by Class
def get_class_attendance(class_id):
    return AttendanceRecord.query.filter_by(class_id=class_id).all()

#Get Teacher's Class Attendance
def get_teacher_classes_attendance(teacher_id):
    teacher_classes = Class.query.filter_by(teacher_id=teacher_id).all()
    attendance_data = {}
    for cls in teacher_classes:
        attendance_data[cls.name] = AttendanceRecord.query.filter_by(class_id=cls.id).all()
    return attendance_data

#GPS-Based Attendance
from geopy.distance import geodesic

def get_attendance_by_location(student_id, latitude, longitude, max_distance_km):
    student = Student.query.get(student_id)
    student_location = (student.latitude, student.longitude)
    attendance_distance = geodesic((latitude, longitude), student_location).km
    
    if attendance_distance <= max_distance_km:
        return "Present"
    else:
        return "Absent"
    

#Attendance Status Based on Schedule
def is_attendance_allowed(day, period):
    status = AttendanceStatus.query.filter_by(day=day, period=period).first()
    return status and status.status

def get_teacher_attendance_summary(teacher_id, day, period):
    # First, get all the classes taught by the teacher
    classes = Class.query.filter_by(teacher_id=teacher_id).all()
    attendance_summary = {}
    
    for cls in classes:
        # Join AttendanceRecord with Class, and then filter based on ScheduleEntry attributes
        attendance = AttendanceRecord.query.join(Class).join(ScheduleEntry, 
            (ScheduleEntry.teacher_id == teacher_id) & 
            (ScheduleEntry.day_of_week == day) &
            (ScheduleEntry.time_start <= period) & 
            (ScheduleEntry.time_end >= period)
        ).filter(AttendanceRecord.class_id == cls.id).all()
        
        attendance_summary[cls.name] = attendance
        
    return attendance_summary


#Student Attendance Trends
def get_frequent_absentees(threshold=0.7):
    students = Student.query.all()
    absentees = []
    for student in students:
        total_records = AttendanceRecord.query.filter_by(student_id=student.id).count()
        absent_records = AttendanceRecord.query.filter_by(student_id=student.id, present=False).count()
        if total_records > 0 and absent_records / total_records >= threshold:
            absentees.append(student)
    return absentees

#Attendance and Performance Correlation
def correlate_attendance_with_performance(student_id, performance_data):
    attendance_records = AttendanceRecord.query.filter_by(student_id=student_id).count()
    present_records = AttendanceRecord.query.filter_by(student_id=student_id, present=True).count()
    
    attendance_rate = (present_records / attendance_records) * 100 if attendance_records > 0 else 0
    performance = performance_data.get(student_id, None)
    
    return {"attendance_rate": attendance_rate, "performance": performance}

#Student Attendance within a Course
def get_students_by_course_attendance(class_id):
    return db.session.query(Student, db.func.count(AttendanceRecord.id).label('attendance_count')).join(AttendanceRecord).filter(
        AttendanceRecord.class_id == class_id).group_by(Student.id).order_by(db.desc('attendance_count')).all()

#Pie Chart for Department-Wise Attendance
def get_department_attendance():
    query = db.session.query(Student.department, db.func.count(AttendanceRecord.id).label('attendance_count')).join(AttendanceRecord).group_by(Student.department).all()
    return query
