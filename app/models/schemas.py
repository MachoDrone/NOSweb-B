from pydantic import BaseModel
from typing import Optional


class CPUStats(BaseModel):
    count_physical: Optional[int] = None
    count_logical: int
    percent: float
    freq_mhz: Optional[float] = None


class MemoryStats(BaseModel):
    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


class DiskStats(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class SystemStats(BaseModel):
    hostname: str
    os: str
    uptime_seconds: float
    cpu: CPUStats
    memory: MemoryStats
    disk: DiskStats


class GPUDevice(BaseModel):
    index: int
    name: str
    temperature_c: int
    gpu_utilization_pct: int
    memory_utilization_pct: int
    memory_used_mb: int
    memory_total_mb: int
    memory_free_mb: int
    power_draw_w: float
    power_limit_w: float
    fan_speed_pct: Optional[int] = None


class ContainerInfo(BaseModel):
    id: str
    name: str
    status: str
    image: str
    created: str


class CommandPreset(BaseModel):
    label: str
    command: str
    description: str
    category: str
