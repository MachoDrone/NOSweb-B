/**
 * WebSocket connection manager with auto-reconnect.
 * Reusable across log viewer, GPU monitor, and command center.
 */
class WSManager {
    constructor(path, options = {}) {
        this.path = path;
        this.onMessage = options.onMessage || (() => {});
        this.onOpen = options.onOpen || (() => {});
        this.onClose = options.onClose || (() => {});
        this.onError = options.onError || (() => {});
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.maxRetries = options.maxRetries || 10;
        this.retries = 0;
        this.ws = null;
        this._closed = false;
    }

    connect() {
        if (this._closed) return;

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}${this.path}`;

        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            this.onError(e);
            this._scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this.retries = 0;
            this.onOpen();
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onMessage(data);
            } catch (e) {
                this.onMessage({ type: 'raw', data: event.data });
            }
        };

        this.ws.onclose = () => {
            this.onClose();
            this._scheduleReconnect();
        };

        this.ws.onerror = (e) => {
            this.onError(e);
        };
    }

    _scheduleReconnect() {
        if (this._closed || this.retries >= this.maxRetries) return;
        this.retries++;
        const delay = this.reconnectDelay * Math.min(this.retries, 5);
        setTimeout(() => this.connect(), delay);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    close() {
        this._closed = true;
        this.maxRetries = 0;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
