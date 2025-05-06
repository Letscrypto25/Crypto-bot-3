# Use a minimal Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to cache dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the app port
EXPOSE 8080

# Run your bot server
CMD ["python", "main.py"]
