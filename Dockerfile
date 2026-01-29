# Use the official Python image from the Docker Hub
FROM python:slim-bullseye
#python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY ./app/requirements.txt requirements.txt

RUN pip install --upgrade pip

RUN pip install --upgrade openai

# Install the required dependencies
RUN pip install -q -U --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev curl

# Install Gunicorn 
RUN pip install gunicorn

# Copy the rest of the application code into the container
COPY ./app/  .

#docker run --name  my_flask -d -p 5000:5000 -d --mount type=bind,source=/home/carole/www,target=/app/export my_flask_app


VOLUME /app/export

# Expose the port the app runs on
EXPOSE 5000

#set time zone to utc+1
ENV TZ=CET

# Set the environment variable for Flask
ENV FLASK_APP=app.py
#new_key = Fernet.generate_key()
#print(new_key.decode())

ENV ENCRYPTION_KEY=6fs2snc6Kauavjf3atIKi-DWqfgGvlT9Bz0YmtK0gr0=
# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
# Run Gunicorn to start the app 
#CMD ["gunicorn", "app:app", "-w", "4", "-b", "0.0.0.0:5000"]
