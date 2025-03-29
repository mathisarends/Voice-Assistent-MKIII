import asyncio
import functools
import inspect
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Callable


def log_exceptions_from_self_logger(context: str = ""):
    """
    Decorator für Methoden, die `self.logger` enthalten.
    Holt sich den Logger zur Laufzeit aus dem Objekt.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self_instance = args[
                    0
                ]  # 'self' ist immer das erste Argument bei Methoden
                logger = getattr(self_instance, "logger", None)
                msg = f"Fehler {context}: {e}" if context else f"Fehler: {e}"
                if logger:
                    logger.error(f"❌ {msg}")
                else:
                    print(f"[WARNUNG] Kein logger gefunden auf self: {msg}")

        return wrapper

    return decorator


def measure_performance(func: Callable) -> Callable:
    """
    Einfacher Dekorator zum Messen der Ausführungszeit einer Funktion.
    Funktioniert sowohl mit synchronen als auch mit asynchronen Funktionen.
    """
    @wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        start_time = time.time()
        
        result = await func(self, *args, **kwargs)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.logger.info(f"⏱️ API-Antwortzeit: {elapsed_time:.2f} Sekunden")
        
        return result
    
    @wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        start_time = time.time()
        
        result = func(self, *args, **kwargs)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.logger.info(f"⏱️ API-Antwortzeit: {elapsed_time:.2f} Sekunden")
        
        return result
    
    # Entscheide, ob es eine async-Funktion ist
    if hasattr(func, '__code__') and (func.__code__.co_flags & 0x80):
        return async_wrapper
    return sync_wrapper


_thread_pool = ThreadPoolExecutor()

def non_blocking(func):
    """
    Führt die Funktion in einem separaten Thread aus – egal ob sync oder async.
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_running_loop()

        if inspect.iscoroutinefunction(func):
            # async-Funktion: führe sie im Eventloop in einem separaten Thread aus
            return await loop.run_in_executor(
                _thread_pool,
                lambda: asyncio.run(func(self, *args, **kwargs))
            )
        else:
            # normale Funktion: direkt in Executor ausführen
            return await loop.run_in_executor(
                _thread_pool,
                functools.partial(func, self, *args, **kwargs)
            )

    return wrapper