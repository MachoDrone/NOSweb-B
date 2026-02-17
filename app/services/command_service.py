import asyncio
from typing import AsyncGenerator


# Pre-defined command catalog for the button UI
PRESET_COMMANDS = {
    "node_status": {
        "label": "Node Status",
        "command": "npx @nosana/cli@latest node view",
        "description": "Display current Nosana node information",
        "category": "nosana",
    },
    "nosana_version": {
        "label": "Nosana Version",
        "command": "npx @nosana/cli@latest --version",
        "description": "Show Nosana CLI version",
        "category": "nosana",
    },
    "gpu_info": {
        "label": "GPU Info",
        "command": "nvidia-smi",
        "description": "Full NVIDIA GPU diagnostic output",
        "category": "gpu",
    },
    "gpu_processes": {
        "label": "GPU Processes",
        "command": "nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv",
        "description": "Show processes using GPU memory",
        "category": "gpu",
    },
    "disk_usage": {
        "label": "Disk Usage",
        "command": "df -h",
        "description": "Show disk space usage",
        "category": "system",
    },
    "memory_usage": {
        "label": "Memory Usage",
        "command": "free -h",
        "description": "Show RAM usage",
        "category": "system",
    },
    "docker_ps": {
        "label": "Docker Containers",
        "command": "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'",
        "description": "List running Docker containers",
        "category": "docker",
    },
    "system_uptime": {
        "label": "System Uptime",
        "command": "uptime",
        "description": "Show system uptime and load averages",
        "category": "system",
    },
    "os_info": {
        "label": "OS Info",
        "command": "cat /etc/os-release",
        "description": "Show operating system details",
        "category": "system",
    },
    "network_info": {
        "label": "Network Info",
        "command": "ip addr show",
        "description": "Show network interface configuration",
        "category": "system",
    },
}

# Dangerous patterns to always block
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    "> /dev/",
    "chmod 777 /",
    ":(){ :|:&",
    "shutdown",
    "reboot",
    "poweroff",
    "init 0",
    "init 6",
    "halt",
    "kill -9 1",
    "killall",
    "pkill -9",
    "curl | sh",
    "wget | sh",
    "curl | bash",
    "wget | bash",
]


class CommandService:
    """Execute commands on the host via nsenter with safety checks."""

    NSENTER_PREFIX = ["nsenter", "-t", "1", "-m", "-u", "-i", "-n", "-p", "--"]

    def __init__(
        self,
        allowed_prefixes: list[str],
        allow_custom: bool = True,
        timeout: int = 30,
    ):
        self.allowed_prefixes = allowed_prefixes
        self.allow_custom = allow_custom
        self.timeout = timeout

    def validate_command(self, command: str) -> tuple[bool, str]:
        """Check if a command is allowed. Returns (allowed, reason)."""
        cmd = command.strip()

        if not cmd:
            return False, "Empty command"

        # Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd:
                return False, f"Command contains blocked pattern: {pattern}"

        # Check against allowed prefixes
        for prefix in self.allowed_prefixes:
            if cmd.startswith(prefix):
                return True, "Matches allowed prefix"

        # If custom commands are allowed, permit it
        if self.allow_custom:
            return True, "Custom commands enabled"

        return False, "Command does not match any allowed prefix"

    async def run_command(self, command: str) -> AsyncGenerator[str, None]:
        """Run a command on the host via nsenter, yielding output lines."""
        allowed, reason = self.validate_command(command)
        if not allowed:
            yield f"[BLOCKED] {reason}\n"
            return

        full_cmd = self.NSENTER_PREFIX + ["bash", "-c", command]

        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            while True:
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=self.timeout,
                    )
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace")
                except asyncio.TimeoutError:
                    yield "\n[TIMEOUT] Command exceeded time limit.\n"
                    process.kill()
                    return

            await process.wait()
            yield f"\n[Exit code: {process.returncode}]\n"

        except FileNotFoundError:
            yield "[ERROR] nsenter not found. Is the container running with --pid=host?\n"
        except Exception as e:
            yield f"[ERROR] {str(e)}\n"
