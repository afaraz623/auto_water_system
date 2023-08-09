FROM python:3.11

ADD main.py .

RUN pip install tabula-py

CMD ["python", "./main.py"]

