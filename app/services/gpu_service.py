import asyncio
import json
from typing import Optional


class GPUService:
    """GPU monitoring via nvidia-ml-py (pynvml) with nsenter fallback."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._pynvml = None
        self._initialized = False

        if enabled:
            self._try_pynvml_init()

    def _try_pynvml_init(self):
        """Try to initialize pynvml for direct GPU access."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self._pynvml = pynvml
            self._initialized = True
        except Exception:
            # pynvml not available or no GPU; fall back to nsenter nvidia-smi
            self._initialized = False

    @property
    def device_count(self) -> int:
        if not self._initialized or not self._pynvml:
            return 0
        try:
            return self._pynvml.nvmlDeviceGetCount()
        except Exception:
            return 0

    def get_all_gpu_stats(self) -> list[dict]:
        """Return stats for all GPUs via pynvml."""
        if not self._initialized or not self._pynvml:
            return []

        pynvml = self._pynvml
        stats = []

        for i in range(self.device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temperature = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")

                stats.append({
                    "index": i,
                    "name": name,
                    "temperature_c": temperature,
                    "gpu_utilization_pct": utilization.gpu,
                    "memory_utilization_pct": utilization.memory,
                    "memory_used_mb": memory.used // (1024 * 1024),
                    "memory_total_mb": memory.total // (1024 * 1024),
                    "memory_free_mb": memory.free // (1024 * 1024),
                    "power_draw_w": round(power, 1),
                    "power_limit_w": round(power_limit, 1),
                    "fan_speed_pct": self._safe_fan_speed(handle),
                })
            except Exception:
                continue

        return stats

    def _safe_fan_speed(self, handle) -> Optional[int]:
        """Some GPUs don't report fan speed."""
        try:
            return self._pynvml.nvmlDeviceGetFanSpeed(handle)
        except Exception:
            return None

    async def get_stats_via_nsenter(self) -> list[dict]:
        """Fallback: get GPU stats by running nvidia-smi on the host."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "nsenter", "-t", "1", "-m", "-u", "-i", "-n", "-p", "--",
                "nvidia-smi",
                "--query-gpu=index,name,temperature.gpu,utilization.gpu,"
                "utilization.memory,memory.used,memory.total,memory.free,"
                "power.draw,power.limit,fan.speed",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return self._parse_nvidia_smi(stdout.decode())
        except Exception:
            return []

    @staticmethod
    def _parse_nvidia_smi(output: str) -> list[dict]:
        """Parse nvidia-smi CSV output into structured dicts."""
        stats = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 11:
                continue
            try:
                stats.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "temperature_c": int(parts[2]),
                    "gpu_utilization_pct": int(parts[3]),
                    "memory_utilization_pct": int(parts[4]),
                    "memory_used_mb": int(parts[5]),
                    "memory_total_mb": int(parts[6]),
                    "memory_free_mb": int(parts[7]),
                    "power_draw_w": float(parts[8]),
                    "power_limit_w": float(parts[9]),
                    "fan_speed_pct": int(parts[10]) if parts[10] != "[N/A]" else None,
                })
            except (ValueError, IndexError):
                continue
        return stats

    def close(self):
        if self._initialized and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception:
                pass
