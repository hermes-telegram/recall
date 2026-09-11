"""Admin Panel — built-in web UI for recall-cache management."""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, Callable

from recall.cache import CacheBackend, MemoryBackend, DiskBackend, RedisBackend, MultiTierBackend


class AdminPanel:
    """
    Built-in admin panel for recall-cache.
    
    Usage:
        from recall import cache, MemoryBackend
        from recall.admin import AdminPanel
        
        backend = MemoryBackend()
        panel = AdminPanel(backend, port=8080)
        panel.start()  # Starts web UI at http://localhost:8080
        
    Or with decorator:
        @cache(ttl="1h", backend=backend, admin=True)
        def my_func(x):
            return x * 2
    """
    
    def __init__(
        self,
        backend: CacheBackend,
        port: int = 8080,
        host: str = "0.0.0.0",
        auth_token: Optional[str] = None,
        enable_metrics: bool = True,
        enable_audit: bool = True,
    ):
        self.backend = backend
        self.port = port
        self.host = host
        self.auth_token = auth_token
        self.enable_metrics = enable_metrics
        self.enable_audit = enable_audit
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._audit_log: list = []
        self._start_time = time.time()
        
    def _log_audit(self, action: str, details: str = ""):
        """Log an audit entry."""
        if self.enable_audit:
            self._audit_log.append({
                "timestamp": time.time(),
                "action": action,
                "details": details,
            })
            # Keep only last 1000 entries
            if len(self._audit_log) > 1000:
                self._audit_log = self._audit_log[-1000:]
    
    def start(self):
        """Start the admin panel in a background thread."""
        if self._server:
            return
        
        handler = self._create_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"✅ Admin panel started at http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the admin panel."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
    
    def _create_handler(self) -> type:
        """Create request handler class."""
        panel = self
        
        class AdminHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)
                
                # Auth check
                if panel.auth_token:
                    token = params.get("token", [None])[0]
                    if token != panel.auth_token:
                        self.send_error(401, "Unauthorized")
                        return
                
                # Routes
                if path == "/":
                    self._serve_dashboard()
                elif path == "/api/stats":
                    self._serve_stats()
                elif path == "/api/keys":
                    self._serve_keys()
                elif path == "/api/health":
                    self._serve_health()
                elif path == "/api/metrics":
                    self._serve_metrics()
                elif path == "/api/audit":
                    self._serve_audit()
                else:
                    self.send_error(404, "Not Found")
            
            def do_DELETE(self):
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)
                
                # Auth check
                if panel.auth_token:
                    token = params.get("token", [None])[0]
                    if token != panel.auth_token:
                        self.send_error(401, "Unauthorized")
                        return
                
                if path == "/api/cache":
                    panel.backend.clear()
                    panel._log_audit("clear_all")
                    self._serve_json({"status": "ok", "message": "Cache cleared"})
                elif path.startswith("/api/cache/"):
                    key = path[len("/api/cache/"):]
                    panel.backend.delete(key)
                    panel._log_audit("delete_key", key)
                    self._serve_json({"status": "ok", "message": f"Key '{key}' deleted"})
                else:
                    self.send_error(404, "Not Found")
            
            def _serve_json(self, data: dict):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode())
            
            def _serve_dashboard(self):
                """Serve HTML dashboard."""
                html = panel._get_dashboard_html()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode())
            
            def _serve_stats(self):
                """Serve cache statistics."""
                health = panel.backend.health()
                stats = {
                    "backend": health,
                    "uptime": time.time() - panel._start_time,
                    "admin_panel": {
                        "port": panel.port,
                        "auth_enabled": panel.auth_token is not None,
                        "metrics_enabled": panel.enable_metrics,
                        "audit_enabled": panel.enable_audit,
                    }
                }
                self._serve_json(stats)
            
            def _serve_keys(self):
                """Serve list of keys."""
                keys = panel.backend.keys()
                self._serve_json({"keys": keys, "count": len(keys)})
            
            def _serve_health(self):
                """Serve health check."""
                health = panel.backend.health()
                status = 200 if health.get("status") == "healthy" else 503
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(health, indent=2).encode())
            
            def _serve_metrics(self):
                """Serve Prometheus-compatible metrics."""
                if not panel.enable_metrics:
                    self.send_error(403, "Metrics disabled")
                    return
                metrics = panel._get_prometheus_metrics()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(metrics.encode())
            
            def _serve_audit(self):
                """Serve audit log."""
                self._serve_json({"audit_log": panel._audit_log[-100:]})
            
            def log_message(self, format, *args):
                pass  # Suppress default logging
        
        return AdminHandler
    
    def _get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics."""
        health = self.backend.health()
        lines = []
        
        # Backend status
        status_val = 1 if health.get("status") == "healthy" else 0
        lines.append(f'recall_cache_backend_status {status_val}')
        
        # Backend type
        backend_type = health.get("type", "unknown")
        lines.append(f'recall_cache_backend_type{{type="{backend_type}"}} 1')
        
        # Key count
        try:
            key_count = len(self.backend.keys())
            lines.append(f'recall_cache_keys_total {key_count}')
        except:
            lines.append(f'recall_cache_keys_total 0')
        
        # Uptime
        lines.append(f'recall_cache_uptime_seconds {time.time() - self._start_time}')
        
        return "\n".join(lines) + "\n"
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>recall-cache Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #e94560; margin-bottom: 20px; }
        .card { background: #16213e; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #0f3460; margin-bottom: 10px; }
        .stat { display: inline-block; margin: 10px 20px 10px 0; }
        .stat-value { font-size: 2em; color: #e94560; }
        .stat-label { color: #888; }
        .btn { background: #e94560; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #c73e54; }
        .btn-danger { background: #dc3545; }
        .keys-list { max-height: 300px; overflow-y: auto; background: #0f3460; padding: 10px; border-radius: 5px; }
        .key-item { padding: 5px; border-bottom: 1px solid #1a1a2e; }
        .key-item:last-child { border-bottom: none; }
        .refresh-btn { float: right; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 recall-cache Admin Panel</h1>
        
        <div class="card">
            <h2>Statistics</h2>
            <div id="stats"></div>
        </div>
        
        <div class="card">
            <h2>Actions</h2>
            <button class="btn btn-danger" onclick="clearCache()">Clear All Cache</button>
            <button class="btn refresh-btn" onclick="refreshData()">Refresh</button>
        </div>
        
        <div class="card">
            <h2>Keys</h2>
            <div id="keys" class="keys-list"></div>
        </div>
        
        <div class="card">
            <h2>Health</h2>
            <div id="health"></div>
        </div>
    </div>
    
    <script>
        async function fetchJSON(url) {
            const res = await fetch(url);
            return res.json();
        }
        
        async function refreshData() {
            const [stats, keys, health] = await Promise.all([
                fetchJSON('/api/stats'),
                fetchJSON('/api/keys'),
                fetchJSON('/api/health')
            ]);
            
            document.getElementById('stats').innerHTML = `
                <div class="stat"><div class="stat-value">${stats.backend.type}</div><div class="stat-label">Backend</div></div>
                <div class="stat"><div class="stat-value">${stats.backend.status}</div><div class="stat-label">Status</div></div>
                <div class="stat"><div class="stat-value">${Math.round(stats.uptime)}s</div><div class="stat-label">Uptime</div></div>
            `;
            
            document.getElementById('keys').innerHTML = keys.keys.map(k => 
                `<div class="key-item">${k} <button class="btn btn-danger" style="padding:2px 5px;font-size:10px;float:right;" onclick="deleteKey('${k}')">Delete</button></div>`
            ).join('');
            
            document.getElementById('health').innerHTML = `<pre>${JSON.stringify(health, null, 2)}</pre>`;
        }
        
        async function clearCache() {
            if (!confirm('Clear all cache?')) return;
            await fetch('/api/cache', { method: 'DELETE' });
            refreshData();
        }
        
        async function deleteKey(key) {
            if (!confirm('Delete key: ' + key + '?')) return;
            await fetch('/api/cache/' + key, { method: 'DELETE' });
            refreshData();
        }
        
        refreshData();
        setInterval(refreshData, 5000);
    </script>
</body>
</html>"""


def start_admin(
    backend: CacheBackend,
    port: int = 8080,
    host: str = "0.0.0.0",
    auth_token: Optional[str] = None,
) -> AdminPanel:
    """
    Start the admin panel for a cache backend.
    
    Usage:
        from recall import cache, MemoryBackend
        from recall.admin import start_admin
        
        backend = MemoryBackend()
        panel = start_admin(backend, port=8080)
    """
    panel = AdminPanel(backend, port=port, host=host, auth_token=auth_token)
    panel.start()
    return panel
