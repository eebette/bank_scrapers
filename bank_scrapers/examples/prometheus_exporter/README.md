# BankExporter

## Overview

This is a Python script for a Docker image to generate a metrics collector for financial metrics for use with
Prometheus. This enables us to create a Prometheus/Grafana personal finance dashboard.

This project utilizes the scrapers in the package [`bank_scrapers`](https://github.com/eebette/bank_scrapers).

## Usage

### Set up `banks.json`

This script/container uses a configuration called `banks.json`

#### Example

```json
{
  "banks": [
    {
      "name": "becu",
      "id": "password_manager_object_id"
    }
  ]
}
```

### Run

You can run the container by using `docker run`:

```sh
docker run --rm --env-file .env -t -v /path/to/config_file:/bank_exporter -v /path/to/mfa/files:/sms --network host ebette1/bank-exporter:latest
```

## Building the image

If you want to build the image locally, the easiest way is to clone the GitHub repo and build from there:

```sh
git clone https://github.com/eebette/bank_scrapers
```

```sh
cd bank_scrapers/examples/prometheus_exporter/
docker build ./BankExporter
```

## Chrome CA hint certificates

RoundPoint's portal (`ccmportal.youarehome.com`) serves a chain that ends at GoDaddy's new `GoDaddy TLS Root CA - R1`,
which isn't in the Chrome Root Store yet, and leaves out the cross-certificate that links R1 to the trusted
`Go Daddy Root Certificate Authority - G2`. Without it, Chrome fails the login page with
`net::ERR_CERT_AUTHORITY_INVALID`.

The image hands Google Chrome that cross-certificate through the `CAHintCertificates` enterprise policy
(`/etc/opt/chrome/policies/managed/ca_hint_certificates.json`). Hint certificates are only used for path building and are
not trust anchors, so the chain still has to end at a root Chrome already trusts (G2). Sites that don't need the hint are
unaffected.

- File: `certs/gd_tls_root-r1-cross-g2.pem`, from `http://certificates.godaddy.com/repository/gd_tls_root-r1-cross-g2.crt`
- Subject `GoDaddy TLS Root CA - R1`, issuer `Go Daddy Root Certificate Authority - G2`, valid 2025-09-24 to 2037-12-31
- SHA-256 `7B:CB:0F:2F:2D:10:31:A6:AF:8D:61:BA:A8:35:D2:83:5A:3B:8B:CC:26:D9:4A:3B:04:8B:16:55:FB:81:29:8C`

Remove the cert and its Dockerfile step once either of these checks passes:

- Chrome trusts R1: the grep below prints a line. It checks Chromium main, so wait for a Chrome stable release after that
  (about 1–2 months) and rebuild the image, which installs Chrome at build time, before dropping the hint.
  ```sh
  curl -fsS 'https://chromium.googlesource.com/chromium/src/+/main/net/data/ssl/chrome_root_store/root_store.md?format=TEXT' \
    | base64 -d | grep 25cf3da8e9b97addbf92543c2b82527c8a4e2cff2062a6483040d4b64ace719f
  ```
- The portal serves the full chain: the output below lists a cert with subject `GoDaddy TLS Root CA - R1` and issuer
  `Go Daddy Root Certificate Authority - G2`.
  ```sh
  openssl s_client -connect ccmportal.youarehome.com:443 -servername ccmportal.youarehome.com -showcerts </dev/null
  ```

G2 is due to leave the Chrome Root Store on 2027-04-15 (15-year term limit) unless Chrome extends it. If neither check
passes by then, the hint stops helping and this needs another look.