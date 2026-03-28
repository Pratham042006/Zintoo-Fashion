class WeatherAPI:
    @staticmethod
    def get_weather_context(label: str):
        """Translates UI labels into demand multipliers"""
        contexts = {
            "Sunny ☀️": {"multiplier": 1.0, "status": "Normal"},
            "Rainy 🌧️": {"multiplier": 1.4, "status": "High Demand Surge"},
            "Heatwave 🌡️": {"multiplier": 1.2, "status": "Increased Demand"}
        }
        # Returns the context or a default if label is missing
        return contexts.get(label, {"multiplier": 1.0, "status": "Stable"})