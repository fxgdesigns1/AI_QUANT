"""Log streaming via SSE for dashboard

Tails a log file and streams to clients via Server-Sent Events
Includes basic redaction for secrets
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import AsyncIterator, Optional


class LogStream:
    """Stream log file to SSE clients with secret redaction"""
    
    def __init__(self, log_path: Optional[str] = None):
        """Initialize log stream
        
        Args:
            log_path: Path to log file. Defaults to logs/ai_quant.log
                     Can be overridden with LOG_FILE_PATH env var
        """
        import os
        if log_path is None:
            log_path = os.getenv("LOG_FILE_PATH", "logs/ai_quant.log")
        
        self.log_path = Path(log_path)
        
        # Secret redaction patterns
        self.secret_patterns = [
            # API keys and tokens
            (re.compile(r'(api[_-]?key["\s:=]+)[a-zA-Z0-9_\-]{10,}', re.IGNORECASE), r'\1***REDACTED***'),
            (re.compile(r'(token["\s:=]+)[a-zA-Z0-9_\-\.]{10,}', re.IGNORECASE), r'\1***REDACTED***'),
            (re.compile(r'(bearer\s+)[a-zA-Z0-9_\-\.]{10,}', re.IGNORECASE), r'\1***REDACTED***'),
            # Passwords
            (re.compile(r'(password["\s:=]+)[^\s"]+', re.IGNORECASE), r'\1***REDACTED***'),
            # OANDA-specific
            (re.compile(r'(OANDA_API_KEY["\s:=]+)[a-zA-Z0-9_\-]{10,}', re.IGNORECASE), r'\1***REDACTED***'),
            # Generic secrets
            (re.compile(r'(secret["\s:=]+)[^\s"]+', re.IGNORECASE), r'\1***REDACTED***'),
        ]
    
    def _redact_secrets(self, line: str) -> str:
        """Redact secrets from log line"""
        for pattern, replacement in self.secret_patterns:
            line = pattern.sub(replacement, line)
        return line
    
    async def tail(self, num_lines: int = 100) -> list[str]:
        """Get last N lines from log file (for initial page load)"""
        if not self.log_path.exists():
            return ["# Log file not found - waiting for runner to start..."]
        
        try:
            # Read last N lines efficiently
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                recent_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                return [self._redact_secrets(line.rstrip()) for line in recent_lines]
        except Exception as e:
            return [f"# Error reading log file: {e}"]
    
    async def stream(self) -> AsyncIterator[str]:
        """Stream new log lines as they appear (for SSE)
        
        Yields redacted log lines as they are written
        """
        # Ensure log file exists (or wait for it)
        if not self.log_path.exists():
            yield "data: # Waiting for log file...\n\n"
            # Wait up to 10 seconds for log file to appear
            for _ in range(10):
                await asyncio.sleep(1)
                if self.log_path.exists():
                    break
            else:
                yield "data: # Log file not found\n\n"
                return
        
        # Open file and seek to end
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                # Seek to end
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        # New line available
                        redacted = self._redact_secrets(line.rstrip())
                        yield f"data: {redacted}\n\n"
                    else:
                        # No new lines, wait briefly
                        await asyncio.sleep(0.5)
        except Exception as e:
            yield f"data: # Stream error: {e}\n\n"
