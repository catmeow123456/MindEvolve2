import os
import json
import hashlib
from typing import Optional
from evolution.config import CacheConfig

class SimpleCacheManager:
    def __init__(self, cache_config: CacheConfig, name: str):
        self.config = cache_config
        self.name = name
        self.cache_file = os.path.join(cache_config.cache_dir, f"{name}_cache.json")
        os.makedirs(cache_config.cache_dir, exist_ok=True)
        self.cache_data = self._load_cache()

    def _load_cache(self) -> dict[str, str]:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Warning: Failed to load cache from {self.cache_file}")
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def _generate_cache_key(self, **kwargs) -> str:
        """Generate cache key from messages and parameters"""
        cache_input = {**kwargs}
        try:
            cache_str = json.dumps(cache_input, sort_keys=True, ensure_ascii=False)
        except:
            raise ValueError(f"Failed to generate cache key for {kwargs}")
        return hashlib.md5(cache_str.encode('utf-8')).hexdigest()

    def get_cached_response(self, **kwargs) -> Optional[str]:
        """Get cached response if exists"""
        cache_key = self._generate_cache_key(**kwargs)
        response = self.cache_data.get(cache_key)
        if response is not None:
            print(f"Cache Hit for {cache_key}")
        return response

    def cache_response(self, response: str, **kwargs):
        """Cache a response"""
        cache_key = self._generate_cache_key(**kwargs)
        self.cache_data[cache_key] = response
        print(f"Cached response for key: {cache_key[:16]}...")
        
        # Save to file periodically
        if len(self.cache_data) % 10 == 0:  # Save every 10 entries
            self._save_cache()

    def __del__(self):
        """Save cache when object is destroyed"""
        try:
            self._save_cache()
        except:
            pass
