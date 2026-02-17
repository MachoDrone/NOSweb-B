from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8585
    DEBUG: bool = False

    # Docker
    DOCKER_SOCKET: str = "/var/run/docker.sock"
    NOSANA_CONTAINER_PATTERN: str = "nosana"

    # GPU
    HAS_GPU: bool = False

    # Command safety
    ALLOWED_COMMAND_PREFIXES: list[str] = [
        "npx @nosana/cli",
        "nosana",
        "nvidia-smi",
        "docker ps",
        "docker logs",
        "docker stats",
        "docker inspect",
        "uptime",
        "df -h",
        "free -h",
        "top -bn1",
        "lscpu",
        "lsblk",
        "ip addr",
        "hostname",
        "cat /etc/os-release",
        "uname -a",
    ]
    ALLOW_CUSTOM_COMMANDS: bool = True
    COMMAND_TIMEOUT: int = 30

    model_config = {"env_prefix": "NOSWEB_"}


settings = Settings()
