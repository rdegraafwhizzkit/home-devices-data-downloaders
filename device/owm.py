import requests


class OWM:

    def __init__(self, url, id, app_id, units, proxies=None):
        self.url = url
        self.id = id
        self.app_id = app_id
        self.units = units
        self.proxies = proxies if proxies is not None else {}

    def get_response(self):
        return requests.get(
            url=self.url,
            params={
                'id': self.id,
                'appid': self.app_id,
                'units': self.units
            }
        ).json()

    def get_info(self):
        r = self.get_response()

        r.update({
            'timestamp': r['dt'],
            'weather_main': r['weather'][0]['main'],
            'weather_description': r['weather'][0]['description'],
            'lon': r['coord']['lon'],
            'lat': r['coord']['lat'],
            'wind_speed': r['wind']['speed'],
            'wind_beaufort': OWM.ms_to_beaufort(float(r['wind']['speed'])),
            'wind_deg': r['wind']['deg'],
            'wind_direction': OWM.degree_to_description(float(r['wind']['deg'])),
            'country': r['sys']['country'],
            'sunrise': r['sys']['sunrise'],
            'sunset': r['sys']['sunset'],
            'clouds_all': r['clouds']['all'],
            'temp': r['main']['temp'],
            'feels_like': r['main']['feels_like'],
            'temp_min': r['main']['temp_min'],
            'temp_max': r['main']['temp_max'],
            'pressure': r['main']['pressure'],
            'humidity': r['main']['humidity']
        })

        r.pop('cod')
        r.pop('weather')
        r.pop('dt')
        r.pop('coord')
        r.pop('base')
        r.pop('wind')
        r.pop('sys')
        r.pop('main')
        r.pop('clouds')
        r.pop('id')

        return [r]

    @staticmethod
    # B = (W/0.836)^2/3
    def ms_to_beaufort(w: float):
        return round(pow(w / 0.836, 2 / 3))

    @staticmethod
    # W = 0.836B^3/2
    def beaufort_to_ms(b: float):
        return 0.836 * pow(b, 3 / 2)

    @staticmethod
    def degree_to_description(d: float):
        return {0: 'N', 1: 'NW', 2: 'W', 3: 'SW', 4: 'S', 5: 'SE', 6: 'E', 7: 'NE', }.get(int((d + 22.5) / 45) % 8)
