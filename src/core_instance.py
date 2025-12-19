# src/core_instance.py
from typing import Optional

# Global storage for the singleton API instance
_api_instance = None

def set_api(instance):
    """Sets the global API instance."""
    global _api_instance
    _api_instance = instance

def get_api():
    """Retrieves the global API instance. Raises error if not set."""
    if _api_instance is None:
        raise RuntimeError("API Instance not initialized (HeadlessApi)")
    return _api_instance

_db_instance = None

def set_db(instance):
    global _db_instance
    _db_instance = instance

def get_db():
    if _db_instance is None:
        raise RuntimeError("DB Instance not initialized")
    return _db_instance
