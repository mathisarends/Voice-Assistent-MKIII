import asyncio
from langchain.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field

from tools.lights.bridge import HueBridge
from tools.lights.hue_controller import HueController

# ---- Gemeinsame Basis-Klasse für alle Hue Tools ----

class HueBaseTool(BaseTool):
    
    # Gemeinsame Instanz des HueControllers für alle Tools
    hue_controller: HueController = Field(default_factory=lambda: HueController(HueBridge.connect_by_ip()), exclude=True)
    
    def _run(self, **kwargs):
        return asyncio.run(self._arun(**kwargs))


# ---- Szenen-Management Tools ----

class SceneListInput(BaseModel):
    """Leeres Eingabemodell, da keine Parameter benötigt werden."""
    pass

class SceneListTool(HueBaseTool):
    """Listet alle verfügbaren Philips Hue Lichtszenen auf."""
    
    name: str = "list_hue_scenes"
    description: str = "Listet alle verfügbaren Philips Hue Lichtszenen auf."
    args_schema: Type[BaseModel] = SceneListInput
    
    async def _arun(self) -> str:
        try:
            scenes = await self.hue_controller.get_scene_names()
            if not scenes:
                return "Keine Lichtszenen gefunden."
            return f"Verfügbare Lichtszenen: {', '.join(scenes)}"
        except Exception as e:
            return f"Fehler beim Abrufen der Lichtszenen: {str(e)}"


class SceneActivateInput(BaseModel):
    """Eingabemodell für die Szenenaktivierung."""
    scene_name: str = Field(..., description="Name der zu aktivierenden Lichtszene")

class SceneActivateTool(HueBaseTool):
    """Aktiviert eine bestimmte Philips Hue Lichtszene anhand ihres Namens."""
    
    name: str = "activate_hue_scene"
    description: str = "Aktiviert eine bestimmte Philips Hue Lichtszene anhand ihres Namens."
    args_schema: Type[BaseModel] = SceneActivateInput
    
    async def _arun(self, scene_name: str) -> str:
        try:
            await self.hue_controller.activate_scene(scene_name)
            return f"Lichtszene '{scene_name}' wurde aktiviert."
        except Exception as e:
            return f"Fehler beim Aktivieren der Lichtszene '{scene_name}': {str(e)}"


class SceneNextInput(BaseModel):
    """Leeres Eingabemodell, da keine Parameter benötigt werden."""
    pass

class SceneNextTool(HueBaseTool):
    """Wechselt zur nächsten Philips Hue Lichtszene in der aktuellen Gruppe."""
    
    name: str = "next_hue_scene"
    description: str = "Wechselt zur nächsten Philips Hue Lichtszene in der aktuellen Gruppe."
    args_schema: Type[BaseModel] = SceneNextInput
    
    async def _arun(self) -> str:
        try:
            await self.hue_controller.next_scene()
            return "Zur nächsten Lichtszene gewechselt."
        except Exception as e:
            return f"Fehler beim Wechseln zur nächsten Lichtszene: {str(e)}"


class ScenePreviousInput(BaseModel):
    """Leeres Eingabemodell, da keine Parameter benötigt werden."""
    pass

class ScenePreviousTool(HueBaseTool):
    """Wechselt zur vorherigen Philips Hue Lichtszene in der aktuellen Gruppe."""
    
    name: str = "previous_hue_scene"
    description: str = "Wechselt zur vorherigen Philips Hue Lichtszene in der aktuellen Gruppe."
    args_schema: Type[BaseModel] = ScenePreviousInput
    
    async def _arun(self) -> str:
        try:
            await self.hue_controller.previous_scene()
            return "Zur vorherigen Lichtszene gewechselt."
        except Exception as e:
            return f"Fehler beim Wechseln zur vorherigen Lichtszene: {str(e)}"

# ---- Lichtsteuerung Tools ----

class LightToggleInput(BaseModel):
    """Eingabemodell für das Ein-/Ausschalten der Lichter."""
    action: str = Field(..., description="Gewünschte Aktion: 'on' oder 'off'")
    fade_duration: float = Field(2.0, description="Fade-Dauer in Sekunden (optional)")

class LightToggleTool(HueBaseTool):
    """Schaltet alle Philips Hue Lichter ein oder aus mit einem sanften Übergang."""
    
    name: str = "toggle_hue_lights"
    description: str = "Schaltet alle Philips Hue Lichter ein oder aus mit einem sanften Übergang."
    args_schema: Type[BaseModel] = LightToggleInput
    
    async def _arun(self, action: str, fade_duration: float = 2.0) -> str:
        try:
            if action.lower() == "on":
                await self.hue_controller.turn_on()
                return f"Alle Lichter wurden eingeschaltet."
            elif action.lower() == "off":
                await self.hue_controller.turn_off()
                return f"Alle Lichter wurden ausgeschaltet."
            else:
                return f"Ungültige Aktion: '{action}'. Bitte 'on' oder 'off' verwenden."
        except Exception as e:
            return f"Fehler beim Schalten der Lichter: {str(e)}"


class BrightnessAdjustInput(BaseModel):
    """Eingabemodell für die Helligkeitsanpassung."""
    percent_change: float = Field(..., description="Prozentuale Änderung der Helligkeit (positiv = heller, negativ = dunkler)")

class BrightnessAdjustTool(HueBaseTool):
    """Passt die Helligkeit der Philips Hue Lichter prozentual an."""
    
    name: str = "adjust_hue_brightness"
    description: str = "Passt die Helligkeit der Philips Hue Lichter prozentual an (positiv = heller, negativ = dunkler)."
    args_schema: Type[BaseModel] = BrightnessAdjustInput
    
    async def _arun(self, percent_change: float) -> str:
        try:
            await self.hue_controller.adjust_brightness(percent_change)
            direction = "erhöht" if percent_change > 0 else "verringert"
            return f"Helligkeit wurde um {abs(percent_change)}% {direction}."
        except Exception as e:
            return f"Fehler bei der Helligkeitsanpassung: {str(e)}"


class BrightnessSetInput(BaseModel):
    """Eingabemodell für das Setzen der Helligkeit."""
    percent: int = Field(..., description="Helligkeit in Prozent (0-100)")

class BrightnessSetTool(HueBaseTool):
    """Setzt die Helligkeit der Philips Hue Lichter auf einen bestimmten Prozentwert."""
    
    name: str = "set_hue_brightness"
    description: str = "Setzt die Helligkeit der Philips Hue Lichter auf einen bestimmten Prozentwert (0-100%)."
    args_schema: Type[BaseModel] = BrightnessSetInput
    
    async def _arun(self, percent: int) -> str:
        try:
            # Begrenze den Wert auf 0-100
            percent = max(0, min(100, percent))
            await self.hue_controller.set_brightness(percent)
            return f"Helligkeit wurde auf {percent}% gesetzt."
        except Exception as e:
            return f"Fehler beim Setzen der Helligkeit: {str(e)}"


# ---- Toolkit-Erstellung ----

def get_hue_tools() -> List[BaseTool]:
    return [
        SceneListTool(),
        SceneActivateTool(),
        SceneNextTool(),
        ScenePreviousTool(),
        LightToggleTool(),
        BrightnessAdjustTool(),
        BrightnessSetTool()
    ]