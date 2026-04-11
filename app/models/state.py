"""System state management"""
from enum import Enum
from threading import Lock
from typing import Dict


class SystemStatus(Enum):
    """System initialization status"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"


_system_status = SystemStatus.NOT_INITIALIZED
_status_lock = Lock()
_initialization_progress = {
    "current": 0,
    "total": 0,
    "current_store": "",
    "current_category": ""
}


def get_system_status() -> SystemStatus:
    with _status_lock:
        return _system_status


def set_system_status(status: SystemStatus):
    global _system_status
    with _status_lock:
        _system_status = status


def get_initialization_progress() -> Dict:
    with _status_lock:
        return dict(_initialization_progress)


def update_initialization_progress(**kwargs):
    global _initialization_progress
    with _status_lock:
        _initialization_progress.update(kwargs)