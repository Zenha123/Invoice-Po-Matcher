# Use Python 3.13 slim image
FROM python:3.13-slim

# Install system dependencies including Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Set environment variable for Django
ENV PYTHONUNBUFFERED=1

# Collect static files
RUN python manage.py collectstatic --noinput

# Apply migrations
RUN python manage.py migrate

# Expose port
EXPOSE 8000

# Run the app using Gunicorn
CMD ["gunicorn", "invoice_project.wsgi:application", "--bind", "0.0.0.0:8000"]
