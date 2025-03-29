from functools import wraps

import spotipy


def spotify_api_call(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except spotipy.exceptions.SpotifyException as e:
            action_name = func.__name__.replace('_', ' ')
            self.logger.error(f"❌ Spotify API Fehler bei '{action_name}': {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unerwarteter Fehler bei '{func.__name__}': {e}")
            return False
            
    return wrapper