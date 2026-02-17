/**
 * Alpine.js global store and page components.
 * Each function returns an Alpine.js component data object.
 */

/* ---- Global Dashboard Component ---- */
function dashboard() {
    return {
        activeTab: 'overview',
        darkMode: localStorage.getItem('nosweb-dark') !== 'false', // dark by default
        hasGpu: document.body.dataset.hasGpu === 'true',

        switchTab(tab) {
            this.activeTab = tab;
            window.dispatchEvent(new CustomEvent('tab-changed', { detail: tab }));
        },

        toggleDark() {
            this.darkMode = !this.darkMode;
            localStorage.setItem('nosweb-dark', this.darkMode);
        }
    };
}

/* ---- Overview Page ---- */
function overviewPage() {
    return {
        stats: {},
        containers: [],
        gpuDevices: [],
        _interval: null,

        async startPolling() {
            await this.fetchData();
            this._interval = setInterval(() => this.fetchData(), 5000);
        },

        stopPolling() {
            if (this._interval) {
                clearInterval(this._interval);
                this._interval = null;
            }
        },

        async fetchData() {
            try {
                const res = await fetch('/api/overview/summary');
                const data = await res.json();
                this.stats = data.system;
                this.containers = data.containers.list;
                this.gpuDevices = data.gpu.devices;
            } catch (e) {
                console.error('Failed to fetch overview:', e);
            }
        },

        formatUptime(seconds) {
            if (!seconds) return '--';
            const d = Math.floor(seconds / 86400);
            const h = Math.floor((seconds % 86400) / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            if (d > 0) return `${d}d ${h}h ${m}m`;
            if (h > 0) return `${h}h ${m}m`;
            return `${m}m`;
        },

        destroy() {
            this.stopPolling();
        }
    };
}

/* ---- Log Viewer ---- */
function logViewer() {
    return {
        containers: [],
        selectedContainer: '',
        lines: [],
        autoScroll: true,
        ws: null,

        async loadContainers() {
            try {
                const res = await fetch('/api/logs/containers');
                this.containers = await res.json();
            } catch (e) {
                console.error('Failed to load containers:', e);
            }
        },

        switchContainer() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
            this.lines = [];

            if (!this.selectedContainer) return;

            this.ws = new WSManager(`/api/logs/ws/${this.selectedContainer}`, {
                onMessage: (msg) => {
                    if (msg.type === 'log_line') {
                        this.lines.push(msg.data);
                        if (this.lines.length > 5000) this.lines.shift();
                        if (this.autoScroll) {
                            this.$nextTick(() => {
                                const el = this.$refs.logOutput;
                                if (el) el.scrollTop = el.scrollHeight;
                            });
                        }
                    }
                }
            });
            this.ws.connect();
        },

        clearLogs() {
            this.lines = [];
        },

        downloadLogs() {
            const blob = new Blob([this.lines.join('')], { type: 'text/plain' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${this.selectedContainer}-logs.txt`;
            a.click();
            URL.revokeObjectURL(a.href);
        },

        destroy() {
            if (this.ws) this.ws.close();
        }
    };
}

/* ---- GPU Monitor ---- */
function gpuMonitor() {
    return {
        enabled: document.body.dataset.hasGpu === 'true',
        devices: [],
        ws: null,

        connect() {
            if (!this.enabled || this.ws) return;

            this.ws = new WSManager('/api/gpu/ws', {
                onMessage: (msg) => {
                    if (msg.type === 'gpu_stats') {
                        this.devices = msg.data;
                    }
                }
            });
            this.ws.connect();
        },

        disconnect() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
        },

        destroy() {
            this.disconnect();
        }
    };
}

/* ---- Command Center ---- */
function commandCenter() {
    return {
        presets: {},
        categories: [],
        customCmd: '',
        output: '',
        isRunning: false,
        ws: null,
        history: [],
        historyIndex: -1,

        async init() {
            try {
                const res = await fetch('/api/commands/presets');
                this.presets = await res.json();
                this.categories = [...new Set(
                    Object.values(this.presets).map(p => p.category)
                )];
            } catch (e) {
                console.error('Failed to load presets:', e);
            }

            this.ws = new WSManager('/api/commands/ws/exec', {
                onMessage: (msg) => {
                    if (msg.type === 'exec_start') {
                        this.output += `\n$ ${msg.command}\n`;
                    } else if (msg.type === 'exec_output') {
                        this.output += msg.data;
                    } else if (msg.type === 'exec_done') {
                        this.isRunning = false;
                        this.output += '\n';
                        this.scrollTerminal();
                    } else if (msg.type === 'exec_error') {
                        this.output += `\n[ERROR] ${msg.data}\n`;
                        this.isRunning = false;
                    }
                }
            });
            this.ws.connect();
        },

        getByCategory(category) {
            const result = {};
            for (const [key, preset] of Object.entries(this.presets)) {
                if (preset.category === category) result[key] = preset;
            }
            return result;
        },

        runCommand(cmd) {
            if (!cmd || !cmd.trim() || this.isRunning) return;
            this.isRunning = true;
            this.history.push(cmd);
            this.historyIndex = this.history.length;
            this.ws.send({ command: cmd.trim() });
        },

        historyUp() {
            if (this.historyIndex > 0) {
                this.historyIndex--;
                this.customCmd = this.history[this.historyIndex];
            }
        },

        historyDown() {
            if (this.historyIndex < this.history.length - 1) {
                this.historyIndex++;
                this.customCmd = this.history[this.historyIndex];
            } else {
                this.historyIndex = this.history.length;
                this.customCmd = '';
            }
        },

        clearOutput() {
            this.output = '';
        },

        scrollTerminal() {
            this.$nextTick(() => {
                const el = this.$refs.terminal;
                if (el) el.scrollTop = el.scrollHeight;
            });
        },

        destroy() {
            if (this.ws) this.ws.close();
        }
    };
}
