from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.image import Image
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp

import requests
import datetime
import json

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from plyer import gps


class WeatherCard(MDCard):
    def __init__(self, title, value, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(100)
        self.padding = dp(8)
        self.elevation = 2
        self.radius = [10, 10, 10, 10]
        self.md_bg_color = [0.95, 0.95, 0.95, 1]

        title_label = MDLabel(
            text=title,
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20)
        )

        value_label = MDLabel(
            text=value,
            font_style="H6",
            theme_text_color="Primary",
            halign="center"
        )

        self.add_widget(title_label)
        self.add_widget(value_label)
        self.value_label = value_label

    def update_value(self, value):
        self.value_label.text = value


class WeatherApp(MDApp):
    latitude = StringProperty("44.3907")
    longitude = StringProperty("7.5483")

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "DeepOrange"
        self.theme_cls.theme_style = "Light"

        screen = MDScreen()
        layout = MDBoxLayout(orientation="vertical")

        # Navigation bar con logo
        self.toolbar = MDTopAppBar(
            title="T.S. Weather",
            elevation=10,
            pos_hint={"top": 1}
        )
        logo = Image(source="logo.png", size_hint=(None, None), size=(dp(40), dp(40)))
        self.toolbar.add_widget(logo)

        layout.add_widget(self.toolbar)

        # Label coordinate
        self.location_label = MDLabel(
            text=f"Location: {self.latitude}, {self.longitude}",
            halign="center",
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(self.location_label)

        # Scrollable weather content
        scroll = MDScrollView()
        self.weather_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(10),
            size_hint_y=None
        )
        self.weather_container.bind(minimum_height=self.weather_container.setter('height'))
        scroll.add_widget(self.weather_container)

        layout.add_widget(scroll)

        screen.add_widget(layout)

        # Aggiunta delle card
        self.max_temp_card = WeatherCard("Maximum Temperature", "Loading...")
        self.min_temp_card = WeatherCard("Minimum Temperature", "Loading...")
        self.sunrise_card = WeatherCard("Sunrise Time", "Loading...")
        self.sunset_card = WeatherCard("Sunset Time", "Loading...")
        self.uv_index_card = WeatherCard("UV Index", "Loading...")
        self.sunshine_card = WeatherCard("Sunshine Duration", "Loading...")
        self.daylight_card = WeatherCard("Daylight Duration", "Loading...")
        self.precip_prob_card = WeatherCard("Precipitation Probability", "Loading...")
        self.wind_speed_card = WeatherCard("Wind Speed", "Loading...")

        for card in [self.max_temp_card, self.min_temp_card, self.sunrise_card,
                     self.sunset_card, self.uv_index_card, self.sunshine_card,
                     self.daylight_card, self.precip_prob_card, self.wind_speed_card]:
            self.weather_container.add_widget(card)

        # Gestione GPS
        if platform == 'android':
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ])
            try:
                gps.configure(on_location=self.on_location)
                gps.start(minTime=1000, minDistance=0)
            except NotImplementedError:
                print("GPS non implementato")

        Clock.schedule_once(self.fetch_weather_data, 1)

        return screen

    def on_location(self, **kwargs):
        if 'lat' in kwargs and 'lon' in kwargs:
            self.latitude = str(kwargs['lat'])
            self.longitude = str(kwargs['lon'])
            self.location_label.text = f"Location: {self.latitude}, {self.longitude}"
            self.fetch_weather_data()

    def fetch_weather_data(self, *args):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "daily": ["temperature_2m_max", "temperature_2m_min", "sunset", "sunrise",
                      "uv_index_max", "sunshine_duration", "daylight_duration",
                      "precipitation_probability_max"],
            "hourly": "wind_speed_10m",
            "timezone": "Europe/Berlin"
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                self.process_weather_data(response.json())
            else:
                print(f"Errore: {response.status_code}")
        except Exception as e:
            print(f"Errore richiesta API: {e}")

    def process_weather_data(self, data):
        try:
            daily = data.get('daily', {})
            hourly = data.get('hourly', {})

            self.max_temp_card.update_value(f"{daily.get('temperature_2m_max', ['N/A'])[0]}°C")
            self.min_temp_card.update_value(f"{daily.get('temperature_2m_min', ['N/A'])[0]}°C")

            sunrise = daily.get('sunrise', ['N/A'])[0]
            sunset = daily.get('sunset', ['N/A'])[0]

            if sunrise != 'N/A':
                self.sunrise_card.update_value(datetime.datetime.fromisoformat(sunrise).strftime('%H:%M'))

            if sunset != 'N/A':
                self.sunset_card.update_value(datetime.datetime.fromisoformat(sunset).strftime('%H:%M'))

            self.uv_index_card.update_value(str(daily.get('uv_index_max', ['N/A'])[0]))

            sunshine = daily.get('sunshine_duration', ['N/A'])[0]
            if sunshine != 'N/A':
                self.sunshine_card.update_value(f"{round(sunshine / 3600, 1)} h")

            daylight = daily.get('daylight_duration', ['N/A'])[0]
            if daylight != 'N/A':
                self.daylight_card.update_value(f"{round(daylight / 3600, 1)} h")

            self.precip_prob_card.update_value(f"{daily.get('precipitation_probability_max', ['N/A'])[0]}%")

            current_hour = datetime.datetime.now().hour
            wind = hourly.get('wind_speed_10m', [])
            if len(wind) > current_hour:
                self.wind_speed_card.update_value(f"{wind[current_hour]} km/h")

        except Exception as e:
            print("Errore elaborazione dati:", e)
            print(json.dumps(data, indent=2))


if __name__ == "__main__":
    WeatherApp().run()
