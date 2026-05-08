import customtkinter as ctk
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# -----------------------------
# Conversion Dictionary
# -----------------------------
conversions = {
    "Length": {
        "in → mm": lambda x: x * 25.4,
        "mm → in": lambda x: x / 25.4,
        "ft → m": lambda x: x * 0.3048,
        "m → ft": lambda x: x / 0.3048
    },
    "Weight": {
        "lb → kg": lambda x: x * 0.453592,
        "kg → lb": lambda x: x / 0.453592,
        "oz → g": lambda x: x * 28.3495,
        "g → oz": lambda x: x / 28.3495
    },
    "Pressure": {
        "psi → kPa": lambda x: x * 6.89476,
        "kPa → psi": lambda x: x / 6.89476,
        "bar → psi": lambda x: x * 14.5038,
        "psi → bar": lambda x: x / 14.5038
    },
    "Power": {
        "hp → kW": lambda x: x * 0.7457,
        "kW → hp": lambda x: x / 0.7457
    },
    "Torque": {
        "lb-ft → N-m": lambda x: x * 1.35582,
        "N-m → lb-ft": lambda x: x / 1.35582
    },
    "Temperature": {
        "°F → °C": lambda x: (x - 32) * 5 / 9,
        "°C → °F": lambda x: (x * 9 / 5) + 32
    },
    "Density": {
        "lb/ft³ → kg/m³": lambda x: x * 16.0185,
        "kg/m³ → lb/ft³": lambda x: x / 16.0185
    }
}

saved_weather_locations = []

state_lookup = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming"
}

# -----------------------------
# App Setup
# -----------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("800x480")
app.title("EDA - Engineering Dashboard Assistant")


def clear_screen():
    for widget in app.winfo_children():
        widget.destroy()


# -----------------------------
# Weather Helpers
# -----------------------------
def get_coordinates(city_name):
    original_search = city_name.strip()
    search_parts = [part.strip() for part in original_search.split(",")]

    city_search = search_parts[0]
    requested_state = None

    if len(search_parts) > 1:
        requested_state = search_parts[1].strip()
        if requested_state.upper() in state_lookup:
            requested_state = state_lookup[requested_state.upper()]

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {
        "name": city_search,
        "count": 10,
        "language": "en",
        "format": "json"
    }

    response = requests.get(geo_url, params=geo_params, timeout=10)
    data = response.json()

    if "results" not in data:
        return None

    results = data["results"]
    selected_place = results[0]

    if requested_state:
        for place in results:
            place_state = place.get("admin1", "")
            if place_state.lower() == requested_state.lower():
                selected_place = place
                break

    return {
        "name": selected_place.get("name", city_search),
        "state": selected_place.get("admin1", ""),
        "country": selected_place.get("country_code", ""),
        "latitude": selected_place["latitude"],
        "longitude": selected_place["longitude"],
        "timezone": selected_place.get("timezone", "auto")
    }


def get_weather(location):
    weather_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,precipitation",
        "hourly": "temperature_2m,precipitation_probability,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": location["timezone"],
        "forecast_days": 7
    }

    response = requests.get(weather_url, params=params, timeout=10)
    return response.json()


def location_display_name(location):
    parts = [location["name"]]

    if location["state"]:
        parts.append(location["state"])

    if location["country"]:
        parts.append(location["country"])

    return ", ".join(parts)


def city_local_time(location):
    try:
        timezone = location.get("timezone", "auto")

        if timezone == "auto":
            return "Local time unavailable"

        local_time = datetime.now(ZoneInfo(timezone))
        return local_time.strftime("%I:%M %p")

    except Exception:
        return "Local time unavailable"


# -----------------------------
# Main Dashboard
# -----------------------------
def show_main_screen():
    clear_screen()

    ctk.CTkLabel(app, text="EDA", font=("Arial", 42, "bold")).pack(pady=(30, 5))
    ctk.CTkLabel(app, text="Engineering Dashboard Assistant", font=("Arial", 18)).pack(pady=(0, 25))

    time_label = ctk.CTkLabel(app, text="", font=("Arial", 28))
    time_label.pack(pady=10)

    ctk.CTkLabel(app, text="System Status: Online", font=("Arial", 18)).pack(pady=10)

    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=25)

    ctk.CTkButton(button_frame, text="Units", width=160, command=show_units_screen).grid(row=0, column=0, padx=10, pady=10)
    ctk.CTkButton(button_frame, text="Weather", width=160, command=show_weather_screen).grid(row=0, column=1, padx=10, pady=10)
    ctk.CTkButton(button_frame, text="Timer", width=160, command=show_timer_screen).grid(row=0, column=2, padx=10, pady=10)

    def update_time():
        if time_label.winfo_exists():
            time_label.configure(text=datetime.now().strftime("%I:%M:%S %p"))
            app.after(1000, update_time)

    update_time()


# -----------------------------
# Unit Converter
# -----------------------------
def show_units_screen():
    clear_screen()

    ctk.CTkLabel(app, text="Unit Converter", font=("Arial", 32, "bold")).pack(pady=(25, 10))
    ctk.CTkLabel(app, text="Select Conversion Category", font=("Arial", 16)).pack(pady=(10, 5))

    category_dropdown = ctk.CTkOptionMenu(app, values=list(conversions.keys()))
    category_dropdown.pack(pady=5)

    ctk.CTkLabel(app, text="Select Conversion Type", font=("Arial", 16)).pack(pady=(15, 5))

    conversion_dropdown = ctk.CTkOptionMenu(app, values=list(conversions["Length"].keys()))
    conversion_dropdown.pack(pady=5)

    input_box = ctk.CTkEntry(app, placeholder_text="Enter value", width=250)
    input_box.pack(pady=15)

    result_label = ctk.CTkLabel(app, text="Result will appear here", font=("Arial", 18))
    result_label.pack(pady=10)

    def update_conversion_options(selected_category):
        options = list(conversions[selected_category].keys())
        conversion_dropdown.configure(values=options)
        conversion_dropdown.set(options[0])
        input_box.delete(0, "end")
        result_label.configure(text="Result will appear here")

    category_dropdown.configure(command=update_conversion_options)

    def convert_value():
        try:
            value = float(input_box.get())
            category = category_dropdown.get()
            conversion_type = conversion_dropdown.get()
            result = conversions[category][conversion_type](value)

            from_unit, to_unit = conversion_type.split(" → ")
            result_label.configure(text=f"{value:g} {from_unit} = {result:.3f} {to_unit}")

        except ValueError:
            result_label.configure(text="Please enter a valid number")

    def clear_converter():
        input_box.delete(0, "end")
        result_label.configure(text="Result will appear here")

    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=15)

    ctk.CTkButton(button_frame, text="Convert", width=120, command=convert_value).grid(row=0, column=0, padx=8)
    ctk.CTkButton(button_frame, text="Clear", width=120, command=clear_converter).grid(row=0, column=1, padx=8)
    ctk.CTkButton(button_frame, text="Back", width=120, command=show_main_screen).grid(row=0, column=2, padx=8)


# -----------------------------
# Weather Dashboard
# -----------------------------
def show_weather_screen():
    clear_screen()

    ctk.CTkLabel(app, text="Weather", font=("Arial", 32, "bold")).pack(pady=(15, 8))

    search_frame = ctk.CTkFrame(app)
    search_frame.pack(pady=5)

    city_entry = ctk.CTkEntry(search_frame, placeholder_text="Search city, ex: Auburn, AL", width=330)
    city_entry.grid(row=0, column=0, padx=8, pady=8)

    status_label = ctk.CTkLabel(app, text="", font=("Arial", 14))
    status_label.pack(pady=2)

    content_frame = ctk.CTkFrame(app)
    content_frame.pack(fill="both", expand=True, padx=20, pady=8)

    def refresh_weather_cards():
        for widget in content_frame.winfo_children():
            widget.destroy()

        if len(saved_weather_locations) == 0:
            ctk.CTkLabel(content_frame, text="Search for a city to add weather.", font=("Arial", 20)).pack(expand=True)
        elif len(saved_weather_locations) == 1:
            build_large_weather_view(content_frame, saved_weather_locations[0])
        else:
            build_weather_card_grid(content_frame)

    def add_city():
        city_name = city_entry.get().strip()

        if not city_name:
            status_label.configure(text="Enter a city first.")
            return

        status_label.configure(text="Searching...")

        try:
            location = get_coordinates(city_name)

            if location is None:
                status_label.configure(text="City not found.")
                return

            saved_weather_locations.append(location)
            city_entry.delete(0, "end")
            status_label.configure(text=f"Added {location_display_name(location)}")
            refresh_weather_cards()

        except Exception as error:
            status_label.configure(text=f"Weather error: {error}")

    ctk.CTkButton(search_frame, text="Add City", width=120, command=add_city).grid(row=0, column=1, padx=8, pady=8)
    ctk.CTkButton(search_frame, text="Back", width=100, command=show_main_screen).grid(row=0, column=2, padx=8, pady=8)

    refresh_weather_cards()


def build_weather_card_grid(parent):
    for index, location in enumerate(saved_weather_locations):
        try:
            data = get_weather(location)
            current = data["current"]

            card = ctk.CTkFrame(parent)
            card.grid(row=index // 2, column=index % 2, padx=12, pady=12, sticky="nsew")

            name = location_display_name(location)
            temp = current["temperature_2m"]
            feels = current["apparent_temperature"]
            humidity = current["relative_humidity_2m"]
            wind = current["wind_speed_10m"]

            ctk.CTkLabel(card, text=name, font=("Arial", 18, "bold")).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=f"Local Time: {city_local_time(location)}", font=("Arial", 13)).pack()
            ctk.CTkLabel(card, text=f"{temp:.0f}°F", font=("Arial", 36, "bold")).pack()
            ctk.CTkLabel(card, text=f"Feels {feels:.0f}°F | Humidity {humidity}% | Wind {wind:.0f} mph").pack(pady=4)

            ctk.CTkButton(card, text="Open", command=lambda loc=location: show_weather_detail_screen(loc)).pack(pady=(6, 10))

        except Exception:
            ctk.CTkLabel(parent, text="Could not load weather card.").pack(pady=10)


def build_large_weather_view(parent, location):
    try:
        data = get_weather(location)
        current = data["current"]

        name = location_display_name(location)
        temp = current["temperature_2m"]
        feels = current["apparent_temperature"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
        precip = current["precipitation"]

        ctk.CTkLabel(parent, text=name, font=("Arial", 24, "bold")).pack(pady=(8, 2))
        ctk.CTkLabel(parent, text=f"Local Time: {city_local_time(location)}", font=("Arial", 16)).pack()
        ctk.CTkLabel(parent, text=f"{temp:.0f}°F", font=("Arial", 54, "bold")).pack()
        ctk.CTkLabel(parent, text=f"Feels Like {feels:.0f}°F", font=("Arial", 18)).pack()
        ctk.CTkLabel(parent, text=f"Humidity: {humidity}%   Wind: {wind:.0f} mph   Rain: {precip:.2f} in", font=("Arial", 15)).pack(pady=5)

        ctk.CTkButton(parent, text="Open Full Forecast", width=180, command=lambda: show_weather_detail_screen(location)).pack(pady=8)

    except Exception as error:
        ctk.CTkLabel(parent, text=f"Could not load weather: {error}").pack(pady=20)


def show_weather_detail_screen(location):
    clear_screen()

    data = get_weather(location)
    current = data["current"]
    hourly = data["hourly"]
    daily = data["daily"]

    ctk.CTkLabel(app, text=location_display_name(location), font=("Arial", 28, "bold")).pack(pady=(12, 2))
    ctk.CTkLabel(app, text=f"Local Time: {city_local_time(location)}", font=("Arial", 16)).pack()
    ctk.CTkLabel(app, text=f"{current['temperature_2m']:.0f}°F | Feels {current['apparent_temperature']:.0f}°F", font=("Arial", 22)).pack()
    ctk.CTkLabel(app, text=f"Humidity {current['relative_humidity_2m']}% | Wind {current['wind_speed_10m']:.0f} mph", font=("Arial", 15)).pack(pady=(0, 8))

    tabview = ctk.CTkTabview(app, width=750, height=310)
    tabview.pack(pady=5)

    today_tab = tabview.add("Rest of Day")
    week_tab = tabview.add("7-Day")

    hourly_box = ctk.CTkScrollableFrame(today_tab, width=700, height=240)
    hourly_box.pack(padx=10, pady=10)

    city_now = datetime.now(ZoneInfo(location["timezone"]))

    shown = 0
    for time_text, temp, rain, wind in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        hourly["wind_speed_10m"]
    ):
        hour_dt = datetime.fromisoformat(time_text)

        if hour_dt.date() == city_now.date() and hour_dt.hour >= city_now.hour:
            row_text = f"{hour_dt.strftime('%I %p')}    {temp:.0f}°F    Rain {rain}%    Wind {wind:.0f} mph"
            ctk.CTkLabel(hourly_box, text=row_text, font=("Arial", 15)).pack(anchor="w", pady=3)
            shown += 1

    if shown == 0:
        ctk.CTkLabel(hourly_box, text="No more hourly data for today.").pack(pady=10)

    daily_box = ctk.CTkScrollableFrame(week_tab, width=700, height=240)
    daily_box.pack(padx=10, pady=10)

    for day, high, low, rain in zip(
        daily["time"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_probability_max"]
    ):
        day_name = datetime.fromisoformat(day).strftime("%a %m/%d")
        row_text = f"{day_name}    High {high:.0f}°F    Low {low:.0f}°F    Rain {rain}%"
        ctk.CTkLabel(daily_box, text=row_text, font=("Arial", 15)).pack(anchor="w", pady=4)

    bottom_frame = ctk.CTkFrame(app)
    bottom_frame.pack(pady=8)

    ctk.CTkButton(bottom_frame, text="Back to Weather", width=160, command=show_weather_screen).grid(row=0, column=0, padx=8)
    ctk.CTkButton(bottom_frame, text="Main Menu", width=160, command=show_main_screen).grid(row=0, column=1, padx=8)


# -----------------------------
# Timer Placeholder
# -----------------------------
# -----------------------------
# Timer Screen
# -----------------------------
def show_timer_screen():
    clear_screen()

    timer_running = {"active": False}
    remaining_time = {"seconds": 0}
    after_id = {"id": None}

    ctk.CTkLabel(app, text="Timer", font=("Arial", 32, "bold")).pack(pady=(35, 10))

    ctk.CTkLabel(
        app,
        text="Enter minutes and optional seconds",
        font=("Arial", 16)
    ).pack(pady=(0, 10))

    input_frame = ctk.CTkFrame(app)
    input_frame.pack(pady=10)

    minutes_entry = ctk.CTkEntry(input_frame, placeholder_text="Minutes", width=130)
    minutes_entry.grid(row=0, column=0, padx=10, pady=10)

    seconds_entry = ctk.CTkEntry(input_frame, placeholder_text="Seconds", width=130)
    seconds_entry.grid(row=0, column=1, padx=10, pady=10)

    timer_label = ctk.CTkLabel(app, text="00:00", font=("Arial", 60, "bold"))
    timer_label.pack(pady=20)

    status_label = ctk.CTkLabel(app, text="Ready", font=("Arial", 16))
    status_label.pack(pady=5)

    def format_time(total_seconds):
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def update_display():
        timer_label.configure(text=format_time(remaining_time["seconds"]))

    def tick():
        if timer_running["active"] and remaining_time["seconds"] > 0:
            remaining_time["seconds"] -= 1
            update_display()
            after_id["id"] = app.after(1000, tick)

        elif timer_running["active"] and remaining_time["seconds"] == 0:
            timer_running["active"] = False
            status_label.configure(text="Timer complete")

    def start_timer():
        try:
            minutes_text = minutes_entry.get().strip()
            seconds_text = seconds_entry.get().strip()

            minutes = int(minutes_text) if minutes_text else 0
            seconds = int(seconds_text) if seconds_text else 0

            if seconds >= 60:
                status_label.configure(text="Seconds must be less than 60")
                return

            total_seconds = minutes * 60 + seconds

            if total_seconds <= 0:
                status_label.configure(text="Enter a time greater than 0")
                return

            remaining_time["seconds"] = total_seconds
            timer_running["active"] = True
            update_display()
            status_label.configure(text="Running")
            tick()

        except ValueError:
            status_label.configure(text="Enter valid whole numbers")

    def pause_timer():
        timer_running["active"] = False
        status_label.configure(text="Paused")

    def reset_timer():
        timer_running["active"] = False
        remaining_time["seconds"] = 0
        update_display()
        status_label.configure(text="Ready")

    button_frame = ctk.CTkFrame(app)
    button_frame.pack(pady=15)

    ctk.CTkButton(button_frame, text="Start", width=120, command=start_timer).grid(row=0, column=0, padx=8)
    ctk.CTkButton(button_frame, text="Pause", width=120, command=pause_timer).grid(row=0, column=1, padx=8)
    ctk.CTkButton(button_frame, text="Reset", width=120, command=reset_timer).grid(row=0, column=2, padx=8)

    ctk.CTkButton(app, text="Back", width=140, command=show_main_screen).pack(pady=15)

# -----------------------------
# Start App
# -----------------------------
show_main_screen()
app.mainloop()