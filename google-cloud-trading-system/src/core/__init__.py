# Ensure unified credential loader is imported first
try:
    from .unified_credential_loader import ensure_credentials_loaded
    # Auto-load credentials on module import
    ensure_credentials_loaded()
except Exception:
    pass
