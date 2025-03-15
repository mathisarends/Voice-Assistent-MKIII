from typing import List, Optional, Tuple


class ColorPresets:
    """Preset colors for easy access."""
    
    # Basic colors
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    
    # Mixed colors
    YELLOW = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    CYAN = (0, 255, 255)
    
    # Additional hues
    ORANGE = (255, 165, 0)
    PINK = (255, 192, 203)
    PURPLE = (128, 0, 128)
    TURQUOISE = (64, 224, 208)
    
    # White and gray tones
    WHITE = (255, 255, 255)
    WARM_WHITE = (255, 223, 179)
    COOL_WHITE = (240, 255, 255)
    
    # Moods
    RELAXATION = (70, 130, 180)  # Steel Blue
    CONCENTRATION = (240, 248, 255)  # Alice Blue
    PARTY = (138, 43, 226)  # Blueviolet
    COZY = (210, 105, 30)  # Chocolate
    
    COLORS = {
        "red": RED,
        "green": GREEN,
        "blue": BLUE,
        "yellow": YELLOW,
        "magenta": MAGENTA,
        "cyan": CYAN,
        "orange": ORANGE,
        "pink": PINK,
        "purple": PURPLE,
        "turquoise": TURQUOISE,
        "white": WHITE,
        "warm_white": WARM_WHITE,
        "warm white": WARM_WHITE,
        "cool_white": COOL_WHITE,
        "cool white": COOL_WHITE,
        "relaxation": RELAXATION,
        "concentration": CONCENTRATION,
        "party": PARTY,
        "cozy": COZY,
    }
    
    @classmethod
    def get_color(cls, name: str) -> Optional[Tuple[int, int, int]]:
        """
        Returns RGB values for a named color.
        
        Args:
            name: Name of the color (e.g. "red", "green", etc.)
            
        Returns:
            RGB tuple with values from 0-255 or None if the color was not found
        """
        return cls.COLORS.get(name.lower())
    
    @classmethod
    def list_colors(cls) -> List[str]:
        """Lists all available color names."""
        return list(cls.COLORS.keys())