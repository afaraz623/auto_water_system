FROM python:3.11-slim

# set the working directory inside the container
WORKDIR /usr/app

COPY main.py ./
COPY secrets.json ./

RUN apt-get update

RUN pip3 install tabula-py pandas discord.py tabulate

CMD ["python", "main.py"]
