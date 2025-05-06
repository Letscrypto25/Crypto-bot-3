# Use a smaller Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only the requirements first to leverage Docker's caching mechanism
COPY requirements.txt /app/requirements.txt

# Install only the dependencies specified in the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application
COPY . /app

# Expose the port that the app will run on
EXPOSE 8080

# Start the application using Hypercorn
CMD ["hypercorn", "main:app", "--bind", "0.0.0.0:8080"]
