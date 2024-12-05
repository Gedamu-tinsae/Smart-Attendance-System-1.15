# Smart Attendance System Setup Guide

This guide provides detailed instructions to set up, configure, and run the Smart Attendance System project on your local machine.

## Prerequisites

Ensure you have Python installed and a virtual environment set up. This project uses Flask, SQLAlchemy, OpenCV, and other dependencies listed in the `requirements.txt` file.

## Project Overview

### Functionalities:
- **Student Side:**
  1. Users sign up and train a face recognition model unique to their face and ID.
  2. Students give live attendance using their trained models.
  
- **Teacher Side:**
  1. Users sign up and manage class schedules.
  2. Teachers enable attendance tracking for each class.
  
- **Shared:**
  - Attendance data is created for each course, teacher, and day.
  - Students view attendance percentages for their courses.
  - Teachers monitor students' attendance percentages.

### Key Models and Relationships:
- **User:** Can be a student or a teacher.
  - One-to-One: Student, Teacher profiles.
  - One-to-Many: Schedule entries.
- **Student:** Associated with a `User`. Tracks attendance records.
- **Teacher:** Associated with a `User`. Manages classes and schedules.
- **Class:** Managed by a teacher; tracks attendance.
- **AttendanceRecord:** Links students, classes, and attendance data.

## Facial Recognition Process

The face recognition system for students in the Smart Attendance System utilizes **MobileNetV2**, a pre-trained deep learning model optimized for mobile and embedded vision applications. It improves the accuracy and efficiency of the system while reducing computational overhead.

### 1. **Feature Extraction:**
   - MobileNetV2 is used to extract a compact feature vector for each student's image. This vector captures essential characteristics of the face.
   
### 2. **Training:**
   - During the training phase, the feature vectors from the student's images are saved. These vectors represent the "known" faces of the student.

### 3. **Recognition:**
   - When a new image is provided for recognition, it is preprocessed and passed through the MobileNetV2 model to extract its feature vector.
   - The new feature vector is compared with the stored feature vectors using **cosine similarity**. If the similarity exceeds a threshold (e.g., 0.8), the system recognizes the face as belonging to the student.

### Why **MobileNetV2**?
- **Efficiency:** MobileNetV2 is optimized for mobile and embedded vision applications, offering high accuracy with low computational cost. It is more efficient compared to LBPH and pre-trained CNNs like SqueezeNet or AlexNet.
- **Feature Extraction:** Unlike traditional methods like Haar-Cascade or LBPH, MobileNetV2 provides more detailed and robust feature extraction, improving recognition accuracy even with varied lighting and student poses.
- **Scalability:** MobileNetV2 can handle larger and more complex datasets effectively, making it suitable for real-world scenarios where scalability is crucial.
- **Real-Time Performance:** The model’s efficiency allows for faster real-time face recognition, enhancing the system's responsiveness compared to models with higher computational demands.
- **Versatility:** Pre-trained on a vast dataset like ImageNet, MobileNetV2 is adaptable to various environments and conditions, unlike models limited by smaller or less diverse training sets.
- **Integration:** MobileNetV2 integrates well with modern deep learning frameworks and tools, facilitating easier implementation and maintenance in diverse systems.

### Summary:
Utilizing advanced facial recognition technology, the system delivers precise and efficient attendance tracking, drastically cutting down the time and effort involved in manual processes. It offers a user-friendly interface that enhances user experience while ensuring data security and integrity.

### Impact:
- The adoption of this system reduces human error and fosters greater accountability and transparency in attendance monitoring.
- Automating the attendance process allows organizations to focus on core activities, enhancing productivity and better resource management.

### Future Scope:
- **Analytics:** Future upgrades might include analytics for real-time attendance tracking, reporting, absence notifications, and performance metrics.
- **Scalability:** Scaling the system to meet diverse organizational needs.
- **Integration:** Integration with other management platforms to further increase its effectiveness across various sectors.
- **Mobile App Integration:** Building a mobile app to enable students to check in their attendance directly from their devices, improving access and convenience.
- **AI Insights:** Introducing predictive AI to anticipate student absence trends and provide insights for data-driven decisions to improve engagement.

---

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd smart_attendance_system
```

### 2. Set Up the Virtual Environment
```bash
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Database Setup
Initialize and migrate the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Handle Face Recognition Setup (Windows Specific)
If you encounter CMake errors for `face_recognition`, follow these steps:
1. Install the Desktop Development Tool from Visual Studio, including SDK and CMake tools.
2. Add Visual Studio's CMake path to your system environment variables:
   ```plaintext
   C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin
   ```
3. Ensure this path is listed above the Python path in system variables.

### 6. Run the Application
Execute the main file:
```bash
python run.py
```
Access the app in your browser at:
```
http://127.0.0.1:5000
```

## Running Multiple Instances
To run two instances of the Flask app on different ports:

1. **Update Your Run Command:**
   Ensure your `run.py` looks like this:
   ```python
   from app import create_app
   import sys

   app = create_app()

   if __name__ == '__main__':
       port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
       app.run(debug=True, port=port)
   ```

2. **Run the First Instance:**
   ```bash
   python run.py 5000
   ```

3. **Run the Second Instance:**
   ```bash
   python run.py 5001
   ```

4. **Access Both Instances:**
   - First instance: `http://127.0.0.1:5000/`
   - Second instance: `http://127.0.0.1:5001/`

## Setting Up School Location Coordinates and Radius

### 1. **Get School Coordinates**
   - **Using Google Maps:**
     1. Open [Google Maps](https://maps.google.com).
     2. Find your school and right-click on its location.
     3. Select "What's here?" to get the coordinates.
     4. Copy the latitude and longitude.

### 2. **Set Radius**
   - Choose a radius based on your campus size:
     - **Small Campus:** 50-100 meters
     - **Large Campus:** 200-500 meters

### 3. **Update Configuration**
Add the coordinates and radius to `config.py`:
```python
# instance/config.py
class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # Max file size (32MB)

    # School's coordinates and allowed radius
    SCHOOL_LATITUDE = 37.7749
    SCHOOL_LONGITUDE = -122.4194
    ALLOWED_RADIUS = 100
```

## Project Structure
```plaintext
smart_attendance_system/
│
├── app/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   ├── attendance.html
│   │   ├── ...
│   ├── __init__.py
│   ├── routes.py
│   ├── models.py
│   ├── forms.py
│   └── facial_recognition.py
├── instance/
│   └── config.py
├── migrations/
├── .env
├── requirements.txt
├── run.py
└── README.md
```

---

Now you're ready to explore the Smart Attendance System! 🚀
