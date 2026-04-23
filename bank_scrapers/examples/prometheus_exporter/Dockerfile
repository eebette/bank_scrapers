FROM python:3.12

COPY bank_exporter.py /
COPY requirements.txt /

RUN curl -fsSL https://get.docker.com | sh

RUN pip install -r /requirements.txt

RUN apt update && \
    apt install -y xvfb xserver-xephyr tigervnc-standalone-server \
        libgtk-3-0 libdbus-glib-1-2 libx11-xcb1 libasound2 libxtst6

RUN patchright install chrome
RUN camoufox fetch

ENTRYPOINT [ "python", "/bank_exporter.py" ]