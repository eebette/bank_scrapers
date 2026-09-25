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

## Persistent browser profiles

By default every run launches Chrome on a throwaway profile, so every run logs
in from scratch. Set `BANK_SCRAPERS_PROFILES_DIR` to a directory mounted from
the host and each bank keeps its own Chrome profile there between runs:
session cookies, device-trust tokens and the browser identity survive, and
drivers that support it skip the logon while the previous session is still
valid. Chase supports this today; other drivers keep logging in every run but
still benefit from a remembered device.

```
docker create ... \
  --hostname bank-exporter \
  -v /path/to/profiles:/profiles \
  -e BANK_SCRAPERS_PROFILES_DIR=/profiles \
  -e BANK_SCRAPERS_PROFILE_BANKS=chase \
  ...
```

`BANK_SCRAPERS_PROFILE_BANKS` is an optional comma-separated allow-list of
banks (lower-case, spaces as underscores) that get a persistent profile; leave
it unset to enable every bank. Keep it to drivers whose post-logon flow copes
with a remembered device skipping MFA.

Notes:

- The directory holds live bank sessions. The exporter restricts it to the
  owner (`0700`), keep it out of backups and treat it like the credentials
  file.
- A stable `--hostname` keeps Chrome's profile lock consistent between runs;
  the exporter also clears stale locks and disk caches on every launch.
- Bank logins are session cookies, which Chrome normally drops on restart. The
  exporter sets each profile to "continue where you left off" so they survive,
  and parks the tabs that setting reopens.
- Delete a bank's sub-directory to force a fresh login on the next run. A
  driver that finds its profile in a state it does not recognise does the
  same on its own.

## Building the image

If you want to build the image locally, the easiest way is to clone the GitHub repo and build from there:

```sh
git clone https://github.com/eebette/bank_scrapers
```

```sh
cd bank_scrapers/examples/prometheus_exporter/
docker build ./BankExporter
```