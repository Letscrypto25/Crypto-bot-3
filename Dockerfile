# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install pip dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional; Fly.io doesn't require this, but good practice)
EXPOSE 8080

# Run the app
CMD ["python", "main.py"]
