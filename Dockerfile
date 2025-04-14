# Use a base Python image
FROM python:3.12-alpine

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . .

# Expose the correct port (matching app.py)
EXPOSE 5678

# Run the application
CMD ["python", "app.py"]
