"""Self-update service — triggers a host-side script via nsenter that
downloads the latest source tarball, rebuilds the Docker image, and
restarts the container.  The script runs detached (nohup) in the host
PID namespace so it survives the old container being stopped."""

import asyncio

from app.config import settings

NSENTER_PREFIX = ["nsenter", "-t", "1", "-m", "-u", "-i", "-n", "-p", "--"]

UPDATE_SCRIPT_TEMPLATE = r"""
exec 200>/tmp/corelink-update.lock
flock -n 200 || {{ echo '[ERROR] Update already in progress'; exit 1; }}

CONTAINER="{container}"
IMAGE="{image}"
TARBALL="{tarball_url}"
LOG="/tmp/corelink-update.log"

echo "[$(date)] Update started" > "$LOG"

# 1. Download & build (old container still running)
BUILD_DIR=$(mktemp -d)
echo "[$(date)] Downloading source..." >> "$LOG"
wget -qO- "$TARBALL" | tar xz -C "$BUILD_DIR" || {{ echo "[$(date)] Download failed" >> "$LOG"; exit 1; }}

echo "[$(date)] Building image..." >> "$LOG"
docker build --no-cache -q -t "$IMAGE" "$BUILD_DIR/NOSweb-B-main/" >> "$LOG" 2>&1 \
    || {{ echo "[$(date)] Build failed" >> "$LOG"; rm -rf "$BUILD_DIR"; exit 1; }}
rm -rf "$BUILD_DIR"

# 2. Capture current container config
PORT=$(docker inspect -f '{{{{(index (index .NetworkSettings.Ports "8585/tcp") 0).HostPort}}}}' "$CONTAINER" 2>/dev/null || echo "8585")
GPU_FLAG=$(docker inspect -f '{{{{range .HostConfig.DeviceRequests}}}}--gpus all{{{{end}}}}' "$CONTAINER" 2>/dev/null || echo "")
HAS_GPU=$(docker inspect -f '{{{{range .Config.Env}}}}{{{{println .}}}}{{{{end}}}}' "$CONTAINER" 2>/dev/null | grep NOSWEB_HAS_GPU | cut -d= -f2 || echo "false")

# 3. Stop old, start new
echo "[$(date)] Restarting container..." >> "$LOG"
docker stop "$CONTAINER" 2>/dev/null || true
docker rm "$CONTAINER" 2>/dev/null || true

docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    --pid=host \
    -p "0.0.0.0:${{PORT:-8585}}:8585" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /etc/hostname:/etc/host_hostname:ro \
    $GPU_FLAG \
    -e "NOSWEB_HAS_GPU=${{HAS_GPU:-false}}" \
    -e "NOSWEB_NOSANA_CONTAINER_PATTERN=nosana" \
    "$IMAGE" >> "$LOG" 2>&1

echo "[$(date)] Update complete" >> "$LOG"
"""


async def trigger_update() -> dict:
    """Launch the self-update script on the host (detached)."""
    script = UPDATE_SCRIPT_TEMPLATE.format(
        container=settings.CONTAINER_NAME,
        image=f"{settings.CONTAINER_NAME}:latest",
        tarball_url=settings.REPO_TARBALL_URL,
    )

    cmd = NSENTER_PREFIX + [
        "bash", "-c",
        f"nohup bash -c '{script}' </dev/null >/dev/null 2>&1 &",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(process.wait(), timeout=5)
        return {"status": "started", "message": "Update launched on host"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_update_status() -> dict:
    """Read the update log from the host."""
    cmd = NSENTER_PREFIX + [
        "bash", "-c",
        "cat /tmp/corelink-update.log 2>/dev/null || echo 'No update log found'",
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        log = stdout.decode("utf-8", errors="replace").strip()
        done = "Update complete" in log
        failed = "failed" in log.lower()
        status = "complete" if done else ("failed" if failed else "updating")
        return {"status": status, "log": log}
    except Exception as e:
        return {"status": "unknown", "log": str(e)}
