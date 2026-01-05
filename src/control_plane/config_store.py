"""Atomic config store with validation and backup

REQUIREMENTS:
- Atomic writes (tmp + fsync + rename)
- Backup on every write (.bak)
- Validation before commit
- Safe defaults if file missing
- NO SECRETS in config files
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .schema import RuntimeConfig, get_default_config


class ConfigStore:
    """Manages runtime config with atomic writes and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config store
        
        Args:
            config_path: Path to runtime config file. Defaults to runtime/config.yaml
                        Can be overridden with RUNTIME_CONFIG_PATH env var
        """
        if config_path is None:
            config_path = os.getenv("RUNTIME_CONFIG_PATH", "runtime/config.yaml")
        
        self.config_path = Path(config_path)
        self.backup_path = self.config_path.with_suffix('.yaml.bak')
        self._last_hash: Optional[str] = None
        
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _compute_hash(self, config: RuntimeConfig) -> str:
        """Compute hash of config for change detection"""
        config_str = str(config.to_dict())
        return hashlib.sha256(config_str.encode('utf-8')).hexdigest()
    
    def load(self) -> RuntimeConfig:
        """Load config from file, or return defaults if missing"""
        if not self.config_path.exists():
            config = get_default_config()
            # Save defaults so file exists for next time
            self._save_without_backup(config)
            return config
        
        try:
            config = RuntimeConfig.load_from_yaml(str(self.config_path))
            errors = config.validate()
            if errors:
                raise ValueError(f"Invalid config: {'; '.join(errors)}")
            
            self._last_hash = self._compute_hash(config)
            return config
        except Exception as e:
            # If config is corrupted, restore from backup
            if self.backup_path.exists():
                try:
                    shutil.copy(self.backup_path, self.config_path)
                    config = RuntimeConfig.load_from_yaml(str(self.config_path))
                    self._last_hash = self._compute_hash(config)
                    return config
                except Exception:
                    pass
            
            # Last resort: return defaults
            config = get_default_config()
            return config
    
    def save(self, partial_update: Optional[Dict[str, Any]] = None) -> RuntimeConfig:
        """Save config with atomic write and validation
        
        Args:
            partial_update: Optional dict of fields to update. If None, saves current config.
        
        Returns:
            Updated config object
        
        Raises:
            ValueError: If validation fails (old config is preserved)
        """
        # Load current config
        current = self.load()
        
        # Apply partial update if provided
        if partial_update is not None:
            current_dict = current.to_dict()
            # Merge updates (shallow merge for top-level keys)
            for key, value in partial_update.items():
                if key in current_dict:
                    # If nested dict, merge nested keys
                    if isinstance(current_dict[key], dict) and isinstance(value, dict):
                        current_dict[key].update(value)
                    else:
                        current_dict[key] = value
            
            # Reconstruct config object
            new_config = RuntimeConfig.from_dict(current_dict)
        else:
            new_config = current
        
        # Validate before writing
        errors = new_config.validate()
        if errors:
            raise ValueError(f"Config validation failed: {'; '.join(errors)}")
        
        # Atomic write with backup
        self._atomic_write(new_config)
        self._last_hash = self._compute_hash(new_config)
        
        return new_config
    
    def _atomic_write(self, config: RuntimeConfig) -> None:
        """Atomic write: tmp + fsync + rename + backup"""
        # Create backup of old config
        if self.config_path.exists():
            shutil.copy(self.config_path, self.backup_path)
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.config_path.parent,
            prefix='.config_',
            suffix='.yaml.tmp',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            config.save_to_yaml(str(tmp_path))
            
            # Fsync to ensure write to disk
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        
        # Atomic rename
        tmp_path.replace(self.config_path)
    
    def _save_without_backup(self, config: RuntimeConfig) -> None:
        """Save config without backup (used for initial defaults)"""
        config.save_to_yaml(str(self.config_path))
    
    def has_changed(self) -> bool:
        """Check if config file has changed since last load (for hot-reload)"""
        if not self.config_path.exists():
            return False
        
        try:
            current = RuntimeConfig.load_from_yaml(str(self.config_path))
            current_hash = self._compute_hash(current)
            return current_hash != self._last_hash
        except Exception:
            return False
    
    def get_mtime(self) -> float:
        """Get config file modification time (alternative change detection)"""
        if not self.config_path.exists():
            return 0.0
        return self.config_path.stat().st_mtime
