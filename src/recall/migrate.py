"""Migration Tooling — automated scripts for migrating to recall-cache."""

import json
import re
from typing import Dict, List, Any, Optional


class MigrationTool:
    """
    Automated migration tool for migrating from other caching solutions.
    
    Usage:
        from recall.migrate import MigrationTool
        
        tool = MigrationTool()
        
        # Migrate from Django Redis
        tool.migrate_from_django_redis(
            settings_path="settings.py",
            output_path="settings_new.py"
        )
        
        # Migrate from Flask-Caching
        tool.migrate_from_flask_caching(
            app_path="app.py",
            output_path="app_new.py"
        )
    """
    
    @staticmethod
    def migrate_from_django_redis(settings_path: str, output_path: str) -> Dict[str, Any]:
        """
        Migrate Django Redis settings to recall-cache.
        
        Args:
            settings_path: Path to current settings.py
            output_path: Path to write new settings.py
            
        Returns:
            Dict with migration results
        """
        with open(settings_path, "r") as f:
            content = f.read()
        
        # Replace CACHES configuration
        old_pattern = r"CACHES\s*=\s*\{[^}]+\}"
        new_caches = """CACHES = {
    'default': {
        'BACKEND': 'recall.plugins.django_plugin.RecallCache',
        'LOCATION': 'recall-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 3,
        }
    }
}"""
        
        new_content = re.sub(old_pattern, new_caches, content)
        
        # Add recall import if not present
        if "import recall" not in new_content:
            new_content = "import recall\n" + new_content
        
        with open(output_path, "w") as f:
            f.write(new_content)
        
        return {
            "status": "success",
            "source": settings_path,
            "output": output_path,
            "changes": ["CACHES configuration", "Added recall import"]
        }
    
    @staticmethod
    def migrate_from_flask_caching(app_path: str, output_path: str) -> Dict[str, Any]:
        """
        Migrate Flask-Caching to recall-cache.
        
        Args:
            app_path: Path to current app.py
            output_path: Path to write new app.py
            
        Returns:
            Dict with migration results
        """
        with open(app_path, "r") as f:
            content = f.read()
        
        # Replace Cache initialization
        old_pattern = r"Cache\(app,\s*config=\{[^}]+\}\)"
        new_init = "recall_cache = FastAPICache(app, backend=MemoryBackend())"
        
        new_content = re.sub(old_pattern, new_init, content)
        
        # Replace cache decorators
        new_content = re.sub(
            r"@cache\.cached\([^)]+\)",
            "@recall_cache.route(ttl='5m')",
            new_content
        )
        
        with open(output_path, "w") as f:
            f.write(new_content)
        
        return {
            "status": "success",
            "source": app_path,
            "output": output_path,
            "changes": ["Cache initialization", "Cache decorators"]
        }
    
    @staticmethod
    def migrate_from_cachetools(code_path: str, output_path: str) -> Dict[str, Any]:
        """
        Migrate cachetools to recall-cache.
        
        Args:
            code_path: Path to current code
            output_path: Path to write new code
            
        Returns:
            Dict with migration results
        """
        with open(code_path, "r") as f:
            content = f.read()
        
        # Replace TTLCache initialization
        old_pattern = r"TTLCache\(maxsize=\d+,\s*ttl=\d+\)"
        new_init = "cache = MemoryBackend(maxsize=1000)"
        
        new_content = re.sub(old_pattern, new_init, content)
        
        # Replace cache get/set
        new_content = re.sub(
            r"cache\[([^]]+)\]\s*=\s*([^]]+)",
            r"cache.set(\1, \2, ttl=300)",
            new_content
        )
        
        with open(output_path, "w") as f:
            f.write(new_content)
        
        return {
            "status": "success",
            "source": code_path,
            "output": output_path,
            "changes": ["Cache initialization", "Cache get/set operations"]
        }
    
    @staticmethod
    def generate_migration_report(source: str, output: str) -> str:
        """Generate a human-readable migration report."""
        return f"""
# Migration Report

## Source: {source}
## Output: {output}

### Changes Made:
- Updated cache backend configuration
- Replaced cache decorators
- Added necessary imports

### Next Steps:
1. Review the generated code
2. Run tests
3. Deploy to staging
4. Monitor performance

### Rollback:
- Original file: {source}.backup
- To restore: cp {source}.backup {source}
"""
    
    @staticmethod
    def backup_file(path: str) -> str:
        """Create a backup of a file."""
        backup_path = f"{path}.backup"
        with open(path, "r") as f:
            content = f.read()
        with open(backup_path, "w") as f:
            f.write(content)
        return backup_path


class ConfigMigrator:
    """Migrate configuration files."""
    
    @staticmethod
    def migrate_django_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate Django settings dict."""
        new_settings = settings.copy()
        
        if "CACHES" in new_settings:
            new_settings["CACHES"] = {
                "default": {
                    "BACKEND": "recall.plugins.django_plugin.RecallCache",
                    "LOCATION": "recall-cache",
                    "OPTIONS": {
                        "MAX_ENTRIES": 10000,
                        "CULL_FREQUENCY": 3,
                    }
                }
            }
        
        return new_settings
    
    @staticmethod
    def migrate_flask_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate Flask config dict."""
        new_config = config.copy()
        
        if "CACHE_TYPE" in new_config:
            del new_config["CACHE_TYPE"]
            new_config["RECALL_BACKEND"] = "memory"
            new_config["RECALL_MAXSIZE"] = 1000
        
        return new_config
    
    @staticmethod
    def migrate_fastapi_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate FastAPI config dict."""
        new_config = config.copy()
        
        if "CACHE_BACKEND" in new_config:
            new_config["RECALL_BACKEND"] = new_config.pop("CACHE_BACKEND")
        
        return new_config


class DataMigrator:
    """Migrate cached data between backends."""
    
    @staticmethod
    def export_data(backend: Any, output_path: str) -> int:
        """Export all data from a backend to a file."""
        keys = backend.keys()
        data = {}
        
        for key in keys:
            result = backend.get(key)
            if result:
                expire_time, value = result
                data[key] = {
                    "value": value,
                    "expire_time": expire_time,
                    "ttl": expire_time - __import__("time").time(),
                }
        
        with open(output_path, "w") as f:
            json.dump({
                "timestamp": __import__("time").time(),
                "key_count": len(data),
                "data": data,
            }, f, indent=2, default=str)
        
        return len(data)
    
    @staticmethod
    def import_data(backend: Any, input_path: str, overwrite: bool = False) -> int:
        """Import data from a file to a backend."""
        with open(input_path, "r") as f:
            backup = json.load(f)
        
        data = backup.get("data", {})
        restored = 0
        
        for key, item in data.items():
            if not overwrite and backend.get(key):
                continue
            
            ttl = item.get("ttl", 0)
            if ttl > 0:
                backend.set(key, item["value"], ttl)
                restored += 1
        
        return restored
    
    @staticmethod
    def migrate_between_backends(source: Any, target: Any, overwrite: bool = False) -> int:
        """Migrate data directly between two backends."""
        keys = source.keys()
        migrated = 0
        
        for key in keys:
            result = source.get(key)
            if result:
                expire_time, value = result
                remaining = expire_time - __import__("time").time()
                
                if remaining > 0:
                    if not overwrite and target.get(key):
                        continue
                    target.set(key, value, remaining)
                    migrated += 1
        
        return migrated
