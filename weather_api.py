class CulturalContextAPI:
    @staticmethod
    def get_context(weather_label: str, event_label: str) -> dict:
        """Combines weather and festival logic with category targeting"""
        
        # Base Weather Multipliers
        weather_map = {
            "Sunny ☀️": 1.0,
            "Rainy 🌧️": 1.4,
            "Heatwave 🌡️": 1.2
        }
        
        # Indian Festival Multipliers & Target Categories
        event_map = {
            "None": {"mult": 1.0, "target": None},
            "Holi 🎨": {"mult": 2.8, "target": ["White", "Kurta", "Linen"]},
            "Diwali 🪔": {"mult": 3.5, "target": ["Saree", "Sherwani", "Ethnic"]},
            "Eid 🌙": {"mult": 2.5, "target": ["Formal", "Traditional", "Kurta"]},
            "Wedding Season 💍": {"mult": 2.2, "target": ["Lehenga", "Suits", "Ethnic"]}
        }
        
        ctx = event_map.get(event_label, {"mult": 1.0, "target": None})
        
        return {
            "weather_multiplier": weather_map.get(weather_label, 1.0),
            "festival_multiplier": ctx["mult"],
            "target_categories": ctx["target"],
            "status": f"Active Context: {event_label} Strategy" if event_label != "None" else "Standard Operations"
        }