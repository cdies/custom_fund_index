FROM python:3.8

RUN python -m pip install pandas numpy tinkoff-investments fastapi gunicorn uvicorn uvloop httptools

WORKDIR /app

ADD tinkoff-microservice.py tinkoff-microservice.py
ADD custom_index.py custom_index.py
ADD token.txt token.txt