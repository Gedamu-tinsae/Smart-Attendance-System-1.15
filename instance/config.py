
class Config:

    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'app/static/uploads'  # Directory where uploaded files will be saved
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # Max file size (16MB)
    
    # Google OAuth Credentials
    GOOGLE_CLIENT_ID = ''
    GOOGLE_CLIENT_SECRET = ''
    GOOGLE_REDIRECT_URI = "http://127.0.0.1:5000/google_callback"


    #  https://www.gps-coordinates.net/my-location
    

    #list of possible location since browser keeps changing
    SCHOOL_LOCATIONS = [
        (22.552786, 72.924109),  # Bvm
        (22.553529, 72.923447),  #bvm 2
        #...

    ]

    ALLOWED_RADIUS = 100  #in meters

