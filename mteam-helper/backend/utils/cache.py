"""
简单的内存缓存工具
用于缓存仪表板数据和下载器状态，减少重复查询
"""

import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import asyncio
import json

class SimpleCache:
    """简单的内存缓存类"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        
        # 检查是否过期
        if time.time() > item['expires_at']:
            del self._cache[key]
            return None
        
        return item['value']
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认 5 分钟
        """
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
    
    def cleanup(self) -> int:
        """清理过期缓存，返回清理的数量"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items()
            if current_time > item['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        current_time = time.time()
        total_items = len(self._cache)
        expired_items = sum(
            1 for item in self._cache.values()
            if current_time > item['expires_at']
        )
        
        return {
            'total_items': total_items,
            'active_items': total_items - expired_items,
            'expired_items': expired_items,
            'memory_usage_kb': len(str(self._cache)) / 1024
        }

# 全局缓存实例
cache = SimpleCache()

def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        key_func: 自定义键生成函数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成键
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"{func.__name__}:{hash(args_str)}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"{func.__name__}:{hash(args_str)}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def cache_key_with_params(*param_names):
    """生成包含指定参数的缓存键"""
    def key_func(*args, **kwargs):
        key_parts = []
        
        # 添加位置参数
        for i, param_name in enumerate(param_names):
            if i < len(args):
                key_parts.append(f"{param_name}:{args[i]}")
        
        # 添加关键字参数
        for param_name in param_names:
            if param_name in kwargs:
                key_parts.append(f"{param_name}:{kwargs[param_name]}")
        
        return ":".join(key_parts)
    
    return key_func

# 定期清理过期缓存的后台任务
async def cache_cleanup_task():
    """定期清理过期缓存"""
    while True:
        try:
            cleaned = cache.cleanup()
            if cleaned > 0:
                print(f"[Cache] 清理了 {cleaned} 个过期缓存项")
        except Exception as e:
            print(f"[Cache] 清理缓存失败: {e}")
        
        # 每 5 分钟清理一次
        await asyncio.sleep(300)

# 缓存统计接口
def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return cache.stats()

# 清空缓存接口
def clear_cache() -> None:
    """清空所有缓存"""
    cache.clear()
    print("[Cache] 已清空所有缓存")