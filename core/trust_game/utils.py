"""
Utility functions for Trust Game Evaluator
"""
import time
import datetime
import hashlib


def get_time() -> str:
    """Get current timestamp in formatted string"""
    return datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H:%M:%S.%f")


def sha256_hash(text: str) -> str:
    """Calculate SHA256 hash of text"""
    sha256 = hashlib.sha256()
    sha256.update(text.encode('utf-8'))
    return sha256.hexdigest()
