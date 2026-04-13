# cronwatcher

A lightweight CLI tool that monitors cron job execution and sends alerts on failure or missed runs.

---

## Installation

```bash
pip install cronwatcher
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatcher.git
cd cronwatcher
pip install .
```

---

## Usage

Register a cron job to be monitored:

```bash
cronwatcher register --name "daily-backup" --schedule "0 2 * * *" --alert email
```

Wrap an existing cron command to track its execution:

```bash
cronwatcher run --name "daily-backup" -- /path/to/backup.sh
```

Check the status of all monitored jobs:

```bash
cronwatcher status
```

View logs for a specific job:

```bash
cronwatcher logs --name "daily-backup" --tail 50
```

Configure alert destinations in `~/.cronwatcher/config.yaml`:

```yaml
alerts:
  email: you@example.com
  slack_webhook: https://hooks.slack.com/services/your/webhook/url
```

---

## Features

- Detects failed runs (non-zero exit codes) and missed schedules
- Supports email and Slack alert integrations
- Minimal overhead — designed to wrap existing cron jobs
- Simple YAML-based configuration

---

## License

This project is licensed under the [MIT License](LICENSE).