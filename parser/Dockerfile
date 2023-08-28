FROM python:3.11-slim

# set the working directory inside the container
WORKDIR /usr/app

COPY main.py ./
COPY requirements.txt ./

RUN apt-get update && apt-get install -y openjdk-17-jre

RUN pip3 install -r requirements.txt

CMD ["python", "main.py"]
