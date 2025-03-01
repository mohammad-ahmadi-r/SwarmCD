# Use the official Python image from the Docker Hub
FROM python:3.12-alpine
# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt into the container at /app
COPY requirements.txt .

# Install the dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .
EXPOSE 5000

CMD ["python3", "app.py"]
