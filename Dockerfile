# Use an official Python runtime as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Install GDAL
RUN apt-get update && apt-get install -y libgdal-dev

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements file to the container
COPY requirements.txt .

# Install the project dependencies
RUN pip install -r requirements.txt

# Copy the Django project code to the container
COPY . .

# Run migrations
# RUN python manage.py makemigrations
# RUN python manage.py migrate

# Expose the port on which the Django development server will run
EXPOSE 8000

# Define the command to run when the container starts
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
