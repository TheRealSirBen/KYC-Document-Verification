from os import makedirs

from database import initialize_database

# Prepare folders
IMAGE_FOLDER = 'images'
PDF_FOLDER = 'pdfs'
PREDICTIONS_FOLDER = 'predictions'

# Standard Image configuration
IMAGE_SIZE, PDF_SIZE = 400, 1000
IMAGE_MAX_SIZE = (IMAGE_SIZE, IMAGE_SIZE)
PDF_MAX_SIZE = (PDF_SIZE, PDF_SIZE)

# Create image folders
makedirs(PDF_FOLDER, exist_ok=True)
makedirs(IMAGE_FOLDER, exist_ok=True)
makedirs(PREDICTIONS_FOLDER, exist_ok=True)

# initialise database
initialize_database()

PAGE_HELP = """
This is the Application form page, where you are required to provide the requested information.
"""
