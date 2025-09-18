"""
Performance Optimization for Rural Banking
Lightweight algorithms and caching for low-resource devices
"""

import time
import functools
import threading
import gc
from typing import Dict, Any, Optional, Callable
import psutil
import os
from collections import OrderedDict
import pickle
import gzip
import json

class LRUCache:
    """Lightweight LRU Cache implementation for memory efficiency"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put item in cache"""
        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache[key] = value
                self.cache.move_to_end(key)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    self.cache.popitem(last=False)
                self.cache[key] = value
    
    def clear(self) -> None:
        """Clear cache"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)

class PerformanceMonitor:
    """Monitor system performance and resource usage"""
    
    def __init__(self):
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'response_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.start_time = time.time()
    
    def record_cpu_usage(self):
        """Record current CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics['cpu_usage'].append({
                'timestamp': time.time(),
                'value': cpu_percent
            })
            # Keep only last 100 measurements
            if len(self.metrics['cpu_usage']) > 100:
                self.metrics['cpu_usage'] = self.metrics['cpu_usage'][-100:]
        except:
            pass  # Ignore errors on systems without psutil
    
    def record_memory_usage(self):
        """Record current memory usage"""
        try:
            memory = psutil.virtual_memory()
            self.metrics['memory_usage'].append({
                'timestamp': time.time(),
                'value': memory.percent,
                'available_mb': memory.available / (1024 * 1024)
            })
            # Keep only last 100 measurements
            if len(self.metrics['memory_usage']) > 100:
                self.metrics['memory_usage'] = self.metrics['memory_usage'][-100:]
        except:
            pass
    
    def record_response_time(self, duration: float):
        """Record response time"""
        self.metrics['response_times'].append({
            'timestamp': time.time(),
            'duration': duration
        })
        # Keep only last 1000 measurements
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics['cache_misses'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Calculate averages
        avg_cpu = 0
        if self.metrics['cpu_usage']:
            avg_cpu = sum(m['value'] for m in self.metrics['cpu_usage']) / len(self.metrics['cpu_usage'])
        
        avg_memory = 0
        if self.metrics['memory_usage']:
            avg_memory = sum(m['value'] for m in self.metrics['memory_usage']) / len(self.metrics['memory_usage'])
        
        avg_response_time = 0
        if self.metrics['response_times']:
            avg_response_time = sum(m['duration'] for m in self.metrics['response_times']) / len(self.metrics['response_times'])
        
        # Cache hit ratio
        total_cache_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_ratio = 0
        if total_cache_requests > 0:
            cache_hit_ratio = self.metrics['cache_hits'] / total_cache_requests
        
        return {
            'uptime_seconds': uptime,
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_response_time_ms': avg_response_time * 1000,
            'cache_hit_ratio': cache_hit_ratio,
            'total_requests': len(self.metrics['response_times']),
            'timestamp': current_time
        }

class DataCompressor:
    """Compress data for efficient storage and transmission"""
    
    @staticmethod
    def compress_json(data: Dict[str, Any]) -> bytes:
        """Compress JSON data"""
        json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
        return gzip.compress(json_str.encode('utf-8'))
    
    @staticmethod
    def decompress_json(compressed_data: bytes) -> Dict[str, Any]:
        """Decompress JSON data"""
        json_str = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_str)
    
    @staticmethod
    def compress_object(obj: Any) -> bytes:
        """Compress Python object using pickle"""
        pickled = pickle.dumps(obj)
        return gzip.compress(pickled)
    
    @staticmethod
    def decompress_object(compressed_data: bytes) -> Any:
        """Decompress Python object"""
        pickled = gzip.decompress(compressed_data)
        return pickle.loads(pickled)

def performance_timer(func: Callable) -> Callable:
    """Decorator to measure function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            performance_monitor.record_response_time(duration)
            if duration > 1.0:  # Log slow operations
                print(f"Slow operation: {func.__name__} took {duration:.2f}s")
    return wrapper

def memory_efficient_cache(max_size: int = 50):
    """Decorator for memory-efficient caching"""
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(max_size)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                performance_monitor.record_cache_hit()
                return result
            
            # Execute function and cache result
            performance_monitor.record_cache_miss()
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        wrapper.cache_clear = cache.clear
        wrapper.cache_size = cache.size
        return wrapper
    return decorator

class ResourceManager:
    """Manage system resources efficiently"""
    
    def __init__(self):
        self.cleanup_threshold = 80  # Memory usage percentage
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def check_memory_usage(self) -> float:
        """Check current memory usage percentage"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except:
            return 0.0
    
    def force_garbage_collection(self):
        """Force garbage collection"""
        gc.collect()
        print("Forced garbage collection completed")
    
    def cleanup_if_needed(self):
        """Cleanup resources if memory usage is high"""
        current_time = time.time()
        
        # Check if cleanup interval has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        memory_usage = self.check_memory_usage()
        
        if memory_usage > self.cleanup_threshold:
            print(f"High memory usage detected: {memory_usage:.1f}%")
            self.force_garbage_collection()
            self.last_cleanup = current_time
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_count': cpu_count,
                'total_memory_gb': memory.total / (1024**3),
                'available_memory_gb': memory.available / (1024**3),
                'memory_usage_percent': memory.percent,
                'total_disk_gb': disk.total / (1024**3),
                'free_disk_gb': disk.free / (1024**3),
                'disk_usage_percent': (disk.used / disk.total) * 100
            }
        except:
            return {'error': 'Unable to get system information'}

class LightweightMLOptimizer:
    """Optimize ML operations for low-resource devices"""
    
    @staticmethod
    def reduce_model_precision(model_data: Any) -> Any:
        """Reduce model precision to save memory"""
        # This would implement model quantization for TensorFlow/PyTorch models
        # For now, return as-is
        return model_data
    
    @staticmethod
    def batch_predictions(inputs: list, batch_size: int = 32) -> list:
        """Process predictions in batches to manage memory"""
        results = []
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            # Process batch (placeholder)
            batch_results = batch  # Replace with actual prediction logic
            results.extend(batch_results)
        return results
    
    @staticmethod
    def optimize_feature_extraction(features: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize feature extraction for performance"""
        # Remove unnecessary features, normalize data types
        optimized = {}
        for key, value in features.items():
            if isinstance(value, float):
                # Reduce precision for floats
                optimized[key] = round(value, 4)
            elif isinstance(value, list) and len(value) > 100:
                # Truncate large lists
                optimized[key] = value[:100]
            else:
                optimized[key] = value
        return optimized

# Global instances
performance_monitor = PerformanceMonitor()
resource_manager = ResourceManager()
data_compressor = DataCompressor()
ml_optimizer = LightweightMLOptimizer()

# Background monitoring thread
def start_performance_monitoring():
    """Start background performance monitoring"""
    def monitor_loop():
        while True:
            try:
                performance_monitor.record_cpu_usage()
                performance_monitor.record_memory_usage()
                resource_manager.cleanup_if_needed()
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                print(f"Performance monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print("Performance monitoring started")
