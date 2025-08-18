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