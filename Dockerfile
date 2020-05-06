FROM python:3.7-slim

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY Server.py /Server.py
COPY logging-config.yaml /logging-config.yaml
WORKDIR /

ENTRYPOINT ["python", "Server.py"]