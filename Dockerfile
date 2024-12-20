# Use a Python base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install dependencies
COPY app/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy application files into the /app directory
COPY app /app

# Create volume for config file
VOLUME /config

# Set default environment variables
ENV DEBUG=false

# Expose port for the Flask app
EXPOSE 8080

# Start the application
CMD ["python", "observ3r.py"]
