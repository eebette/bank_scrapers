FROM python:latest

COPY bank_exporter.py /
COPY requirements.txt /

RUN apt update && apt install -y wget && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' && \
    apt update && \
    apt install -y google-chrome-stable

RUN apt update && \
    apt install -y xvfb xserver-xephyr tigervnc-standalone-server

RUN pip install -r /requirements.txt
RUN find /usr/local/lib -path "*/undetected_playwright/driver" -exec chmod +x -R {} \;

ENTRYPOINT [ "python", "/bank_exporter.py" ]