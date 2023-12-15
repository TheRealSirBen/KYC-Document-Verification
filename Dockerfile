# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Delete records from tables
RUN sqlite3 app_database.db "DELETE FROM application_form; DELETE FROM uploaded_document;"

# Create Virtual Environment
RUN python -m venv venv

# Activate Virtual Environment
RUN /bin/bash -c "source venv/bin/activate"

# Upgrade pip and install required Python packages
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "1_👋🏾_Hello.py", "--server.port=8501", "--server.address=0.0.0.0"]