import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import threading

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


app.after(200, force_fullscreen)
app.bind("<Escape>", lambda e: app.destroy())
app.bind("<F11>", lambda e: force_fullscreen())

saved_weather_locations = []
active_screen = {"name": "clock"}
is_dimmed = {"value": False}
dim_job = {"id": None}

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
    "MI": "Michigan",
    "OH": "Ohio",
    "IL": "Illinois",
    "PA": "Pennsylvania",
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

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(frame, text="EDA", font=("Arial", 42, "bold")).grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 4))
    ctk.CTkLabel(frame, text="Engineering Dashboard Assistant", font=("Arial", 18)).grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

    buttons = [
        ("Units", show_units_screen),
        ("Weather", show_weather_screen),
        ("Timer", show_timer_screen),
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

    frame = ctk.CTkFrame(app, fg_color="#111111")
    frame.pack(fill="both", expand=True, padx=14, pady=14)

    ctk.CTkLabel(
        frame,
        text="Unit Converter",
        font=("Arial", 38, "bold"),
        text_color="white"
    ).pack(fill="x", pady=(0, 12))

    category_var = tk.StringVar(value="Length")
    conversion_var = tk.StringVar(value=list(conversions["Length"].keys())[0])

    ctk.CTkLabel(
        frame,
        text="Category",
        font=("Arial", 22, "bold"),
        text_color="white"
    ).pack(fill="x", padx=8, pady=(4, 2))

    def update_conversion_options(selected_category=None):
        category = category_var.get()
        options = list(conversions[category].keys())

        conversion_dropdown.configure(values=options)
        conversion_var.set(options[0])

        input_box.delete(0, "end")
        result_label.configure(text="Result will appear here")

    category_dropdown = ctk.CTkOptionMenu(
        frame,
        variable=category_var,
        values=list(conversions.keys()),
        command=update_conversion_options,
        height=82,
        font=("Arial", 30, "bold"),
        dropdown_font=("Arial", 28, "bold"),
        corner_radius=22,
        fg_color="#1E88E5",
        button_color="#1565C0",
        button_hover_color="#0D47A1",
        dropdown_fg_color="#1E1E1E",
        dropdown_hover_color="#1E88E5",
        dropdown_text_color="white",
    )
    category_dropdown.pack(fill="x", padx=8, pady=(0, 14))

    ctk.CTkLabel(
        frame,
        text="Conversion",
        font=("Arial", 22, "bold"),
        text_color="white"
    ).pack(fill="x", padx=8, pady=(4, 2))

    conversion_dropdown = ctk.CTkOptionMenu(
        frame,
        variable=conversion_var,
        values=list(conversions["Length"].keys()),
        height=82,
        font=("Arial", 30, "bold"),
        dropdown_font=("Arial", 28, "bold"),
        corner_radius=22,
        fg_color="#1E88E5",
        button_color="#1565C0",
        button_hover_color="#0D47A1",
        dropdown_fg_color="#1E1E1E",
        dropdown_hover_color="#1E88E5",
        dropdown_text_color="white",
    )
    conversion_dropdown.pack(fill="x", padx=8, pady=(0, 16))

    input_box = ctk.CTkEntry(
        frame,
        placeholder_text="Enter value",
        height=84,
        font=("Arial", 34, "bold"),
        justify="center"
    )
    input_box.pack(fill="x", padx=8, pady=(0, 14))

    result_label = ctk.CTkLabel(
        frame,
        text="Result will appear here",
        font=("Arial", 26, "bold"),
        text_color="white"
    )
    result_label.pack(fill="x", pady=(0, 10))

    def convert_value():
        try:
            value = float(input_box.get())
            category = category_var.get()
            conversion_type = conversion_var.get()

            result = conversions[category][conversion_type](value)
            from_unit, to_unit = conversion_type.split(" → ")

            result_label.configure(text=f"{value:g} {from_unit} = {result:.3f} {to_unit}")

        except Exception:
            result_label.configure(text="Please enter a valid number")

    def clear_value():
        input_box.delete(0, "end")
        result_label.configure(text="Result will appear here")

    button_frame = ctk.CTkFrame(frame, fg_color="transparent")
    button_frame.pack(fill="both", expand=True, pady=(8, 0))

    full_button(button_frame, "Convert", convert_value, 30).grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    full_button(button_frame, "Clear", clear_value, 30).grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
    full_button(button_frame, "Back", show_main_screen, 30).grid(row=0, column=2, sticky="nsew", padx=6, pady=6)

    for c in range(3):
        button_frame.grid_columnconfigure(c, weight=1)

    button_frame.grid_rowconfigure(0, weight=1)


def show_weather_screen():
    active_screen["name"] = "weather"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=14, pady=14)

    ctk.CTkLabel(frame, text="Weather", font=("Arial", 36, "bold")).pack(fill="x", pady=(0, 6))

    top = ctk.CTkFrame(frame, fg_color="transparent")
    top.pack(fill="x", pady=4)

    city_entry = ctk.CTkEntry(top, placeholder_text="Auburn, AL", height=76, font=("Arial", 30, "bold"))
    city_entry.grid(row=0, column=0, sticky="nsew", padx=6)

    status_label = ctk.CTkLabel(frame, text="", font=("Arial", 20, "bold"))
    status_label.pack(fill="x", pady=2)

    content = ctk.CTkScrollableFrame(frame)
    content.pack(fill="both", expand=True, pady=6)

    def refresh_weather_cards():
        for widget in content.winfo_children():
            widget.destroy()

        if not saved_weather_locations:
            ctk.CTkLabel(content, text="Search for a city to add weather.", font=("Arial", 30, "bold")).pack(expand=True, pady=80)
            return

        for idx, location in enumerate(saved_weather_locations):
            build_weather_card(content, location, idx)

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

    full_button(top, "Add", add_city, 26).grid(row=0, column=1, sticky="nsew", padx=6)
    full_button(top, "Back", show_main_screen, 26).grid(row=0, column=2, sticky="nsew", padx=6)

    top.grid_columnconfigure(0, weight=3)
    top.grid_columnconfigure(1, weight=1)
    top.grid_columnconfigure(2, weight=1)

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


def show_timer_screen():
    active_screen["name"] = "timer"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=14, pady=14)

    timer_running = {"active": False}
    remaining_time = {"seconds": 0}

    ctk.CTkLabel(frame, text="Timer", font=("Arial", 38, "bold")).pack(fill="x", pady=(0, 4))

    inputs = ctk.CTkFrame(frame, fg_color="transparent")
    inputs.pack(fill="x", pady=6)

    minutes_entry = ctk.CTkEntry(inputs, placeholder_text="Minutes", height=78, font=("Arial", 34, "bold"))
    seconds_entry = ctk.CTkEntry(inputs, placeholder_text="Seconds", height=78, font=("Arial", 34, "bold"))

    minutes_entry.grid(row=0, column=0, sticky="nsew", padx=6)
    seconds_entry.grid(row=0, column=1, sticky="nsew", padx=6)

    inputs.grid_columnconfigure(0, weight=1)
    inputs.grid_columnconfigure(1, weight=1)

    timer_label = ctk.CTkLabel(frame, text="00:00", font=("Arial", 102, "bold"))
    timer_label.pack(fill="x", pady=3)

    status_label = ctk.CTkLabel(frame, text="Ready", font=("Arial", 24, "bold"))
    status_label.pack(fill="x", pady=2)

    def format_time(total_seconds):
        return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

    def update_display():
        timer_label.configure(text=format_time(remaining_time["seconds"]))

    def tick():
        if active_screen["name"] != "timer":
            return

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

    controls = ctk.CTkFrame(frame, fg_color="transparent")
    controls.pack(fill="both", expand=True, pady=6)

    full_button(controls, "Start", start_timer, 27).grid(row=0, column=0, sticky="nsew", padx=6, pady=5)
    full_button(controls, "Pause", lambda: [timer_running.update({"active": False}), status_label.configure(text="Paused")], 27).grid(row=0, column=1, sticky="nsew", padx=6, pady=5)
    full_button(controls, "Reset", lambda: [timer_running.update({"active": False}), remaining_time.update({"seconds": 0}), update_display(), status_label.configure(text="Ready")], 27).grid(row=0, column=2, sticky="nsew", padx=6, pady=5)
    full_button(controls, "Back", show_main_screen, 27).grid(row=1, column=0, sticky="nsew", padx=6, pady=5)
    full_button(controls, "Clock", show_idle_screen, 27).grid(row=1, column=1, columnspan=2, sticky="nsew", padx=6, pady=5)

    for c in range(3):
        controls.grid_columnconfigure(c, weight=1)

    for r in range(2):
        controls.grid_rowconfigure(r, weight=1)


def show_notes_screen():
    active_screen["name"] = "notes"
    clear_screen()

    frame = ctk.CTkFrame(app, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=14, pady=14)

    ctk.CTkLabel(frame, text="Quick Notes", font=("Arial", 38, "bold")).pack(fill="x", pady=(0, 6))

    notes_box = ctk.CTkTextbox(frame, font=("Arial", 28, "bold"))
    notes_box.pack(fill="both", expand=True, pady=6)

    try:
        with open("notes.txt", "r") as file:
            notes_box.insert("0.0", file.read())
    except FileNotFoundError:
        notes_box.insert("0.0", "Project EDA notes...\n")

    status_label = ctk.CTkLabel(frame, text="", font=("Arial", 20, "bold"))
    status_label.pack(fill="x", pady=2)

    def save_notes():
        with open("notes.txt", "w") as file:
            file.write(notes_box.get("0.0", "end"))
        status_label.configure(text="Notes saved")

    nav = ctk.CTkFrame(frame, fg_color="transparent")
    nav.pack(fill="x", pady=4)

    full_button(nav, "Save", save_notes, 26).grid(row=0, column=0, sticky="nsew", padx=6)
    full_button(nav, "Back", show_main_screen, 26).grid(row=0, column=1, sticky="nsew", padx=6)
    full_button(nav, "Clock", show_idle_screen, 26).grid(row=0, column=2, sticky="nsew", padx=6)

    for i in range(3):
        nav.grid_columnconfigure(i, weight=1)


load_idle_weather()
show_idle_screen()
app.mainloop()