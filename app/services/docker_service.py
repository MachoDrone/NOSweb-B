import logging
import docker
from docker.errors import NotFound, APIError
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class DockerService:
    """Docker SDK wrapper for container listing and log streaming."""

    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        self._socket_path = socket_path
        self._connect()

    def _connect(self):
        """Attempt to connect to the Docker daemon."""
        try:
            self.client = docker.DockerClient(
                base_url=f"unix://{self._socket_path}",
                timeout=10,
            )
            # Verify the connection actually works
            self.client.ping()
            self._available = True
        except Exception as e:
            logger.warning("Docker connection failed: %s", e)
            self.client = None
            self._available = False

    def _ensure_connected(self) -> bool:
        """Reconnect if the previous connection dropped."""
        if self._available:
            try:
                self.client.ping()
                return True
            except Exception:
                logger.warning("Docker ping failed, reconnecting...")
                self._available = False

        # Try to reconnect
        self._connect()
        return self._available

    @property
    def available(self) -> bool:
        return self._available

    def list_containers(self, pattern: str = "") -> list[dict]:
        """List all containers, optionally filtering by name pattern."""
        if not self._ensure_connected():
            return []

        try:
            containers = self.client.containers.list(all=True)
        except APIError as e:
            logger.warning("Failed to list containers: %s", e)
            return []

        result = []
        for c in containers:
            if pattern and pattern not in c.name:
                continue
            tags = c.image.tags if c.image.tags else []
            result.append({
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": tags[0] if tags else "unknown",
                "created": str(c.attrs.get("Created", "")),
            })
        return result

    def list_all_containers(self) -> list[dict]:
        """List all containers without filtering."""
        return self.list_containers(pattern="")

    def stream_logs(
        self, container_id: str, tail: int = 200
    ) -> Optional[Generator]:
        """Stream logs from a container. Returns a blocking generator."""
        if not self._ensure_connected():
            return None

        try:
            container = self.client.containers.get(container_id)
            return container.logs(
                stream=True,
                follow=True,
                tail=tail,
                timestamps=True,
            )
        except (NotFound, APIError) as e:
            logger.warning("Failed to stream logs for %s: %s", container_id, e)
            return None

    def close(self):
        if self.client:
            self.client.close()
