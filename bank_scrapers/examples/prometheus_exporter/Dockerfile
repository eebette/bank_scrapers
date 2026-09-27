FROM python:3.12

COPY bank_exporter.py /
COPY requirements.txt /

RUN curl -fsSL https://get.docker.com | sh && docker --version

RUN pip install -r /requirements.txt

RUN apt update && \
    apt install -y xvfb xserver-xephyr tigervnc-standalone-server \
        libgtk-3-0 libdbus-glib-1-2 libx11-xcb1 libasound2 libxtst6

RUN patchright install chrome
RUN camoufox fetch

# RoundPoint's portal serves GoDaddy's new R1 chain without the R1->G2 cross-certificate,
# and R1 isn't in the Chrome Root Store yet. Give Chrome the cross-cert as a path-building
# hint (not a trust anchor) so the chain validates to the already-trusted G2 root.
# See README.md "Chrome CA hint certificates" for when to remove this.
COPY certs/gd_tls_root-r1-cross-g2.pem /tmp/
RUN mkdir -p /etc/opt/chrome/policies/managed && \
    printf '{"CAHintCertificates": ["%s"]}\n' \
        "$(openssl x509 -in /tmp/gd_tls_root-r1-cross-g2.pem -outform DER | base64 -w0)" \
        > /etc/opt/chrome/policies/managed/ca_hint_certificates.json && \
    rm /tmp/gd_tls_root-r1-cross-g2.pem

ENTRYPOINT [ "python", "/bank_exporter.py" ]