from functools import wraps
import logging

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
                self_instance = args[0]  # 'self' ist immer das erste Argument bei Methoden
                logger = getattr(self_instance, 'logger', None)
                msg = f"Fehler {context}: {e}" if context else f"Fehler: {e}"
                if logger:
                    logger.error(f"❌ {msg}")
                else:
                    print(f"[WARNUNG] Kein logger gefunden auf self: {msg}")
        return wrapper
    return decorator