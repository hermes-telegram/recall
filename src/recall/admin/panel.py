"""Admin Panel — built-in web UI for recall-cache management."""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, Callable, List

from recall.cache import CacheBackend, MemoryBackend, DiskBackend, RedisBackend, MultiTierBackend


class RBACManager:
    """Role-Based Access Control for admin panel."""
    
    def __init__(self):
        self._roles: Dict[str, List[str]] = {
            "admin": ["read", "write", "delete", "admin", "backup", "restore"],
            "operator": ["read", "write", "delete"],
            "viewer": ["read"],
        }
        self._users: Dict[str, Dict[str, Any]] = {}
    
    def add_user(self, username: str, role: str, token: str):
        """Add a user with a role."""
        self._users[username] = {
            "role": role,
            "token": token,
        }
    
    def check_permission(self, token: str, permission: str) -> bool:
        """Check if a token has a permission."""
        for user in self._users.values():
            if user["token"] == token:
                role = user["role"]
                return permission in self._roles.get(role, [])
        return False
    
    def get_role(self, token: str) -> Optional[str]:
        """Get role for a token."""
        for user in self._users.values():
            if user["token"] == token:
                return user["role"]
        return None


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
        enable_rbac: bool = False,
    ):
        self.backend = backend
        self.port = port
        self.host = host
        self.auth_token = auth_token
        self.enable_metrics = enable_metrics
        self.enable_audit = enable_audit
        self.enable_rbac = enable_rbac
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._audit_log: list = []
        self._start_time = time.time()
        self._rbac = RBACManager()
        
        # Add default admin user
        if auth_token:
            self._rbac.add_user("admin", "admin", auth_token)
        
    def _log_audit(self, action: str, details: str = "", user: str = "system"):
        """Log an audit entry."""
        if self.enable_audit:
            self._audit_log.append({
                "timestamp": time.time(),
                "action": action,
                "details": details,
                "user": user,
            })
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
                token = params.get("token", [None])[0]
                if panel.auth_token and token != panel.auth_token:
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
                token = params.get("token", [None])[0]
                if panel.auth_token and token != panel.auth_token:
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
                """Serve HTML dashboard with Glassmorphism design."""
                html = panel._get_glassmorphism_dashboard()
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
        
        status_val = 1 if health.get("status") == "healthy" else 0
        lines.append(f'recall_cache_backend_status {status_val}')
        
        backend_type = health.get("type", "unknown")
        lines.append(f'recall_cache_backend_type{{type="{backend_type}"}} 1')
        
        try:
            key_count = len(self.backend.keys())
            lines.append(f'recall_cache_keys_total {key_count}')
        except:
            lines.append(f'recall_cache_keys_total 0')
        
        lines.append(f'recall_cache_uptime_seconds {time.time() - self._start_time}')
        
        return "\n".join(lines) + "\n"
    
    def _get_glassmorphism_dashboard(self) -> str:
        """Generate Glassmorphism dashboard HTML."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>recall-cache Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container { max-width: 1200px; margin: 0 auto; }
        
        h1 {
            color: #e94560;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 0 0 20px rgba(233, 69, 96, 0.5);
        }
        
        /* Glassmorphism Cards */
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        
        .card h2 {
            color: #e94560;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .stat {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .stat-value {
            font-size: 2.5em;
            color: #e94560;
            font-weight: bold;
            text-shadow: 0 0 15px rgba(233, 69, 96, 0.5);
        }
        
        .stat-label {
            color: #888;
            margin-top: 5px;
            font-size: 0.9em;
        }
        
        /* Buttons */
        .btn {
            background: linear-gradient(135deg, #e94560, #c73e54);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 10px;
            cursor: pointer;
            margin: 5px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(233, 69, 96, 0.6);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #dc3545, #c82333);
            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
        }
        
        .btn-danger:hover {
            box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #28a745, #218838);
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
        }
        
        /* Keys List */
        .keys-list {
            max-height: 400px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 10px;
        }
        
        .key-item {
            padding: 10px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }
        
        .key-item:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .key-item:last-child { border-bottom: none; }
        
        /* Health Status */
        .health-status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-dot.healthy {
            background: #28a745;
            box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
        }
        
        .status-dot.unhealthy {
            background: #dc3545;
            box-shadow: 0 0 10px rgba(220, 53, 69, 0.5);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(233, 69, 96, 0.5);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(233, 69, 96, 0.7);
        }
        
        /* Refresh Button */
        .refresh-btn {
            float: right;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr 1fr;
            }
            h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 recall-cache Admin Panel</h1>
        
        <div class="card">
            <h2>📊 Statistics</h2>
            <div class="stats-grid" id="stats">
                <div class="stat">
                    <div class="stat-value" id="backend-type">-</div>
                    <div class="stat-label">Backend Type</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="backend-status">-</div>
                    <div class="stat-label">Status</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="key-count">-</div>
                    <div class="stat-label">Keys</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="uptime">-</div>
                    <div class="stat-label">Uptime (s)</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>⚡ Actions</h2>
            <button class="btn btn-danger" onclick="clearCache()">🗑️ Clear All Cache</button>
            <button class="btn btn-success" onclick="refreshData()">🔄 Refresh</button>
            <button class="btn" onclick="exportBackup()">📥 Export Backup</button>
        </div>
        
        <div class="card">
            <h2>🔑 Keys</h2>
            <div id="keys" class="keys-list">
                <div class="key-item">Loading...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>❤️ Health</h2>
            <div id="health">
                <div class="health-status">
                    <div class="status-dot healthy"></div>
                    <span>Loading...</span>
                </div>
            </div>
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
            
            document.getElementById('backend-type').textContent = stats.backend.type;
            document.getElementById('backend-status').textContent = stats.backend.status;
            document.getElementById('key-count').textContent = keys.count;
            document.getElementById('uptime').textContent = Math.round(stats.uptime);
            
            const keysHtml = keys.keys.map(k => 
                `<div class="key-item">
                    <span>${k}</span>
                    <button class="btn btn-danger" style="padding:5px 10px;font-size:12px;" onclick="deleteKey('${k}')">Delete</button>
                </div>`
            ).join('');
            document.getElementById('keys').innerHTML = keysHtml || '<div class="key-item">No keys found</div>';
            
            const statusColor = health.status === 'healthy' ? 'healthy' : 'unhealthy';
            document.getElementById('health').innerHTML = `
                <div class="health-status">
                    <div class="status-dot ${statusColor}"></div>
                    <span>${health.status}</span>
                </div>
                <pre style="margin-top:10px;background:rgba(0,0,0,0.2);padding:10px;border-radius:10px;">${JSON.stringify(health, null, 2)}</pre>
            `;
        }
        
        async function clearCache() {
            if (!confirm('⚠️ Clear all cache? This cannot be undone.')) return;
            await fetch('/api/cache', { method: 'DELETE' });
            refreshData();
        }
        
        async function deleteKey(key) {
            if (!confirm('Delete key: ' + key + '?')) return;
            await fetch('/api/cache/' + encodeURIComponent(key), { method: 'DELETE' });
            refreshData();
        }
        
        async function exportBackup() {
            const keys = await fetchJSON('/api/keys');
            const data = {
                timestamp: new Date().toISOString(),
                key_count: keys.count,
                keys: keys.keys
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'recall-backup-' + Date.now() + '.json';
            a.click();
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
