#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Nosana CoreLink - Bootstrap Installer
# Launched via: bash <(wget -qO- https://raw.githubusercontent.com/MachoDrone/NOSweb-B/main/install.sh)
# ============================================================

DASHBOARD_IMAGE="nosana-corelink:latest"
CONTAINER_NAME="nosana-corelink"
DASHBOARD_PORT="${NOSWEB_PORT:-8585}"
DOCKER_SOCKET="/var/run/docker.sock"
REPO_TARBALL="https://github.com/MachoDrone/NOSweb-B/archive/refs/heads/main.tar.gz"
HAS_GPU=false

# ============================================================
# Colors
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
ok()    { echo -e "${GREEN}[  OK]${NC} $*"; }

# ============================================================
# Prerequisite Checks
# ============================================================
check_docker() {
    command -v docker >/dev/null 2>&1 || error "Docker is not installed. Please install Docker first."
    docker info >/dev/null 2>&1 || error "Docker daemon is not running or current user lacks permission. Try: sudo usermod -aG docker \$USER"
    ok "Docker is available"
}

check_nvidia() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        if nvidia-smi >/dev/null 2>&1; then
            ok "NVIDIA drivers detected"
            # Check if nvidia container toolkit is available
            if docker info 2>/dev/null | grep -qi "nvidia"; then
                ok "NVIDIA Container Toolkit detected"
                HAS_GPU=true
            else
                # Try running a quick GPU container test
                if docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
                    ok "NVIDIA Container Toolkit is functional"
                    HAS_GPU=true
                else
                    warn "NVIDIA Container Toolkit not configured. GPU tab will be disabled."
                    warn "Install with: sudo apt install nvidia-container-toolkit"
                fi
            fi
        else
            warn "nvidia-smi found but not responding. GPU tab will be disabled."
        fi
    else
        info "No NVIDIA GPU detected. GPU monitoring tab will be disabled."
    fi
}

check_port() {
    if command -v ss >/dev/null 2>&1; then
        if ss -tlnp 2>/dev/null | grep -q ":${DASHBOARD_PORT} "; then
            warn "Port ${DASHBOARD_PORT} is already in use"
            DASHBOARD_PORT=$((DASHBOARD_PORT + 1))
            info "Using port ${DASHBOARD_PORT} instead"
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tlnp 2>/dev/null | grep -q ":${DASHBOARD_PORT} "; then
            warn "Port ${DASHBOARD_PORT} is already in use"
            DASHBOARD_PORT=$((DASHBOARD_PORT + 1))
            info "Using port ${DASHBOARD_PORT} instead"
        fi
    fi
}

# ============================================================
# Container Management
# ============================================================
stop_existing() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        info "Stopping existing dashboard container..."
        docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
        docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true
        ok "Old container removed"
    fi
}

build_dashboard() {
    local BUILD_DIR
    BUILD_DIR=$(mktemp -d)

    info "Downloading dashboard source..."
    wget -qO- "${REPO_TARBALL}" | tar xz -C "${BUILD_DIR}" \
        || error "Failed to download source from GitHub"

    info "Building dashboard image (first run ~30s, updates ~10s)..."
    docker build -q -t "${DASHBOARD_IMAGE}" "${BUILD_DIR}/NOSweb-B-main/" \
        || error "Docker build failed"

    rm -rf "${BUILD_DIR}"
    ok "Dashboard image built"
}

launch_dashboard() {
    build_dashboard

    local GPU_FLAGS=""
    if [ "${HAS_GPU}" = true ]; then
        GPU_FLAGS="--gpus all"
    fi

    info "Launching Nosana CoreLink..."
    # --privileged is required for nsenter to enter host namespaces
    # (mount, UTS, IPC, net, PID) which enables the Command Center
    # and host-level monitoring. --pid=host alone is not sufficient.
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        --pid=host \
        --privileged \
        -p "0.0.0.0:${DASHBOARD_PORT}:8585" \
        -v "${DOCKER_SOCKET}:/var/run/docker.sock" \
        -v /etc/hostname:/etc/host_hostname:ro \
        ${GPU_FLAGS} \
        -e "NOSWEB_HAS_GPU=${HAS_GPU}" \
        -e "NOSWEB_NOSANA_CONTAINER_PATTERN=nosana" \
        "${DASHBOARD_IMAGE}" >/dev/null

    ok "Dashboard container started"
}

# ============================================================
# Main
# ============================================================
main() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Nosana CoreLink Installer           ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════╝${NC}"
    echo ""

    check_docker
    check_nvidia
    check_port
    stop_existing
    launch_dashboard

    # Get the host's IP for LAN access info
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Dashboard is running!               ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} Local:  http://localhost:${DASHBOARD_PORT}         ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} LAN:    http://${LOCAL_IP}:${DASHBOARD_PORT}  ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} GPU:    ${HAS_GPU}                          ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Stop:   docker stop ${CONTAINER_NAME}  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Logs:   docker logs ${CONTAINER_NAME}  ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""
}

main "$@"

# ============================================
# SANITY CANARY — DO NOT REMOVE OR MODIFY
# If Claude cannot see this, context is degraded
# ============================================
sanity_canary_v1() {
    # This function intentionally does nothing.
    # Claude should report this function name, version,
    # and line number at the end of every reply.
    local CANARY_VERSION="1"
    local CANARY_LINE="172"
    return 0
}
# END OF SCRIPT — SANITY MARKER
