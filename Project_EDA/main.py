import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import threading
import subprocess

DEFAULT_WEATHER_CITY = "Auburn, AL"
DIM_AFTER_MS = 5 * 60 * 1000

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(1.15)
ctk.set_window_scaling(1.0)

app = ctk.CTk()
app.title("EDA - Engineering Dashboard Assistant")

SCREEN_W = app.winfo_screenwidth()
SCREEN_H = app.winfo_screenheight()
app.geometry(f"{SCREEN_W}x{SCREEN_H}+0+0")


def force_fullscreen():
    app.geometry(f"{SCREEN_W}x{SCREEN_H}+0+0")
    app.attributes("-fullscreen", True)
    app.lift()
    app.focus_force()


app.after(200, force_fullscreen)
app.bind("<Escape>", lambda e: app.destroy())
app.bind("<F11>", lambda e: force_fullscreen())

saved_weather_locations = []
active_screen = {"name": "clock"}
is_dimmed = {"value": False}
dim_job = {"id": None}

global_timer = {
    "running": False,
    "seconds": 0,
    "input": "",
    "job": None,
    "alert_shown": False,
    "alarm_process": None,
}

idle_weather_data = {
    "city": "AUBURN, ALABAMA",
    "temp": "--°F",
    "feels": "FEELS --°F",
    "humidity": "HUM --%",
    "wind": "WIND -- MPH",
}

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
    "AL": "Alabama", "FL": "Florida", "GA": "Georgia", "TX": "Texas",
    "NC": "North Carolina", "SC": "South Carolina", "TN": "Tennessee",
    "NY": "New York", "CA": "California", "MI": "Michigan",
    "OH": "Ohio", "IL": "Illinois", "PA": "Pennsylvania",
}


def clear_screen():
    for widget in app.winfo_children():
        widget.destroy()


def cancel_dim_timer():
    if dim_job["id"] is not None:
        try:
            app.after_cancel(dim_job["id"])
        except Exception:
            pass
        dim_job["id"] = None


def reset_dim_timer():
    cancel_dim_timer()
    is_dimmed["value"] = False
    dim_job["id"] = app.after(DIM_AFTER_MS, dim_idle_screen)


def dim_idle_screen():
    if active_screen["name"] == "clock":
        is_dimmed["value"] = True
        show_idle_screen(dimmed=True)


def full_button(parent, text, command, size=28):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        font=("Arial", size, "bold"),
        corner_radius=22,
        border_width=0,
    )


def keypad_button(parent, text, command, size=26):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        font=("Arial", size, "bold"),
        corner_radius=16,
        border_width=0,
    )


def format_timer_time(total_seconds):
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def play_timer_alarm():
    if not global_timer["alert_shown"]:
        return

    try:
        global_timer["alarm_process"] = subprocess.Popen([
            "aplay",
            "/home/zachboykin4/Downloads/A Dream.wav"
        ])
    except Exception as error:
        print(f"Alarm sound failed: {error}")
        try:
            app.bell()
        except Exception:
            pass

    app.after(2500, play_timer_alarm)


def background_timer_tick():
    if global_timer["running"] and global_timer["seconds"] > 0:
        global_timer["seconds"] -= 1
        global_timer["job"] = app.after(1000, background_timer_tick)

    elif global_timer["running"] and global_timer["seconds"] == 0:
        global_timer["running"] = False
        global_timer["job"] = None

        if not global_timer["alert_shown"]:
            global_timer["alert_shown"] = True
            play_timer_alarm()
            show_timer_alert_screen()

    else:
        global_timer["job"] = None


def start_background_timer():
    if global_timer["job"] is None:
        global_timer["job"] = app.after(1000, background_timer_tick)


def get_coordinates(city_name):
    search_parts = [part.strip() for part in city_name.strip().split(",")]
    city_search = search_parts[0]
    requested_state = None

    if len(search_parts) > 1:
        requested_state = search_parts[1].strip()
        if requested_state.upper() in state_lookup:
            requested_state = state_lookup[requested_state.upper()]

    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city_search, "count": 10, "language": "en", "format": "json"},
        timeout=10,
    )
    data = response.json()

    if "results" not in data:
        return None

    selected_place = data["results"][0]

    if requested_state:
        for place in data["results"]:
            if place.get("admin1", "").lower() == requested_state.lower():
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
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
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
        },
        timeout=10,
    )
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
        return datetime.now(ZoneInfo(timezone)).strftime("%I:%M %p")
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

    threading.Thread(target=worker, daemon=True).start()


def show_idle_screen(dimmed=False):
    active_screen["name"] = "clock"
    clear_screen()

    bg = "#000000" if dimmed else "#020202"
    white = "#404040" if dimmed else "#FFFFFF"
    red = "#230000" if dimmed else "#E00000"
    side_red = "#170000" if dimmed else "#C00000"

    idle_frame = ctk.CTkFrame(app, fg_color=bg)
    idle_frame.pack(fill="both", expand=True)

    ctk.CTkLabel(idle_frame, text="ΚΑΨ", font=("Times New Roman", 96, "bold"), text_color=red).place(relx=0.5, rely=0.095, anchor="center")
    ctk.CTkLabel(idle_frame, text="KAPPA ALPHA PSI", font=("Times New Roman", 25, "bold"), text_color=white).place(relx=0.5, rely=0.205, anchor="center")
    ctk.CTkLabel(idle_frame, text="FRATERNITY, INC.", font=("Arial", 15, "bold"), text_color=red).place(relx=0.5, rely=0.265, anchor="center")

    ctk.CTkLabel(idle_frame, text="19", font=("Times New Roman", 92, "bold"), text_color=side_red).place(relx=0.13, rely=0.52, anchor="center")
    ctk.CTkLabel(idle_frame, text="N I N E T E E N", font=("Arial", 15, "bold"), text_color=white).place(relx=0.13, rely=0.675, anchor="center")

    ctk.CTkLabel(idle_frame, text="11", font=("Times New Roman", 92, "bold"), text_color=side_red).place(relx=0.87, rely=0.52, anchor="center")
    ctk.CTkLabel(idle_frame, text="E L E V E N", font=("Arial", 15, "bold"), text_color=white).place(relx=0.87, rely=0.675, anchor="center")

    clock_frame = ctk.CTkFrame(idle_frame, fg_color="transparent")
    clock_frame.place(relx=0.5, rely=0.50, anchor="center")

    time_label = ctk.CTkLabel(clock_frame, text="", font=("Arial", 138, "bold"), text_color=white)
    time_label.grid(row=0, column=0, padx=(0, 8))

    pm_label = ctk.CTkLabel(clock_frame, text="", font=("Arial", 42, "bold"), text_color=white)
    pm_label.grid(row=0, column=1, sticky="s", pady=(0, 18))

    date_label = ctk.CTkLabel(idle_frame, text="", font=("Arial", 25, "bold"), text_color=red)
    date_label.place(relx=0.5, rely=0.685, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="TAP TO WAKE" if dimmed else "TAP ANYWHERE TO OPEN EDA",
        font=("Arial", 17, "bold"),
        text_color=white,
    ).place(relx=0.5, rely=0.805, anchor="center")

    weather_frame = ctk.CTkFrame(idle_frame, fg_color="transparent")
    weather_frame.place(relx=0.5, rely=0.902, anchor="center")

    city_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color=white)
    temp_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 25, "bold"), text_color=white)
    feels_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color=white)
    hum_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color=white)
    wind_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color=white)

    city_label.grid(row=0, column=0, padx=10)
    temp_label.grid(row=0, column=1, padx=10)
    feels_label.grid(row=0, column=2, padx=10)
    hum_label.grid(row=0, column=3, padx=10)
    wind_label.grid(row=0, column=4, padx=10)

    ctk.CTkLabel(
        idle_frame,
        text="ACHIEVEMENT IN EVERY FIELD OF HUMAN ENDEAVOR",
        font=("Arial", 11, "bold"),
        text_color=red,
    ).place(relx=0.5, rely=0.965, anchor="center")

    def update_idle_clock():
        if active_screen["name"] != "clock" or not time_label.winfo_exists():
            return

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

    def wake_or_open(event=None):
        if is_dimmed["value"]:
            is_dimmed["value"] = False
            show_idle_screen(dimmed=False)
        else:
            cancel_dim_timer()
            show_main_screen()

    idle_frame.bind("<Button-1>", wake_or_open)
    for child in idle_frame.winfo_children():
        child.bind("<Button-1>", wake_or_open)

    update_idle_clock()

    if not dimmed:
        reset_dim_timer()


def show_main_screen():
    active_screen["name"] = "main"
    cancel_dim_timer()
    clear_screen()

    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

    ctk.CTkLabel(frame, text="EDA", font=("Arial", 42, "bold")).grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 4))
    ctk.CTkLabel(frame, text="Engineering Dashboard Assistant", font=("Arial", 18)).grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

    timer_text = "Timer"
    if global_timer["running"]:
        timer_text = f"Timer ({format_timer_time(global_timer['seconds'])})"

    buttons = [
        ("Units", show_units_screen),
        ("Weather", show_weather_screen),
        (timer_text, show_timer_screen),
        ("Notes", show_notes_screen),
        ("Back to Clock", show_idle_screen),
        ("Exit App", app.destroy),
    ]

    for i, (text, command) in enumerate(buttons):
        row = 2 + i // 2
        col = i % 2
        full_button(frame, text, command, 31).grid(row=row, column=col, sticky="nsew", padx=10, pady=8)

    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_rowconfigure(1, weight=1)
    for r in range(2, 5):
        frame.grid_rowconfigure(r, weight=3)


def show_units_screen():
    active_screen["name"] = "units"
    clear_screen()

    state = {
        "input": "",
        "category": "Length",
        "conversion": list(conversions["Length"].keys())[0],
    }

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(frame, text="Unit Converter", font=("Arial", 34, "bold")).grid(row=0, column=0, columnspan=4, sticky="nsew")

    display = ctk.CTkLabel(frame, text="0", font=("Arial", 44, "bold"), fg_color="#1F2937", corner_radius=18)
    display.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)

    result_label = ctk.CTkLabel(frame, text="Result will appear here", font=("Arial", 24, "bold"))
    result_label.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=4)

    selector_frame = ctk.CTkFrame(frame, fg_color="transparent")
    selector_frame.grid(row=3, column=0, columnspan=4, sticky="nsew")

    category_buttons = {}
    conversion_buttons = {}

    category_frame = ctk.CTkFrame(selector_frame)
    category_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    conversion_frame = ctk.CTkFrame(selector_frame)
    conversion_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    selector_frame.grid_columnconfigure(0, weight=1)
    selector_frame.grid_columnconfigure(1, weight=1)
    selector_frame.grid_rowconfigure(0, weight=1)

    def update_display():
        display.configure(text=state["input"] if state["input"] else "0")

    def set_category(category):
        state["category"] = category
        state["conversion"] = list(conversions[category].keys())[0]
        build_conversion_buttons()
        result_label.configure(text="Result will appear here")

        for cat, btn in category_buttons.items():
            btn.configure(fg_color="#1f6aa5" if cat == category else "#2b2b2b")

    def set_conversion(conversion):
        state["conversion"] = conversion
        result_label.configure(text="Result will appear here")

        for conv, btn in conversion_buttons.items():
            btn.configure(fg_color="#1f6aa5" if conv == conversion else "#2b2b2b")

    def build_category_buttons():
        for widget in category_frame.winfo_children():
            widget.destroy()

        cats = list(conversions.keys())
        category_buttons.clear()

        for i, cat in enumerate(cats):
            btn = keypad_button(category_frame, cat, lambda c=cat: set_category(c), size=22)
            btn.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
            category_buttons[cat] = btn

        for r in range(4):
            category_frame.grid_rowconfigure(r, weight=1)
        for c in range(2):
            category_frame.grid_columnconfigure(c, weight=1)

    def build_conversion_buttons():
        for widget in conversion_frame.winfo_children():
            widget.destroy()

        opts = list(conversions[state["category"]].keys())
        conversion_buttons.clear()

        for i, conv in enumerate(opts):
            btn = keypad_button(conversion_frame, conv, lambda cv=conv: set_conversion(cv), size=26)
            btn.grid(row=i, column=0, sticky="nsew", padx=5, pady=5)
            conversion_buttons[conv] = btn

        for r in range(max(1, len(opts))):
            conversion_frame.grid_rowconfigure(r, weight=1)
        conversion_frame.grid_columnconfigure(0, weight=1)

        set_conversion(state["conversion"])

    def press_key(key):
        if key == "⌫":
            state["input"] = state["input"][:-1]
        elif key == "Clear":
            state["input"] = ""
            result_label.configure(text="Result will appear here")
        elif key == ".":
            if "." not in state["input"]:
                state["input"] += "."
        else:
            state["input"] += key

        update_display()

    def convert_value():
        try:
            value = float(state["input"])
            category = state["category"]
            conversion_type = state["conversion"]
            result = conversions[category][conversion_type](value)
            from_unit, to_unit = conversion_type.split(" → ")
            result_label.configure(text=f"{value:g} {from_unit} = {result:.3f} {to_unit}")
        except ValueError:
            result_label.configure(text="Enter a valid number")

    keypad = ctk.CTkFrame(frame, fg_color="transparent")
    keypad.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(4, 0))

    keys = [
        ("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("⌫", 0, 3),
        ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("Clear", 1, 3),
        ("1", 2, 0), ("2", 2, 1), ("3", 2, 2), ("Convert", 2, 3),
        ("0", 3, 0), (".", 3, 1), ("Back", 3, 2), ("Main", 3, 3),
    ]

    for text, r, c in keys:
        if text == "Convert":
            cmd = convert_value
        elif text in ["Back", "Main"]:
            cmd = show_main_screen
        else:
            cmd = lambda k=text: press_key(k)

        keypad_button(keypad, text, cmd, size=24).grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

    for r in range(4):
        keypad.grid_rowconfigure(r, weight=1)
    for c in range(4):
        keypad.grid_columnconfigure(c, weight=1)

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_rowconfigure(3, weight=4)
    frame.grid_rowconfigure(4, weight=4)

    for c in range(4):
        frame.grid_columnconfigure(c, weight=1)

    build_category_buttons()
    build_conversion_buttons()
    set_category("Length")


def show_weather_screen():
    active_screen["name"] = "weather"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=14, pady=14)

    ctk.CTkLabel(frame, text="Weather", font=("Arial", 36, "bold")).pack(fill="x", pady=(0, 6))

    preset_frame = ctk.CTkFrame(frame, fg_color="transparent")
    preset_frame.pack(fill="x", pady=4)

    status_label = ctk.CTkLabel(frame, text="", font=("Arial", 20, "bold"))
    status_label.pack(fill="x", pady=2)

    content = ctk.CTkScrollableFrame(frame)
    content.pack(fill="both", expand=True, pady=6)

    preset_cities = ["Auburn, AL", "Orlando, FL", "Dallas, TX", "Charlotte, NC"]

    def refresh_weather_cards():
        for widget in content.winfo_children():
            widget.destroy()

        if not saved_weather_locations:
            ctk.CTkLabel(content, text="Tap a preset city to add weather.", font=("Arial", 30, "bold")).pack(expand=True, pady=80)
            return

        for idx, location in enumerate(saved_weather_locations):
            build_weather_card(content, location, idx)

    def add_city_by_name(city_name):
        status_label.configure(text=f"Adding {city_name}...")

        def worker():
            try:
                location = get_coordinates(city_name)

                if location is None:
                    app.after(0, lambda: status_label.configure(text="City not found."))
                    return

                saved_weather_locations.append(location)
                app.after(0, lambda: status_label.configure(text=f"Added {location_display_name(location)}"))
                app.after(0, refresh_weather_cards)

            except Exception as error:
                app.after(0, lambda: status_label.configure(text=f"Weather error: {error}"))

        threading.Thread(target=worker, daemon=True).start()

    for i, city in enumerate(preset_cities):
        full_button(preset_frame, city, lambda c=city: add_city_by_name(c), 20).grid(row=0, column=i, sticky="nsew", padx=4, pady=4)
        preset_frame.grid_columnconfigure(i, weight=1)

    nav = ctk.CTkFrame(frame, fg_color="transparent")
    nav.pack(fill="x", pady=4)

    full_button(nav, "Back", show_main_screen, 24).grid(row=0, column=0, sticky="nsew", padx=5)
    full_button(nav, "Clock", show_idle_screen, 24).grid(row=0, column=1, sticky="nsew", padx=5)

    nav.grid_columnconfigure(0, weight=1)
    nav.grid_columnconfigure(1, weight=1)

    refresh_weather_cards()


def build_weather_card(parent, location, idx):
    card = ctk.CTkFrame(parent)
    card.pack(fill="x", padx=8, pady=8)

    loading = ctk.CTkLabel(card, text=f"Loading {location_display_name(location)}...", font=("Arial", 24, "bold"))
    loading.pack(pady=25)

    def worker():
        try:
            data = get_weather(location)
            current = data["current"]

            def update_card():
                if not card.winfo_exists():
                    return

                for widget in card.winfo_children():
                    widget.destroy()

                ctk.CTkLabel(card, text=location_display_name(location), font=("Arial", 28, "bold")).pack(pady=(10, 2))
                ctk.CTkLabel(card, text=f"{current['temperature_2m']:.0f}°F | Feels {current['apparent_temperature']:.0f}°F", font=("Arial", 34, "bold")).pack()
                ctk.CTkLabel(card, text=f"Humidity {current['relative_humidity_2m']}% | Wind {current['wind_speed_10m']:.0f} mph | Local {city_local_time(location)}", font=("Arial", 20)).pack(pady=4)

                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=8)

                full_button(row, "Open Forecast", lambda loc=location: show_weather_detail_screen(loc), 24).grid(row=0, column=0, sticky="nsew", padx=6, pady=5)
                full_button(row, "Remove", lambda i=idx: remove_weather_city(i), 24).grid(row=0, column=1, sticky="nsew", padx=6, pady=5)

                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=1)

            app.after(0, update_card)

        except Exception:
            app.after(0, lambda: loading.configure(text="Could not load weather card."))

    threading.Thread(target=worker, daemon=True).start()


def remove_weather_city(index):
    try:
        saved_weather_locations.pop(index)
    except IndexError:
        pass
    show_weather_screen()


def show_weather_detail_screen(location):
    active_screen["name"] = "weather_detail"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=14, pady=10)

    ctk.CTkLabel(frame, text=location_display_name(location), font=("Arial", 30, "bold")).pack(fill="x")

    top_info = ctk.CTkLabel(frame, text="Loading forecast...", font=("Arial", 22, "bold"))
    top_info.pack(fill="x", pady=4)

    area = ctk.CTkFrame(frame)
    area.pack(fill="both", expand=True, pady=4)

    nav = ctk.CTkFrame(frame, fg_color="transparent")
    nav.pack(fill="x", pady=4)

    full_button(nav, "Back", show_weather_screen, 25).grid(row=0, column=0, sticky="nsew", padx=5)
    full_button(nav, "Main", show_main_screen, 25).grid(row=0, column=1, sticky="nsew", padx=5)
    full_button(nav, "Clock", show_idle_screen, 25).grid(row=0, column=2, sticky="nsew", padx=5)

    for i in range(3):
        nav.grid_columnconfigure(i, weight=1)

    def worker():
        try:
            data = get_weather(location)
            current = data["current"]
            hourly = data["hourly"]
            daily = data["daily"]

            def update_detail():
                if not area.winfo_exists():
                    return

                top_info.configure(
                    text=f"{current['temperature_2m']:.0f}°F | Feels {current['apparent_temperature']:.0f}°F | Humidity {current['relative_humidity_2m']}% | Wind {current['wind_speed_10m']:.0f} mph"
                )

                for widget in area.winfo_children():
                    widget.destroy()

                tabview = ctk.CTkTabview(area)
                tabview.pack(fill="both", expand=True, padx=5, pady=5)

                today_tab = tabview.add("Rest of Day")
                week_tab = tabview.add("7-Day")

                hourly_box = ctk.CTkScrollableFrame(today_tab)
                hourly_box.pack(fill="both", expand=True, padx=8, pady=8)

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
                        row_text = f"{hour_dt.strftime('%I %p')}   {temp:.0f}°F   Rain {rain}%   Wind {wind:.0f} mph"
                        ctk.CTkLabel(hourly_box, text=row_text, font=("Arial", 23, "bold")).pack(anchor="w", pady=5)
                        shown += 1

                if shown == 0:
                    ctk.CTkLabel(hourly_box, text="No more hourly data for today.", font=("Arial", 23)).pack(pady=10)

                daily_box = ctk.CTkScrollableFrame(week_tab)
                daily_box.pack(fill="both", expand=True, padx=8, pady=8)

                for day, high, low, rain in zip(
                    daily["time"],
                    daily["temperature_2m_max"],
                    daily["temperature_2m_min"],
                    daily["precipitation_probability_max"],
                ):
                    day_name = datetime.fromisoformat(day).strftime("%a %m/%d")
                    row_text = f"{day_name}   High {high:.0f}°F   Low {low:.0f}°F   Rain {rain}%"
                    ctk.CTkLabel(daily_box, text=row_text, font=("Arial", 23, "bold")).pack(anchor="w", pady=6)

            app.after(0, update_detail)

        except Exception as error:
            app.after(0, lambda: top_info.configure(text=f"Could not load forecast: {error}"))

    threading.Thread(target=worker, daemon=True).start()


def show_timer_alert_screen():
    active_screen["name"] = "timer_alert"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="#050505")
    frame.pack(fill="both", expand=True)

    alert_label = ctk.CTkLabel(
        frame,
        text="TIMER COMPLETE",
        font=("Arial", 72, "bold"),
        text_color="#FF3333",
    )
    alert_label.pack(expand=True)

    sub_label = ctk.CTkLabel(
        frame,
        text="Tap dismiss to stop alarm",
        font=("Arial", 28, "bold"),
        text_color="white",
    )
    sub_label.pack(pady=10)

    def dismiss_alert():
        global_timer["alert_shown"] = False
        global_timer["seconds"] = 0
        global_timer["input"] = ""
        global_timer["running"] = False

        if global_timer.get("alarm_process") is not None:
            try:
                global_timer["alarm_process"].terminate()
            except Exception:
                pass
            global_timer["alarm_process"] = None

        try:
            subprocess.Popen(["pkill", "-f", "aplay"])
        except Exception:
            pass

        show_main_screen()

    full_button(frame, "Dismiss", dismiss_alert, 36).pack(fill="x", padx=40, pady=35)

    flashing = {"on": True}

    def flash():
        if active_screen["name"] != "timer_alert":
            return

        flashing["on"] = not flashing["on"]
        alert_label.configure(text_color="#FF3333" if flashing["on"] else "#FFFFFF")
        app.after(500, flash)

    flash()


def show_timer_screen():
    active_screen["name"] = "timer"
    clear_screen()

    state = global_timer

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(frame, text="Timer", font=("Arial", 36, "bold")).grid(row=0, column=0, columnspan=4, sticky="nsew")

    timer_label = ctk.CTkLabel(frame, text=format_timer_time(state["seconds"]), font=("Arial", 92, "bold"))
    timer_label.grid(row=1, column=0, columnspan=4, sticky="nsew")

    status_label = ctk.CTkLabel(frame, text="Running" if state["running"] else "Enter minutes using keypad", font=("Arial", 22, "bold"))
    status_label.grid(row=2, column=0, columnspan=4, sticky="nsew")

    def update_timer_display():
        if state["input"] and not state["running"]:
            timer_label.configure(text=state["input"])
        else:
            timer_label.configure(text=format_timer_time(state["seconds"]))

    def refresh_timer_screen():
        if active_screen["name"] != "timer":
            return

        update_timer_display()

        if state["running"]:
            status_label.configure(text="Running")
        elif state["seconds"] == 0 and not state["input"]:
            status_label.configure(text="Ready")
        else:
            status_label.configure(text="Paused / Ready")

        app.after(300, refresh_timer_screen)

    def press_key(key):
        if state["running"]:
            return

        if key == "⌫":
            state["input"] = state["input"][:-1]
        elif key == "Clear":
            state["input"] = ""
            state["seconds"] = 0
            status_label.configure(text="Ready")
        elif key == ":":
            if ":" not in state["input"]:
                state["input"] += ":"
        else:
            state["input"] += key

        update_timer_display()

    def parse_timer_input():
        text = state["input"].strip()

        if not text:
            return 0

        if ":" in text:
            parts = text.split(":")
            minutes = int(parts[0]) if parts[0] else 0
            seconds = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        else:
            minutes = int(text)
            seconds = 0

        if seconds >= 60:
            raise ValueError

        return minutes * 60 + seconds

    def start_timer():
        try:
            if not state["running"]:
                if state["seconds"] <= 0:
                    state["seconds"] = parse_timer_input()

                if state["seconds"] <= 0:
                    status_label.configure(text="Enter time > 0")
                    return

                state["running"] = True
                state["input"] = ""
                state["alert_shown"] = False
                status_label.configure(text="Running")
                update_timer_display()
                start_background_timer()

        except ValueError:
            status_label.configure(text="Invalid time")

    def pause_timer():
        state["running"] = False
        status_label.configure(text="Paused")

    def reset_timer():
        state["running"] = False
        state["seconds"] = 0
        state["input"] = ""
        state["alert_shown"] = False
        status_label.configure(text="Ready")
        update_timer_display()

    keys = [
        ("7", 3, 0), ("8", 3, 1), ("9", 3, 2), ("Start", 3, 3),
        ("4", 4, 0), ("5", 4, 1), ("6", 4, 2), ("Pause", 4, 3),
        ("1", 5, 0), ("2", 5, 1), ("3", 5, 2), ("Reset", 5, 3),
        ("0", 6, 0), (":", 6, 1), ("⌫", 6, 2), ("Back", 6, 3),
    ]

    for text, r, c in keys:
        if text == "Start":
            cmd = start_timer
        elif text == "Pause":
            cmd = pause_timer
        elif text == "Reset":
            cmd = reset_timer
        elif text == "Back":
            cmd = show_main_screen
        else:
            cmd = lambda k=text: press_key(k)

        keypad_button(frame, text, cmd, size=24).grid(row=r, column=c, sticky="nsew", padx=5, pady=5)

    for r in range(7):
        frame.grid_rowconfigure(r, weight=1)
    frame.grid_rowconfigure(1, weight=2)

    for c in range(4):
        frame.grid_columnconfigure(c, weight=1)

    update_timer_display()
    refresh_timer_screen()


def show_notes_screen():
    active_screen["name"] = "notes"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    ctk.CTkLabel(frame, text="EDA Log Notes", font=("Arial", 30, "bold")).grid(
        row=0, column=0, columnspan=10, sticky="nsew", pady=(0, 3)
    )

    notes_box = tk.Text(
        frame,
        font=("Arial", 19, "bold"),
        bg="#1F2937",
        fg="white",
        insertbackground="white",
        relief="flat",
        wrap="word",
    )
    notes_box.grid(row=1, column=0, columnspan=10, sticky="nsew", padx=5, pady=5)

    def new_template():
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        return (
            f"[{timestamp}] EDA LOG\n"
            f"PROJECT UPDATE:\n- \n\n"
            f"TO-DO:\n- \n\n"
            f"IDEA:\n- \n\n"
            f"BUG / ISSUE:\n- \n\n"
            f"NOTES:\n- \n"
            f"----------------------------------------\n\n"
        )

    try:
        with open("notes.txt", "r") as file:
            existing_notes = file.read()
            if existing_notes.strip():
                notes_box.insert("1.0", existing_notes)
            else:
                notes_box.insert("1.0", new_template())
    except FileNotFoundError:
        notes_box.insert("1.0", new_template())

    status_label = ctk.CTkLabel(frame, text="", font=("Arial", 15, "bold"))
    status_label.grid(row=2, column=0, columnspan=10, sticky="nsew")

    def insert_text(text):
        notes_box.insert("insert", text)
        notes_box.see("insert")

    def save_notes():
        with open("notes.txt", "w") as file:
            file.write(notes_box.get("1.0", "end"))

        notes_box.insert("end", "\n" + new_template())
        notes_box.see("end")
        status_label.configure(text="Saved. New template added.")

    def clear_notes():
        notes_box.delete("1.0", "end")
        notes_box.insert("1.0", new_template())
        status_label.configure(text="Template reset.")

    def delete_char():
        try:
            notes_box.delete("insert-1c", "insert")
        except Exception:
            pass

    control_frame = ctk.CTkFrame(frame, fg_color="transparent")
    control_frame.grid(row=3, column=0, columnspan=10, sticky="nsew", pady=3)

    controls = [
        ("Save + New", save_notes),
        ("Reset", clear_notes),
        ("Back", show_main_screen),
        ("Clock", show_idle_screen),
    ]

    for i, (text, cmd) in enumerate(controls):
        keypad_button(control_frame, text, cmd, size=20).grid(
            row=0, column=i, sticky="nsew", padx=4, pady=4
        )
        control_frame.grid_columnconfigure(i, weight=1)

    control_frame.grid_rowconfigure(0, weight=1)

    keyboard_frame = ctk.CTkFrame(frame, fg_color="transparent")
    keyboard_frame.grid(row=4, column=0, columnspan=10, sticky="nsew", pady=(3, 0))

    keyboard_rows = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
    ]

    for r, letters in enumerate(keyboard_rows):
        offset = 0 if r < 2 else 1

        for c, letter in enumerate(letters):
            keypad_button(
                keyboard_frame,
                letter,
                lambda l=letter: insert_text(l.lower()),
                size=22
            ).grid(
                row=r,
                column=c + offset,
                sticky="nsew",
                padx=3,
                pady=3
            )

    keypad_button(keyboard_frame, "SPACE", lambda: insert_text(" "), size=21).grid(
        row=3, column=0, columnspan=3, sticky="nsew", padx=3, pady=3
    )

    keypad_button(keyboard_frame, "ENTER", lambda: insert_text("\n"), size=21).grid(
        row=3, column=3, columnspan=2, sticky="nsew", padx=3, pady=3
    )

    keypad_button(keyboard_frame, "⌫", delete_char, size=21).grid(
        row=3, column=5, columnspan=2, sticky="nsew", padx=3, pady=3
    )

    keypad_button(keyboard_frame, ".", lambda: insert_text("."), size=21).grid(
        row=3, column=7, sticky="nsew", padx=3, pady=3
    )

    keypad_button(keyboard_frame, "-", lambda: insert_text("-"), size=21).grid(
        row=3, column=8, sticky="nsew", padx=3, pady=3
    )

    keypad_button(keyboard_frame, ",", lambda: insert_text(","), size=21).grid(
        row=3, column=9, sticky="nsew", padx=3, pady=3
    )

    for r in range(4):
        keyboard_frame.grid_rowconfigure(r, weight=1)

    for c in range(10):
        keyboard_frame.grid_columnconfigure(c, weight=1)

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_rowconfigure(1, weight=7)
    frame.grid_rowconfigure(2, weight=1)
    frame.grid_rowconfigure(3, weight=2)
    frame.grid_rowconfigure(4, weight=5)

    for c in range(10):
        frame.grid_columnconfigure(c, weight=1)


load_idle_weather()
show_idle_screen()
app.mainloop()