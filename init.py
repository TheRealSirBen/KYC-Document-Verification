from os import makedirs
from os import environ
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

# Create a base class for declarative models
Base = declarative_base()


def get_sql_alchemy_url():
    return environ.get("SQLALCHEMY_DATABASE_URI")


def create_connection():
    sql_alchemy_url = get_sql_alchemy_url()
    return create_engine(sql_alchemy_url)


def initialize_database():
    # Create the SQLAlchemy engine
    engine = create_engine(get_sql_alchemy_url())

    # create a connection object
    conn = engine.connect()

    # Create tables
    Base.metadata.create_all(bind=engine)

    # close the connection
    conn.close()


# Prepare folders
IMAGE_FOLDER = 'images'
PDF_FOLDER = 'pdfs'
PREDICTIONS_FOLDER = 'predictions'

# Standard Image configuration
IMAGE_SIZE, PDF_SIZE = int(environ.get('IMAGE_SIZE')), int(environ.get('PDF_SIZE'))
IMAGE_MAX_SIZE = (IMAGE_SIZE, IMAGE_SIZE)
PDF_MAX_SIZE = (PDF_SIZE, PDF_SIZE)

# Create image folders
makedirs(PDF_FOLDER, exist_ok=True)
makedirs(IMAGE_FOLDER, exist_ok=True)
makedirs(PREDICTIONS_FOLDER, exist_ok=True)

PAGE_HELP = """
This is the Application form page, where you are required to provide the requested information.
"""

HELLO_PAGE = """
        ### Student Details
    
        - Name: Benedict T. Dlamini
        - Student Number: C22148273B
        - Programme: MSC. Big Data Analytics
    
        ### Topic
        A Deep Learning Approach to KYC Document Verification for the Customer 
        Registration in Zimbabwean Financial Institutions: Case of Old Mutual Zimbabwe
    """
