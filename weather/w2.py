import datetime
import os
import sys

# 外部ライブラリのインポートチェック
try:
    from geopy.geocoders import Nominatim
except ImportError:
    print("【エラー】'geopy' モジュールがインストールされていません。")
    print("以下のコマンドを実行してインストールしてください:\n  pip install geopy")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("【エラー】'requests' モジュールがインストールされていません。")
    print("以下のコマンドを実行してインストールしてください:\n  pip install requests")
    sys.exit(1)

def weather_code_to_japanese(code):
    """天気コードを日本語と絵文字に変換する関数"""
    weather = {
        0: ("☀️", "晴れ"),
        1: ("🌤️", "晴れ"),
        2: ("⛅", "晴れ時々曇り"),
        3: ("☁️", "曇り"),
        45: ("🌫️", "霧"),
        48: ("🌫️", "着氷性の霧"),
        51: ("🌧️", "弱い霧雨"),
        53: ("🌧️", "霧雨"),
        55: ("🌧️", "強い霧雨"),
        56: ("🌧️", "弱い着氷性霧雨"),
        57: ("🌧️", "強い着氷性霧雨"),
        61: ("☔", "弱い雨"),
        63: ("☔", "雨"),
        65: ("☔", "大雨"),
        66: ("☔", "弱い着氷性の雨"),
        67: ("☔", "強い着氷性の雨"),
        71: ("❄️", "弱い雪"),
        73: ("❄️", "雪"),
        75: ("❄️", "大雪"),
        77: ("❄️", "雪粒"),
        80: ("🌦️", "弱いにわか雨"),
        81: ("🌦️", "にわか雨"),
        82: ("🌧️", "激しいにわか雨"),
        85: ("🌨️", "弱いにわか雪"),
        86: ("🌨️", "激しいにわか雪"),
        95: ("⛈️", "雷雨"),
        96: ("⛈️", "雷雨（ひょう）"),
        99: ("⛈️", "激しい雷雨（ひょう）"),
    }
    return weather.get(code, ("❓", f"不明({code})"))


def wind_direction(degree):
    """風向の角度(0~360度)を16方位の日本語表記に変換する関数"""
    directions = [
        "北",
        "北北東",
        "北東",
        "東北東",
        "東",
        "東南東",
        "南東",
        "南南東",
        "南",
        "南南西",
        "南西",
        "西南西",
        "西",
        "西北西",
        "北西",
        "北北西",
    ]
    index = int((degree + 11.25) // 22.5) % 16
    return directions[index]


def format_time(iso_time_str):
    """ISO8601形式の時刻文字列から HH:MM を抽出"""
    if not iso_time_str:
        return "--:--"
    try:
        dt = datetime.datetime.fromisoformat(iso_time_str)
        return dt.strftime("%H:%M")
    except Exception:
        return "--:--"


def format_datetime(iso_time_str):
    """ISO8601形式の時刻文字列を YYYY/MM/DD HH:MM:SS 形式に変換"""
    if not iso_time_str:
        return "----/--/-- --:--:--"
    try:
        dt = datetime.datetime.fromisoformat(iso_time_str)
        return dt.strftime("%Y/%m/%d %H:%M:%S")
    except Exception:
        return "----/--/-- --:--:--"


def clear_screen():
    """画面（コンソール）をクリアする関数"""
    os.system("cls" if os.name == "nt" else "clear")


def main():
    address = input("住所を入力してください：")

    # Geocodingで緯度・経度を取得
    geolocator = Nominatim(user_agent="weather_app_takeo_v1")
    location = geolocator.geocode(address)

    if location is None:
        print("住所が見つかりませんでした。")
        return

    latitude = location.latitude
    longitude = location.longitude
    formatted_address = location.address  # ← ★追加：APIが判定した正式住所名を取得

    # Open-Meteo APIのURL構築
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current_weather=true"
        "&hourly=relative_humidity_2m,apparent_temperature,precipitation,surface_pressure,uv_index"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
        "&timezone=auto"
    )

    response = requests.get(url)
    data = response.json()

    current_weather = data.get("current_weather", {})
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})

    # 観測日時のフォーマット
    obs_time_raw = current_weather.get("time", "")
    obs_time_str = format_datetime(obs_time_raw)

    # hourly（時間ごとデータ）から補足データを取得
    humidity = hourly.get("relative_humidity_2m", [0])[0]
    apparent_temp = hourly.get("apparent_temperature", [0.0])[0]
    precipitation = hourly.get("precipitation", [0.0])[0]
    pressure = hourly.get("surface_pressure", [0])[0]
    uv = hourly.get("uv_index", [0.0])[0]

    # 天気コードとアイコンの取得
    emoji, weather_text = weather_code_to_japanese(
        current_weather.get("weathercode", 0)
    )

    # 日の出・日の入り時刻
    sunrise_list = daily.get("sunrise", [])
    sunset_list = daily.get("sunset", [])
    sunrise = format_time(sunrise_list[0]) if sunrise_list else "--:--"
    sunset = format_time(sunset_list[0]) if sunset_list else "--:--"

    # --- 画面をクリアして出力 ---
    """clear_screen()"""

    print(f"住所：{formatted_address}")
    print(f"現在の天気：{obs_time_str}")
    print()
    print(f"{emoji} {weather_text}")
    print(f"気温        {current_weather.get('temperature', 0.0):.1f}℃")
    print(f"体感温度    {apparent_temp:.1f}℃")
    print(f"湿度        {humidity}%")
    print(f"気圧        {int(pressure)}hPa")
    print(f"風速        {current_weather.get('windspeed', 0.0):.1f}km/h")
    print(
        f"風向        {wind_direction(current_weather.get('winddirection', 0))}"
    )
    print(f"降水量      {precipitation:.1f}mm")
    print(f"UV指数      {uv:.1f}")
    print()
    print(f"日の出      {sunrise}")
    print(f"日の入り    {sunset}")
    print()

    labels = ["今日", "明日", "明後日"]
    daily_codes = daily.get("weather_code", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    pops = daily.get("precipitation_probability_max", [])

    for i in range(min(3, len(daily_codes))):
        day_emoji, day_weather = weather_code_to_japanese(daily_codes[i])
        max_temp = round(max_temps[i]) if i < len(max_temps) else "--"
        min_temp = round(min_temps[i]) if i < len(min_temps) else "--"
        pop = pops[i] if i < len(pops) else "--"

        print(labels[i])
        print(f"{day_emoji} {day_weather}")
        print(f"最高 {max_temp}℃")
        print(f"最低 {min_temp}℃")
        print(f"降水確率 {pop}%")
        print()

    """print("--w2 Ver1.00 Copyright(C)2026 TAKEO")"""


if __name__ == "__main__":
    main()