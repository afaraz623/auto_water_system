FROM python:3.11-slim

WORKDIR /usr/app

COPY logs.py .
COPY requirements.txt .

RUN apt-get update && apt-get install openjdk-17-jre -y && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

RUN rm -rf requirements.txt