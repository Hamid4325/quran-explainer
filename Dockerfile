# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]