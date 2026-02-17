import docker
from docker.errors import NotFound, APIError
from typing import Generator, Optional


class DockerService:
    """Docker SDK wrapper for container listing and log streaming."""

    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        try:
            self.client = docker.DockerClient(
                base_url=f"unix://{socket_path}",
                timeout=10,
            )
            self._available = True
        except docker.errors.DockerException:
            self.client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def list_containers(self, pattern: str = "") -> list[dict]:
        """List all containers, optionally filtering by name pattern."""
        if not self._available:
            return []

        try:
            containers = self.client.containers.list(all=True)
        except APIError:
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
        if not self._available:
            return None

        try:
            container = self.client.containers.get(container_id)
            return container.logs(
                stream=True,
                follow=True,
                tail=tail,
                timestamps=True,
            )
        except (NotFound, APIError):
            return None

    def close(self):
        if self.client:
            self.client.close()
