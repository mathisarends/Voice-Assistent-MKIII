from tools.lights.commands import LightCommandGroup, SetBrightnessCommand, SetColorPresetCommand, SetColorRGBCommand, TurnOnCommand


class LightCommandBuilder:
    """Builder für komplexe Lichtbefehle."""
    
    @staticmethod
    def create_sunrise_command(duration_minutes: float = 10.0) -> LightCommandGroup:
        """
        Erstellt einen Sonnenaufgang-Befehl (langsam aufhellend und von rot nach weiß wechselnd).
        
        Args:
            duration_minutes: Dauer des Sonnenaufgangs in Minuten
            
        Returns:
            Ein LightCommandGroup-Objekt mit den nötigen Teilbefehlen
        """
        # Anzahl der Schritte für einen flüssigen Übergang
        steps = 10
        step_duration = (duration_minutes * 60) / steps
        
        commands = [
            # Zuerst dunkelrot mit geringer Helligkeit
            SetColorRGBCommand(50, 0, 0, 0),
            SetBrightnessCommand(5, 0),
            TurnOnCommand()
        ]
        
        # Helligkeit und Farbe schrittweise anpassen
        for i in range(1, steps + 1):
            # Helligkeit von 5% bis 100%
            brightness = 5 + int((100 - 5) * (i / steps))
            
            # Farbe von rot nach weiß
            red = 50 + int((255 - 50) * (i / steps))
            green = int(255 * (i / steps))
            blue = int(220 * (i / steps))
            
            commands.append(SetColorRGBCommand(red, green, blue, step_duration))
            commands.append(SetBrightnessCommand(brightness, step_duration))
        
        return LightCommandGroup(commands)
    
    @staticmethod
    def create_sunset_command(duration_minutes: float = 10.0) -> LightCommandGroup:
        """
        Erstellt einen Sonnenuntergang-Befehl (langsam abdimmen und von weiß nach rot wechselnd).
        
        Args:
            duration_minutes: Dauer des Sonnenuntergangs in Minuten
            
        Returns:
            Ein LightCommandGroup-Objekt mit den nötigen Teilbefehlen
        """
        # Anzahl der Schritte für einen flüssigen Übergang
        steps = 10
        step_duration = (duration_minutes * 60) / steps
        
        # Starte mit 100% Helligkeit und weißem Licht
        commands = [
            SetColorRGBCommand(255, 255, 220, 0),
            SetBrightnessCommand(100, 0),
            TurnOnCommand()
        ]
        
        # Helligkeit und Farbe schrittweise anpassen
        for i in range(1, steps + 1):
            # Helligkeit von 100% bis 5%
            brightness = 100 - int((100 - 5) * (i / steps))
            
            # Farbe von weiß nach rot
            red = 255
            green = 255 - int(255 * (i / steps))
            blue = 220 - int(220 * (i / steps))
            
            commands.append(SetColorRGBCommand(red, green, blue, step_duration))
            commands.append(SetBrightnessCommand(brightness, step_duration))
        
        return LightCommandGroup(commands)
    
    @staticmethod
    def create_candlelight_command() -> LightCommandGroup:
        """
        Erstellt einen Kerzenlicht-Befehl mit leichtem Flackern.
        
        Returns:
            Ein LightCommandGroup-Objekt mit den nötigen Teilbefehlen
        """
        # Warmes, orangenes Licht
        commands = [
            SetColorRGBCommand(255, 147, 41, 0),
            SetBrightnessCommand(40, 0),
            TurnOnCommand()
        ]
        
        # Ein paar leichte Helligkeitsschwankungen simulieren das Flackern
        flicker_sequence = [38, 42, 39, 41, 37, 40]
        for brightness in flicker_sequence:
            commands.append(SetBrightnessCommand(brightness, 0.3))
        
        return LightCommandGroup(commands)
    
    @staticmethod
    def create_sync_group_command(color_preset: str, brightness: int = 80) -> LightCommandGroup:
        """
        Erstellt einen Befehl, der mehrere Lampen synchronisieren kann.
        
        Args:
            color_preset: Name einer vordefinierten Farbe
            brightness: Helligkeitswert (0-100%)
            
        Returns:
            Ein LightCommandGroup-Objekt mit den nötigen Teilbefehlen
        """
        return LightCommandGroup([
            TurnOnCommand(),
            SetBrightnessCommand(brightness, 0.5),
            SetColorPresetCommand(color_preset, 0.5)
        ])
