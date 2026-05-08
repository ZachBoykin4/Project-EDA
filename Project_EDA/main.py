import customtkinter as ctk
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import threading

APP_WIDTH = 800
APP_HEIGHT = 480
FULLSCREEN = True
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


def clear_screen():
    for widget in app.winfo_children():
        widget.destroy()


def nav_button(parent, text, command):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=78,
        font=("Arial", 28, "bold"),
        corner_radius=20,
    )


def huge_button(parent, text, command):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=105,
        font=("Arial", 31, "bold"),
        corner_radius=24,
    )


def get_coordinates(city_name):
    search_parts = [part.strip() for part in city_name.strip().split(",")]
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
            idle_weather_data["temp"] = "--°F"
            idle_weather_data["feels"] = "FEELS --°F"
            idle_weather_data["humidity"] = "HUM --%"
            idle_weather_data["wind"] = "WIND -- MPH"

    threading.Thread(target=worker, daemon=True).start()


def show_idle_screen():
    clear_screen()

    idle_frame = ctk.CTkFrame(app, fg_color="#020202")
    idle_frame.pack(fill="both", expand=True)

    ctk.CTkLabel(
        idle_frame,
        text="ΚΑΨ",
        font=("Times New Roman", 96, "bold"),
        text_color="#E00000",
    ).place(relx=0.5, rely=0.095, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="KAPPA ALPHA PSI",
        font=("Times New Roman", 25, "bold"),
        text_color="#FFFFFF",
    ).place(relx=0.5, rely=0.205, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="FRATERNITY, INC.",
        font=("Arial", 15, "bold"),
        text_color="#E00000",
    ).place(relx=0.5, rely=0.265, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="19",
        font=("Times New Roman", 92, "bold"),
        text_color="#C00000",
    ).place(relx=0.13, rely=0.52, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="N I N E T E E N",
        font=("Arial", 15, "bold"),
        text_color="#FFFFFF",
    ).place(relx=0.13, rely=0.675, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="11",
        font=("Times New Roman", 92, "bold"),
        text_color="#C00000",
    ).place(relx=0.87, rely=0.52, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="E L E V E N",
        font=("Arial", 15, "bold"),
        text_color="#FFFFFF",
    ).place(relx=0.87, rely=0.675, anchor="center")

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
    pm_label.grid(row=0, column=1, sticky="s", pady=(0, 18))

    date_label = ctk.CTkLabel(
        idle_frame,
        text="",
        font=("Arial", 25, "bold"),
        text_color="#E00000",
    )
    date_label.place(relx=0.5, rely=0.685, anchor="center")

    ctk.CTkLabel(
        idle_frame,
        text="TAP ANYWHERE TO OPEN EDA",
        font=("Arial", 17, "bold"),
        text_color="#FFFFFF",
    ).place(relx=0.5, rely=0.805, anchor="center")

    weather_frame = ctk.CTkFrame(idle_frame, fg_color="transparent")
    weather_frame.place(relx=0.5, rely=0.902, anchor="center")

    city_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    temp_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 25, "bold"), text_color="#FFFFFF")
    feels_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    hum_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")
    wind_label = ctk.CTkLabel(weather_frame, text="", font=("Arial", 17, "bold"), text_color="#FFFFFF")

    city_label.grid(row=0, column=0, padx=10)
    temp_label.grid(row=0, column=1, padx=10)
    feels_label.grid(row=0, column=2, padx=10)
    hum_label.grid(row=0, column=3, padx=10)
    wind_label.grid(row=0, column=4, padx=10)

    ctk.CTkLabel(
        idle_frame,
        text="ACHIEVEMENT IN EVERY FIELD OF HUMAN ENDEAVOR",
        font=("Arial", 11, "bold"),
        text_color="#E00000",
    ).place(relx=0.5, rely=0.965, anchor="center")

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

    idle_frame.bind("<Button-1>", lambda event: show_main_screen())
    for child in idle_frame.winfo_children():
        child.bind("<Button-1>", lambda event: show_main_screen())

    update_idle_clock()


def show_main_screen():
    clear_screen()

    header = ctk.CTkFrame(app, fg_color="#080808", height=70)
    header.pack(fill="x")

    ctk.CTkLabel(header, text="EDA", font=("Arial", 34, "bold")).pack(pady=(7, 0))
    ctk.CTkLabel(header, text="Engineering Dashboard Assistant", font=("Arial", 13)).pack()

    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(fill="both", expand=True, padx=16, pady=12)

    buttons = [
        ("Units", show_units_screen),
        ("Weather", show_weather_screen),
        ("Timer", show_timer_screen),
        ("Notes", show_notes_screen),
        ("Back to Clock", show_idle_screen),
        ("Exit App", app.destroy),
    ]

    for i, (text, command) in enumerate(buttons):
        huge_button(button_frame, text, command).grid(
            row=i // 2,
            column=i % 2,
            sticky="nsew",
            padx=12,
            pady=9,
        )

    for col in range(2):
        button_frame.grid_columnconfigure(col, weight=1)
    for row in range(3):
        button_frame.grid_rowconfigure(row, weight=1)


def show_units_screen():
    clear_screen()

    container = ctk.CTkFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=18, pady=12)

    ctk.CTkLabel(container, text="Unit Converter", font=("Arial", 34, "bold")).pack(pady=(0, 8))

    category_dropdown = ctk.CTkOptionMenu(
        container,
        values=list(conversions.keys()),
        width=720,
        height=65,
        font=("Arial", 28),
    )
    category_dropdown.pack(pady=5)

    conversion_dropdown = ctk.CTkOptionMenu(
        container,
        values=list(conversions["Length"].keys()),
        width=720,
        height=65,
        font=("Arial", 28),
    )
    conversion_dropdown.pack(pady=5)

    input_box = ctk.CTkEntry(
        container,
        placeholder_text="Enter value",
        width=720,
        height=70,
        font=("Arial", 32),
    )
    input_box.pack(pady=8)

    result_label = ctk.CTkLabel(container, text="Result will appear here", font=("Arial", 26, "bold"))
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

    nav = ctk.CTkFrame(container, fg_color="transparent")
    nav.pack(fill="x", pady=6)

    nav_button(nav, "Convert", convert_value).grid(row=0, column=0, sticky="nsew", padx=6)
    nav_button(nav, "Clear", lambda: input_box.delete(0, "end")).grid(row=0, column=1, sticky="nsew", padx=6)
    nav_button(nav, "Back", show_main_screen).grid(row=0, column=2, sticky="nsew", padx=6)

    for i in range(3):
        nav.grid_columnconfigure(i, weight=1)


def show_weather_screen():
    clear_screen()

    container = ctk.CTkFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=16, pady=10)

    ctk.CTkLabel(container, text="Weather", font=("Arial", 34, "bold")).pack(pady=(0, 6))

    top = ctk.CTkFrame(container, fg_color="transparent")
    top.pack(fill="x", pady=4)

    city_entry = ctk.CTkEntry(top, placeholder_text="Auburn, AL", height=65, font=("Arial", 26))
    city_entry.grid(row=0, column=0, sticky="nsew", padx=6)

    status_label = ctk.CTkLabel(container, text="", font=("Arial", 18))
    status_label.pack(pady=2)

    content_frame = ctk.CTkFrame(container)
    content_frame.pack(fill="both", expand=True, pady=6)

    def refresh_weather_cards():
        for widget in content_frame.winfo_children():
            widget.destroy()

        if not saved_weather_locations:
            ctk.CTkLabel(content_frame, text="Search for a city to add weather.", font=("Arial", 28, "bold")).pack(expand=True)
        else:
            build_large_weather_view(content_frame, saved_weather_locations[-1])

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

    nav_button(top, "Add", add_city).grid(row=0, column=1, sticky="nsew", padx=6)
    nav_button(top, "Back", show_main_screen).grid(row=0, column=2, sticky="nsew", padx=6)

    top.grid_columnconfigure(0, weight=3)
    top.grid_columnconfigure(1, weight=1)
    top.grid_columnconfigure(2, weight=1)

    refresh_weather_cards()


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

        ctk.CTkLabel(parent, text=name, font=("Arial", 30, "bold")).pack(pady=(10, 2))
        ctk.CTkLabel(parent, text=f"{temp:.0f}°F", font=("Arial", 76, "bold")).pack(pady=2)
        ctk.CTkLabel(parent, text=f"Feels {feels:.0f}°F", font=("Arial", 26, "bold")).pack()
        ctk.CTkLabel(parent, text=f"Humidity {humidity}%   Wind {wind:.0f} mph   Rain {precip:.2f} in", font=("Arial", 22)).pack(pady=8)

    except Exception as error:
        ctk.CTkLabel(parent, text=f"Could not load weather: {error}", font=("Arial", 22)).pack(expand=True)


def show_timer_screen():
    clear_screen()

    container = ctk.CTkFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=16, pady=10)

    timer_running = {"active": False}
    remaining_time = {"seconds": 0}

    ctk.CTkLabel(container, text="Timer", font=("Arial", 36, "bold")).pack(pady=(0, 4))

    input_frame = ctk.CTkFrame(container, fg_color="transparent")
    input_frame.pack(fill="x", pady=5)

    minutes_entry = ctk.CTkEntry(input_frame, placeholder_text="Minutes", height=70, font=("Arial", 30))
    seconds_entry = ctk.CTkEntry(input_frame, placeholder_text="Seconds", height=70, font=("Arial", 30))

    minutes_entry.grid(row=0, column=0, sticky="nsew", padx=8)
    seconds_entry.grid(row=0, column=1, sticky="nsew", padx=8)

    input_frame.grid_columnconfigure(0, weight=1)
    input_frame.grid_columnconfigure(1, weight=1)

    timer_label = ctk.CTkLabel(container, text="00:00", font=("Arial", 98, "bold"))
    timer_label.pack(pady=4)

    status_label = ctk.CTkLabel(container, text="Ready", font=("Arial", 22, "bold"))
    status_label.pack(pady=2)

    def format_time(total_seconds):
        return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

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
            minutes = int(minutes_entry.get().strip()) if minutes_entry.get().strip() else 0
            seconds = int(seconds_entry.get().strip()) if seconds_entry.get().strip() else 0

            if seconds >= 60:
                status_label.configure(text="Seconds must be less than 60")
                return

            total_seconds = minutes * 60 + seconds

            if total_seconds <= 0:
                status_label.configure(text="Enter time > 0")
                return

            remaining_time["seconds"] = total_seconds
            timer_running["active"] = True
            update_display()
            status_label.configure(text="Running")
            tick()

        except ValueError:
            status_label.configure(text="Enter whole numbers")

    controls = ctk.CTkFrame(container, fg_color="transparent")
    controls.pack(fill="x", pady=6)

    nav_button(controls, "Start", start_timer).grid(row=0, column=0, sticky="nsew", padx=6)
    nav_button(controls, "Pause", lambda: [timer_running.update({"active": False}), status_label.configure(text="Paused")]).grid(row=0, column=1, sticky="nsew", padx=6)
    nav_button(controls, "Reset", lambda: [timer_running.update({"active": False}), remaining_time.update({"seconds": 0}), update_display(), status_label.configure(text="Ready")]).grid(row=0, column=2, sticky="nsew", padx=6)

    nav = ctk.CTkFrame(container, fg_color="transparent")
    nav.pack(fill="x", pady=6)

    nav_button(nav, "Back", show_main_screen).grid(row=0, column=0, sticky="nsew", padx=6)
    nav_button(nav, "Clock", show_idle_screen).grid(row=0, column=1, sticky="nsew", padx=6)

    for frame, cols in [(controls, 3), (nav, 2)]:
        for i in range(cols):
            frame.grid_columnconfigure(i, weight=1)


def show_notes_screen():
    clear_screen()

    container = ctk.CTkFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=16, pady=10)

    ctk.CTkLabel(container, text="Quick Notes", font=("Arial", 36, "bold")).pack(pady=(0, 5))

    notes_box = ctk.CTkTextbox(container, height=255, font=("Arial", 25))
    notes_box.pack(fill="both", expand=True, pady=6)

    try:
        with open("notes.txt", "r") as file:
            notes_box.insert("0.0", file.read())
    except FileNotFoundError:
        notes_box.insert("0.0", "Project EDA notes...\n")

    status_label = ctk.CTkLabel(container, text="", font=("Arial", 18))
    status_label.pack(pady=2)

    def save_notes():
        with open("notes.txt", "w") as file:
            file.write(notes_box.get("0.0", "end"))
        status_label.configure(text="Notes saved")

    nav = ctk.CTkFrame(container, fg_color="transparent")
    nav.pack(fill="x", pady=5)

    nav_button(nav, "Save", save_notes).grid(row=0, column=0, sticky="nsew", padx=6)
    nav_button(nav, "Back", show_main_screen).grid(row=0, column=1, sticky="nsew", padx=6)
    nav_button(nav, "Clock", show_idle_screen).grid(row=0, column=2, sticky="nsew", padx=6)

    for i in range(3):
        nav.grid_columnconfigure(i, weight=1)


load_idle_weather()
show_idle_screen()
app.mainloop()