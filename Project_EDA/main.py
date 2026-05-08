import customtkinter as ctk
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import threading

# ============================================================
# EDA - Engineering Dashboard Assistant
# ============================================================

APP_WIDTH = 800
APP_HEIGHT = 480
FULLSCREEN = True  # Mac test = False. Raspberry Pi = True.

DEFAULT_WEATHER_CITY = "Auburn, AL"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
app.title("EDA - Engineering Dashboard Assistant")

if FULLSCREEN:
    app.attributes("-fullscreen", True)

app.bind("<Escape>", lambda e: app.attributes("-fullscreen", False))

saved_weather_locations = []
idle_weather_data = {
    "city": "AUBURN, ALABAMA",
    "temp": "--°F",
    "feels": "FEELS --°F",
    "humidity": "HUM --%",
    "wind": "WIND -- MPH",
}

# ============================================================
# Conversions
# ============================================================

conversions = {
    "Length": {
        "in → mm": lambda x: x * 25.4,
        "mm → in": lambda x: x / 25.4,
        "ft → m": lambda x: x * 0.3048,
        "m → ft": lambda x: x / 0.3048,
    },
    "Weight": {
        "lb → kg": lambda x: x * 0.453592,
        "kg → lb": lambda x: x / 0.453592,
        "oz → g": lambda x: x * 28.3495,
        "g → oz": lambda x: x / 28.3495,
    },
    "Pressure": {
        "psi → kPa": lambda x: x * 6.89476,
        "kPa → psi": lambda x: x / 6.89476,
        "bar → psi": lambda x: x * 14.5038,
        "psi → bar": lambda x: x / 14.5038,
    },
    "Power": {
        "hp → kW": lambda x: x * 0.7457,
        "kW → hp": lambda x: x / 0.7457,
    },
    "Torque": {
        "lb-ft → N-m": lambda x: x * 1.35582,
        "N-m → lb-ft": lambda x: x / 1.35582,
    },
    "Temperature": {
        "°F → °C": lambda x: (x - 32) * 5 / 9,
        "°C → °F": lambda x: (x * 9 / 5) + 32,
    },
    "Density": {
        "lb/ft³ → kg/m³": lambda x: x * 16.0185,
        "kg/m³ → lb/ft³": lambda x: x / 16.0185,
    },
}

state_lookup = {
    "AL": "Alabama",
    "FL": "Florida",
    "GA": "Georgia",
    "TX": "Texas",
    "NC": "North Carolina",
    "SC": "South Carolina",
    "TN": "Tennessee",
    "NY": "New York",
    "CA": "California",
}

# ============================================================
# Helpers
# ============================================================

def clear_screen():
    for widget in app.winfo_children():
        widget.destroy()


def big_button(parent, text, command, width=320, height=105, font_size=30):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        font=("Arial", font_size, "bold"),
        corner_radius=22,
    )


def show_loading(message="Loading EDA..."):
    clear_screen()

    frame = ctk.CTkFrame(app, corner_radius=28, fg_color="#090909")
    frame.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        frame,
        text="EDA",
        font=("Arial", 72, "bold"),
        text_color="white",
    ).pack(padx=70, pady=(35, 0))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Arial", 22, "bold"),
        text_color="#E00000",
    ).pack(pady=(5, 18))

    bar = ctk.CTkProgressBar(frame, width=430)
    bar.pack(pady=(0, 35))
    bar.set(0)

    def animate(value=0):
        if value <= 1 and bar.winfo_exists():
            bar.set(value)
            app.after(20, lambda: animate(value + 0.035))

    animate()


# ============================================================
# Weather Logic
# ============================================================

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
        "format": "json",
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
        "timezone": selected_place.get("timezone", "auto"),
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
        "forecast_days": 7,
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


def load_idle_weather():
    def worker():
        try:
            location = get_coordinates(DEFAULT_WEATHER_CITY)
            if location is None:
                return

            data = get_weather(location)
            current = data["current"]

            city = location["name"].upper()
            state = location["state"].upper() if location["state"] else ""

            idle_weather_data["city"] = f"{city}, {state}"
            idle_weather_data["temp"] = f"{current['temperature_2m']:.0f}°F"
            idle_weather_data["feels"] = f"FEELS {current['apparent_temperature']:.0f}°F"
            idle_weather_data["humidity"] = f"HUM {current['relative_humidity_2m']}%"
            idle_weather_data["wind"] = f"WIND {current['wind_speed_10m']:.0f} MPH"

        except Exception:
            idle_weather_data["city"] = "WEATHER UNAVAILABLE"
            idle_weather_data["temp"] = "--°F"
            idle_weather_data["feels"] = "FEELS --°F"
            idle_weather_data["humidity"] = "HUM --%"
            idle_weather_data["wind"] = "WIND -- MPH"

    threading.Thread(target=worker, daemon=True).start()


# ============================================================
# Standby Screen
# ============================================================

def show_idle_screen():
    clear_screen()

    idle_frame = ctk.CTkFrame(app, fg_color="#020202")
    idle_frame.pack(fill="both", expand=True)

    greek_label = ctk.CTkLabel(
        idle_frame,
        text="ΚΑΨ",
        font=("Times New Roman", 96, "bold"),
        text_color="#E00000",
    )
    greek_label.place(relx=0.5, rely=0.095, anchor="center")

    kappa_label = ctk.CTkLabel(
        idle_frame,
        text="KAPPA ALPHA PSI",
        font=("Times New Roman", 25, "bold"),
        text_color="#FFFFFF",
    )
    kappa_label.place(relx=0.5, rely=0.205, anchor="center")

    fraternity_label = ctk.CTkLabel(
        idle_frame,
        text="FRATERNITY, INC.",
        font=("Arial", 15, "bold"),
        text_color="#E00000",
    )
    fraternity_label.place(relx=0.5, rely=0.265, anchor="center")

    diamond_top = ctk.CTkLabel(
        idle_frame,
        text="◆",
        font=("Arial", 20, "bold"),
        text_color="#E00000",
    )
    diamond_top.place(relx=0.5, rely=0.315, anchor="center")

    left_19 = ctk.CTkLabel(
        idle_frame,
        text="19",
        font=("Times New Roman", 92, "bold"),
        text_color="#C00000",
    )
    left_19.place(relx=0.13, rely=0.52, anchor="center")

    left_word = ctk.CTkLabel(
        idle_frame,
        text="N I N E T E E N",
        font=("Arial", 15, "bold"),
        text_color="#FFFFFF",
    )
    left_word.place(relx=0.13, rely=0.675, anchor="center")

    right_11 = ctk.CTkLabel(
        idle_frame,
        text="11",
        font=("Times New Roman", 92, "bold"),
        text_color="#C00000",
    )
    right_11.place(relx=0.87, rely=0.52, anchor="center")

    right_word = ctk.CTkLabel(
        idle_frame,
        text="E L E V E N",
        font=("Arial", 15, "bold"),
        text_color="#FFFFFF",
    )
    right_word.place(relx=0.87, rely=0.675, anchor="center")

    clock_frame = ctk.CTkFrame(idle_frame, fg_color="transparent")
    clock_frame.place(relx=0.5, rely=0.50, anchor="center")

    time_label = ctk.CTkLabel(
        clock_frame,
        text="",
        font=("Arial", 138, "bold"),
        text_color="#FFFFFF",
    )
    time_label.grid(row=0, column=0, padx=(0, 8))

    pm_label = ctk.CTkLabel(
        clock_frame,
        text="",
        font=("Arial", 42, "bold"),
        text_color="#FFFFFF",
    )
    pm_label.grid(row=0, column=1, sticky="s", padx=(0, 0), pady=(0, 18))

    date_label = ctk.CTkLabel(
        idle_frame,
        text="",
        font=("Arial", 25, "bold"),
        text_color="#E00000",
    )
    date_label.place(relx=0.5, rely=0.685, anchor="center")

    divider_left = ctk.CTkFrame(idle_frame, height=2, width=170, fg_color="#AA0000")
    divider_left.place(relx=0.36, rely=0.755, anchor="center")

    diamond_mid = ctk.CTkLabel(
        idle_frame,
        text="◆",
        font=("Arial", 17, "bold"),
        text_color="#E00000",
    )
    diamond_mid.place(relx=0.5, rely=0.755, anchor="center")

    divider_right = ctk.CTkFrame(idle_frame, height=2, width=170, fg_color="#AA0000")
    divider_right.place(relx=0.64, rely=0.755, anchor="center")

    tap_label = ctk.CTkLabel(
        idle_frame,
        text="TAP ANYWHERE TO OPEN EDA",
        font=("Arial", 17, "bold"),
        text_color="#FFFFFF",
    )
    tap_label.place(relx=0.5, rely=0.805, anchor="center")

    weather_top = ctk.CTkFrame(idle_frame, height=2, width=610, fg_color="#AA0000")
    weather_top.place(relx=0.5, rely=0.86, anchor="center")

    weather_frame = ctk.CTkFrame(idle_frame, fg_color="transparent")
    weather_frame.place(relx=0.5, rely=0.902, anchor="center")

    city_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    city_label.grid(row=0, column=0, padx=10)

    temp_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 25, "bold"), text_color="#FFFFFF")
    temp_label.grid(row=0, column=1, padx=10)

    feels_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    feels_label.grid(row=0, column=2, padx=10)

    hum_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    hum_label.grid(row=0, column=3, padx=10)

    wind_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    wind_label.grid(row=0, column=4, padx=10)

    footer_label = ctk.CTkLabel(
        idle_frame,
        text="ACHIEVEMENT IN EVERY FIELD OF HUMAN ENDEAVOR",
        font=("Arial", 11, "bold"),
        text_color="#E00000",
    )
    footer_label.place(relx=0.5, rely=0.965, anchor="center")

    def update_idle_clock():
        if time_label.winfo_exists():
            now = datetime.now()
            time_label.configure(text=now.strftime("%I:%M").lstrip("0"))
            pm_label.configure(text=now.strftime("%p"))
            date_label.configure(text=now.strftime("%A, %B %d").upper())

            city_label.configure(text=idle_weather_data["city"])
            temp_label.configure(text=idle_weather_data["temp"])
            feels_label.configure(text=idle_weather_data["feels"])
            hum_label.configure(text=idle_weather_data["humidity"])
            wind_label.configure(text=idle_weather_data["wind"])

            app.after(1000, update_idle_clock)

    def open_dashboard(event=None):
        show_loading("Opening dashboard...")
        app.after(500, show_main_screen)

    for widget in [
        idle_frame, greek_label, kappa_label, fraternity_label, diamond_top,
        left_19, left_word, right_11, right_word, clock_frame, time_label,
        pm_label, date_label, tap_label, diamond_mid, weather_frame,
        city_label, temp_label, feels_label, hum_label, wind_label, footer_label,
    ]:
        widget.bind("<Button-1>", open_dashboard)

    update_idle_clock()


# ============================================================
# Main Dashboard
# ============================================================

def show_main_screen():
    clear_screen()

    header = ctk.CTkFrame(app, fg_color="#080808", height=78)
    header.pack(fill="x")

    ctk.CTkLabel(
        header,
        text="EDA",
        font=("Arial", 38, "bold"),
        text_color="white",
    ).pack(pady=(8, 0))

    ctk.CTkLabel(
        header,
        text="Engineering Dashboard Assistant",
        font=("Arial", 14),
        text_color="#AAAAAA",
    ).pack()

    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(fill="both", expand=True, padx=18, pady=14)

    buttons = [
        ("Units", show_units_screen),
        ("Weather", show_weather_screen),
        ("Timer", show_timer_screen),
        ("Notes", show_notes_screen),
        ("Clock", show_idle_screen),
        ("Back", show_idle_screen),
        ("Close", app.destroy),
    ]

    for i, (text, command) in enumerate(buttons):
        btn = big_button(button_frame, text, command, width=350, height=105, font_size=30)
        btn.grid(row=i // 2, column=i % 2, padx=14, pady=10, sticky="nsew")

    for col in range(2):
        button_frame.grid_columnconfigure(col, weight=1)

    for row in range(3):
        button_frame.grid_rowconfigure(row, weight=1)


# ============================================================
# Unit Converter
# ============================================================

def show_units_screen():
    clear_screen()

    ctk.CTkLabel(app, text="Unit Converter", font=("Arial", 34, "bold")).pack(pady=(10, 6))

    category_dropdown = ctk.CTkOptionMenu(
        app,
        values=list(conversions.keys()),
        width=500,
        height=62,
        font=("Arial", 28),
    )
    category_dropdown.pack(pady=5)

    conversion_dropdown = ctk.CTkOptionMenu(
        app,
        values=list(conversions["Length"].keys()),
        width=500,
        height=62,
        font=("Arial", 28),
    )
    conversion_dropdown.pack(pady=5)

    input_box = ctk.CTkEntry(
        app,
        placeholder_text="Enter value",
        width=500,
        height=68,
        font=("Arial", 30),
    )
    input_box.pack(pady=8)

    result_label = ctk.CTkLabel(app, text="Result will appear here", font=("Arial", 25))
    result_label.pack(pady=5)

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

    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(pady=8)

    big_button(button_frame, "Convert", convert_value, 240, 70, 24).grid(row=0, column=0, padx=7)
    big_button(button_frame, "Clear", lambda: input_box.delete(0, "end"), 240, 70, 24).grid(row=0, column=1, padx=7)
    big_button(button_frame, "Back", show_main_screen, 240, 70, 24).grid(row=0, column=2, padx=7)


# ============================================================
# Weather Dashboard
# ============================================================

def show_weather_screen():
    clear_screen()

    ctk.CTkLabel(app, text="Weather", font=("Arial", 34, "bold")).pack(pady=(10, 5))

    search_frame = ctk.CTkFrame(app, fg_color="transparent")
    search_frame.pack(pady=5)

    city_entry = ctk.CTkEntry(
        search_frame,
        placeholder_text="Auburn, AL",
        width=430,
        height=60,
        font=("Arial", 24),
    )
    city_entry.grid(row=0, column=0, padx=8, pady=8)

    status_label = ctk.CTkLabel(app, text="", font=("Arial", 18))
    status_label.pack(pady=2)

    content_frame = ctk.CTkFrame(app)
    content_frame.pack(fill="both", expand=True, padx=18, pady=8)

    def refresh_weather_cards():
        for widget in content_frame.winfo_children():
            widget.destroy()

        if len(saved_weather_locations) == 0:
            ctk.CTkLabel(
                content_frame,
                text="Search for a city to add weather.",
                font=("Arial", 24, "bold"),
            ).pack(expand=True)
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

        def worker():
            try:
                location = get_coordinates(city_name)

                if location is None:
                    app.after(0, lambda: status_label.configure(text="City not found."))
                    return

                saved_weather_locations.append(location)
                app.after(0, lambda: city_entry.delete(0, "end"))
                app.after(0, lambda: status_label.configure(text=f"Added {location_display_name(location)}"))
                app.after(0, refresh_weather_cards)

            except Exception as error:
                app.after(0, lambda: status_label.configure(text=f"Weather error: {error}"))

        threading.Thread(target=worker, daemon=True).start()

    big_button(search_frame, "Add", add_city, 145, 60, 22).grid(row=0, column=1, padx=8, pady=8)
    big_button(search_frame, "Back", show_main_screen, 145, 60, 22).grid(row=0, column=2, padx=8, pady=8)

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

            ctk.CTkLabel(card, text=name, font=("Arial", 20, "bold")).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=f"Local Time: {city_local_time(location)}", font=("Arial", 15)).pack()
            ctk.CTkLabel(card, text=f"{temp:.0f}°F", font=("Arial", 42, "bold")).pack()
            ctk.CTkLabel(card, text=f"Feels {feels:.0f}°F | Humidity {humidity}% | Wind {wind:.0f} mph").pack(pady=4)
            big_button(card, "Open", lambda loc=location: show_weather_detail_screen(loc), 200, 60, 22).pack(pady=(6, 10))

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

        ctk.CTkLabel(parent, text=name, font=("Arial", 26, "bold")).pack(pady=(8, 2))
        ctk.CTkLabel(parent, text=f"Local Time: {city_local_time(location)}", font=("Arial", 18)).pack()
        ctk.CTkLabel(parent, text=f"{temp:.0f}°F", font=("Arial", 56, "bold")).pack()
        ctk.CTkLabel(parent, text=f"Feels Like {feels:.0f}°F", font=("Arial", 20)).pack()
        ctk.CTkLabel(
            parent,
            text=f"Humidity: {humidity}%   Wind: {wind:.0f} mph   Rain: {precip:.2f} in",
            font=("Arial", 17),
        ).pack(pady=5)

        big_button(
            parent,
            "Open Forecast",
            lambda: show_weather_detail_screen(location),
            310,
            65,
            24,
        ).pack(pady=8)

    except Exception as error:
        ctk.CTkLabel(parent, text=f"Could not load weather: {error}").pack(pady=20)


def show_weather_detail_screen(location):
    clear_screen()

    data = get_weather(location)
    current = data["current"]
    hourly = data["hourly"]
    daily = data["daily"]

    ctk.CTkLabel(app, text=location_display_name(location), font=("Arial", 28, "bold")).pack(pady=(8, 2))
    ctk.CTkLabel(app, text=f"{current['temperature_2m']:.0f}°F | Feels {current['apparent_temperature']:.0f}°F", font=("Arial", 22)).pack()
    ctk.CTkLabel(app, text=f"Humidity {current['relative_humidity_2m']}% | Wind {current['wind_speed_10m']:.0f} mph", font=("Arial", 16)).pack(pady=(0, 4))

    tabview = ctk.CTkTabview(app, width=750, height=285)
    tabview.pack(pady=3)

    today_tab = tabview.add("Rest of Day")
    week_tab = tabview.add("7-Day")

    hourly_box = ctk.CTkScrollableFrame(today_tab, width=700, height=210)
    hourly_box.pack(padx=10, pady=8)

    city_now = datetime.now(ZoneInfo(location["timezone"]))

    shown = 0
    for time_text, temp, rain, wind in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        hourly["wind_speed_10m"],
    ):
        hour_dt = datetime.fromisoformat(time_text)

        if hour_dt.date() == city_now.date() and hour_dt.hour >= city_now.hour:
            row_text = f"{hour_dt.strftime('%I %p')}    {temp:.0f}°F    Rain {rain}%    Wind {wind:.0f} mph"
            ctk.CTkLabel(hourly_box, text=row_text, font=("Arial", 17)).pack(anchor="w", pady=3)
            shown += 1

    if shown == 0:
        ctk.CTkLabel(hourly_box, text="No more hourly data for today.").pack(pady=10)

    daily_box = ctk.CTkScrollableFrame(week_tab, width=700, height=210)
    daily_box.pack(padx=10, pady=8)

    for day, high, low, rain in zip(
        daily["time"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_probability_max"],
    ):
        day_name = datetime.fromisoformat(day).strftime("%a %m/%d")
        row_text = f"{day_name}    High {high:.0f}°F    Low {low:.0f}°F    Rain {rain}%"
        ctk.CTkLabel(daily_box, text=row_text, font=("Arial", 17)).pack(anchor="w", pady=4)

    bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
    bottom_frame.pack(pady=5)

    big_button(bottom_frame, "Back", show_weather_screen, 230, 60, 22).grid(row=0, column=0, padx=8)
    big_button(bottom_frame, "Main Menu", show_main_screen, 230, 60, 22).grid(row=0, column=1, padx=8)
    big_button(bottom_frame, "Clock", show_idle_screen, 230, 60, 22).grid(row=0, column=2, padx=8)


# ============================================================
# Timer
# ============================================================

def show_timer_screen():
    clear_screen()

    timer_running = {"active": False}
    remaining_time = {"seconds": 0}

    ctk.CTkLabel(app, text="Timer", font=("Arial", 36, "bold")).pack(pady=(10, 4))

    input_frame = ctk.CTkFrame(app, fg_color="transparent")
    input_frame.pack(pady=6)

    minutes_entry = ctk.CTkEntry(input_frame, placeholder_text="Minutes", width=230, height=65, font=("Arial", 28))
    minutes_entry.grid(row=0, column=0, padx=10, pady=8)

    seconds_entry = ctk.CTkEntry(input_frame, placeholder_text="Seconds", width=230, height=65, font=("Arial", 28))
    seconds_entry.grid(row=0, column=1, padx=10, pady=8)

    timer_label = ctk.CTkLabel(app, text="00:00", font=("Arial", 90, "bold"))
    timer_label.pack(pady=4)

    status_label = ctk.CTkLabel(app, text="Ready", font=("Arial", 20))
    status_label.pack(pady=2)

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
            app.after(1000, tick)
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

    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(pady=6)

    big_button(button_frame, "Start", start_timer, 180, 65, 24).grid(row=0, column=0, padx=8)
    big_button(button_frame, "Pause", pause_timer, 180, 65, 24).grid(row=0, column=1, padx=8)
    big_button(button_frame, "Reset", reset_timer, 180, 65, 24).grid(row=0, column=2, padx=8)

    bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
    bottom_frame.pack(pady=5)

    big_button(bottom_frame, "Back", show_main_screen, 230, 60, 22).grid(row=0, column=0, padx=8)
    big_button(bottom_frame, "Clock", show_idle_screen, 230, 60, 22).grid(row=0, column=1, padx=8)


# ============================================================
# Notes
# ============================================================

def show_notes_screen():
    clear_screen()

    ctk.CTkLabel(app, text="Quick Notes", font=("Arial", 36, "bold")).pack(pady=(10, 5))

    notes_box = ctk.CTkTextbox(app, width=720, height=270, font=("Arial", 23))
    notes_box.pack(pady=6)

    try:
        with open("notes.txt", "r") as file:
            notes_box.insert("0.0", file.read())
    except FileNotFoundError:
        notes_box.insert("0.0", "Project EDA notes...\n")

    status_label = ctk.CTkLabel(app, text="", font=("Arial", 16))
    status_label.pack(pady=2)

    def save_notes():
        with open("notes.txt", "w") as file:
            file.write(notes_box.get("0.0", "end"))
        status_label.configure(text="Notes saved")

    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(pady=5)

    big_button(button_frame, "Save", save_notes, 220, 65, 24).grid(row=0, column=0, padx=8)
    big_button(button_frame, "Back", show_main_screen, 220, 65, 24).grid(row=0, column=1, padx=8)
    big_button(button_frame, "Clock", show_idle_screen, 220, 65, 24).grid(row=0, column=2, padx=8)


# ============================================================
# Start App
# ============================================================

load_idle_weather()
show_loading("Booting dashboard...")
app.after(900, show_idle_screen)
app.mainloop()