FROM python:3.12

COPY bank_exporter.py /
COPY requirements.txt /

RUN curl -fsSL https://get.docker.com | sh

RUN pip install -r /requirements.txt

RUN apt update && \
    apt install -y xvfb xserver-xephyr tigervnc-standalone-server

RUN patchright install chrome

ENTRYPOINT [ "python", "/bank_exporter.py" ]