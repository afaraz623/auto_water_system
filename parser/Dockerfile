FROM python:3.11-slim

# set the working directory inside the container
WORKDIR /usr/app

COPY main.py ./

RUN apt-get update && apt-get install -y openjdk-17-jre

RUN pip3 install tabula-py pandas Levenshtein colorlog

CMD ["python", "main.py"]
