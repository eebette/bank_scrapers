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
      "name": "becu"
    }
  ]
}
```

### Set up environment variables

The image uses the environment variables `BW_PASSWORD` to get the authentication credentials for the banks that it
scrapes.

1. Put your password into a local file (i.e. `$HOME/.env`) to pass to the container at runtime:

```sh
echo BW_PASSWORD=<your_bitwarden_password> >> $HOME/.env
```

### Run

You can run the container by using `docker run`:

```sh
docker run --rm --env-file .env -t -v /path/to/config_file:/bank_exporter -v /path/to/mfa/files:/sms --network host ebette1/bank-exporter:latest
```

## Building the image

If you want to build the image locally, the easiest way is to clone the GitHub repo and build from there:

```sh
git clone https://github.com/eebette/BankExporter
```

```sh
docker build ./BankExporter
```