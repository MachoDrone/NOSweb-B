# Nosana Host Dashboard

A lightweight, modular web dashboard for Nosana GPU host operators. Runs as a single Docker container -- zero packages installed on your host OS.

## Features

- **System Overview** -- CPU, RAM, disk usage with live auto-refresh
- **Docker Logs** -- Live streaming container logs via WebSocket
- **GPU Monitoring** -- Real-time NVIDIA GPU temp, utilization, VRAM, power stats
- **Command Center** -- Pre-written command buttons + custom CLI execution on the host
- **Dark/Light Mode** -- Toggle between themes
- **LAN Accessible** -- Monitor from any device on your local network
- **Modular Architecture** -- Easy to add new tabs and features

## Quick Start

```bash
bash <(wget -qO- https://raw.githubusercontent.com/MachoDrone/NOSweb-B/main/install.sh)
```

Then open `http://localhost:8585` in your browser.

## Requirements

- Docker (installed and running)
- Ubuntu 20.04 - 24.04 (Desktop, Server, Minimal, or Core)
- NVIDIA GPU + Container Toolkit (optional, for GPU monitoring)

## Configuration

Environment variables (set with `-e` when running the container):

| Variable | Default | Description |
|----------|---------|-------------|
| `NOSWEB_PORT` | `8585` | Dashboard port |
| `NOSWEB_HAS_GPU` | `false` | Enable GPU monitoring |
| `NOSWEB_ALLOW_CUSTOM_COMMANDS` | `true` | Allow custom CLI commands |
| `NOSWEB_COMMAND_TIMEOUT` | `30` | Command timeout in seconds |
| `NOSWEB_NOSANA_CONTAINER_PATTERN` | `nosana` | Filter pattern for container list |

## Architecture

```
Python + FastAPI (backend)  +  Alpine.js (frontend)
         |                           |
    nsenter --pid=host          WebSocket real-time
         |                           |
    Host OS commands            Live log streaming
```

All CLI commands execute on the **host OS** via `nsenter` (container runs with `--pid=host`). No packages installed on the host.

## Project Structure

```
app/
├── main.py              # FastAPI app factory
├── config.py            # Settings via env vars
├── routers/             # API endpoints (1 file per tab)
├── services/            # System interaction layer
├── models/              # Pydantic schemas
├── templates/           # Jinja2 HTML (base + pages + partials)
└── static/              # CSS + JS (Alpine.js components)
```

**Adding a new tab:** Create 1 router + 1 page template + 1 line in `main.py` + 1 nav button.

## Manual Docker Run

```bash
docker run -d \
  --name nosana-dashboard \
  --restart unless-stopped \
  --pid=host \
  -p 0.0.0.0:8585:8585 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /etc/hostname:/etc/host_hostname:ro \
  --gpus all \
  -e NOSWEB_HAS_GPU=true \
  ghcr.io/machodrone/nosweb:latest
```

## Updating

Re-run the install command. It stops the old container, pulls the latest image, and launches fresh:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/MachoDrone/NOSweb-B/main/install.sh)
```

## License

MIT
