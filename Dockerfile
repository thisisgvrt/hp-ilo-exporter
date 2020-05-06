FROM python:3.7-slim

COPY requirements.txt /

RUN apt update && apt install -y gcc && pip install -r /requirements.txt

COPY Server.py /Server.py
COPY logging-config.yaml /logging-config.yaml
WORKDIR /

ENTRYPOINT ["python", "Server.py"]