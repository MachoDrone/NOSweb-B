import asyncio
import platform
from datetime import datetime

import psutil


class SystemService:
    """Reads system stats from the host."""

    # nsenter prefix to execute in host namespace
    NSENTER = ["nsenter", "-t", "1", "-m", "-u", "-i", "-n", "-p", "--"]

    @staticmethod
    def get_system_stats() -> dict:
        """Get CPU, RAM, disk, and uptime stats.

        When running inside Docker with --pid=host, psutil reads
        /proc from the host PID namespace, giving host-level stats.
        """
        cpu_freq = psutil.cpu_freq()
        virtual_mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        return {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "uptime_seconds": (datetime.now() - boot_time).total_seconds(),
            "cpu": {
                "count_physical": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
                "percent": psutil.cpu_percent(interval=None),
                "freq_mhz": round(cpu_freq.current) if cpu_freq else None,
            },
            "memory": {
                "total_gb": round(virtual_mem.total / (1024**3), 1),
                "used_gb": round(virtual_mem.used / (1024**3), 1),
                "available_gb": round(virtual_mem.available / (1024**3), 1),
                "percent": virtual_mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": disk.percent,
            },
        }

    @staticmethod
    async def get_hostname_from_host() -> str:
        """Read the real hostname from mounted /etc/host_hostname."""
        try:
            with open("/etc/host_hostname", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return platform.node()
