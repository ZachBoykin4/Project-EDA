# ==========================================
# EDA - Engineering Dashboard Assistant
# HYBRID FAST BUILD
# CustomTkinter + Native Tkinter Converter
# ==========================================

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import threading

# ==========================================
# SETTINGS
# ==========================================

DEFAULT_WEATHER_CITY = "Auburn, AL"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("EDA")

SCREEN_W = app.winfo_screenwidth()
SCREEN_H = app.winfo_screenheight()

app.geometry(f"{SCREEN_W}x{SCREEN_H}+0+0")

app.after(
    100,
    lambda: app.attributes("-fullscreen", True)
)

app.bind("<Escape>", lambda e: app.destroy())

# ==========================================
# GLOBALS
# ==========================================

saved_weather_locations = []

active_screen = {"name": "clock"}

# ==========================================
# CONVERSIONS
# ==========================================

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

# ==========================================
# HELPERS
# ==========================================

def clear_screen():

    for widget in app.winfo_children():
        widget.destroy()

# ==========================================
# WEATHER
# ==========================================

def get_coordinates(city_name):

    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": city_name,
            "count": 1
        },
        timeout=10
    )

    data = response.json()

    if "results" not in data:
        return None

    result = data["results"][0]

    return {
        "name": result["name"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "timezone": result.get("timezone", "auto")
    }

def get_weather(location):

    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",

        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],

            "current":
                "temperature_2m,"
                "apparent_temperature,"
                "relative_humidity_2m,"
                "wind_speed_10m",

            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",

            "timezone": location["timezone"]
        },

        timeout=10
    )

    return response.json()

# ==========================================
# IDLE CLOCK SCREEN
# ==========================================

def show_idle_screen():

    active_screen["name"] = "clock"

    clear_screen()

    frame = ctk.CTkFrame(
        app,
        fg_color="#000000"
    )

    frame.pack(
        fill="both",
        expand=True
    )

    # KAPPA
    ctk.CTkLabel(
        frame,
        text="ΚΑΨ",
        font=("Times New Roman", 70, "bold"),
        text_color="#E00000"
    ).pack(pady=(30, 0))

    ctk.CTkLabel(
        frame,
        text="KAPPA ALPHA PSI",
        font=("Arial", 22, "bold"),
        text_color="white"
    ).pack()

    # CLOCK ROW
    clock_row = ctk.CTkFrame(
        frame,
        fg_color="transparent"
    )

    clock_row.pack(
        expand=True
    )

    left_label = ctk.CTkLabel(
        clock_row,
        text="19",
        font=("Arial", 60, "bold"),
        text_color="#C00000"
    )

    left_label.grid(
        row=0,
        column=0,
        padx=20
    )

    time_label = ctk.CTkLabel(
        clock_row,
        text="",
        font=("Arial", 120, "bold"),
        text_color="white"
    )

    time_label.grid(
        row=0,
        column=1
    )

    pm_label = ctk.CTkLabel(
        clock_row,
        text="",
        font=("Arial", 38, "bold"),
        text_color="white"
    )

    pm_label.grid(
        row=0,
        column=2,
        sticky="s",
        padx=(10, 0),
        pady=(0, 25)
    )

    right_label = ctk.CTkLabel(
        clock_row,
        text="11",
        font=("Arial", 60, "bold"),
        text_color="#C00000"
    )

    right_label.grid(
        row=0,
        column=3,
        padx=20
    )

    date_label = ctk.CTkLabel(
        frame,
        text="",
        font=("Arial", 24, "bold"),
        text_color="#E00000"
    )

    date_label.pack()

    tap_label = ctk.CTkLabel(
        frame,
        text="TAP ANYWHERE TO OPEN EDA",
        font=("Arial", 18, "bold"),
        text_color="white"
    )

    tap_label.pack(pady=20)

    def update_clock():

        if active_screen["name"] != "clock":
            return

        now = datetime.now()

        time_label.configure(
            text=now.strftime("%I:%M").lstrip("0")
        )

        pm_label.configure(
            text=now.strftime("%p")
        )

        date_label.configure(
            text=now.strftime("%A, %B %d").upper()
        )

        app.after(
            1000,
            update_clock
        )

    def open_main(event=None):
        show_main_screen()

    frame.bind("<Button-1>", open_main)

    update_clock()

# ==========================================
# MAIN MENU
# ==========================================

def show_main_screen():

    active_screen["name"] = "main"

    clear_screen()

    frame = ctk.CTkFrame(
        app,
        fg_color="#111111"
    )

    frame.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15
    )

    ctk.CTkLabel(
        frame,
        text="EDA",
        font=("Arial", 42, "bold")
    ).pack(pady=(10, 0))

    ctk.CTkLabel(
        frame,
        text="Engineering Dashboard Assistant",
        font=("Arial", 18)
    ).pack(pady=(0, 15))

    grid = ctk.CTkFrame(
        frame,
        fg_color="transparent"
    )

    grid.pack(
        fill="both",
        expand=True
    )

    buttons = [

        ("Units", show_units_screen),

        ("Weather", show_weather_screen),

        ("Timer", show_timer_screen),

        ("Notes", show_notes_screen),

        ("Clock", show_idle_screen),

        ("Exit", app.destroy),
    ]

    for i, (text, command) in enumerate(buttons):

        row = i // 2
        col = i % 2

        btn = ctk.CTkButton(
            grid,

            text=text,

            command=command,

            font=("Arial", 30, "bold"),

            corner_radius=20
        )

        btn.grid(
            row=row,
            column=col,

            sticky="nsew",

            padx=10,
            pady=10
        )

    for i in range(3):
        grid.grid_rowconfigure(i, weight=1)

    for i in range(2):
        grid.grid_columnconfigure(i, weight=1)

# ==========================================
# FAST UNIT CONVERTER
# ==========================================

def show_units_screen():

    active_screen["name"] = "units"

    clear_screen()

    frame = tk.Frame(
        app,
        bg="#111111"
    )

    frame.pack(
        fill="both",
        expand=True
    )

    title = tk.Label(
        frame,

        text="Unit Converter",

        font=("Arial", 26, "bold"),

        bg="#111111",
        fg="white"
    )

    title.pack(
        pady=10
    )

    # =====================================
    # STYLE
    # =====================================

    style = ttk.Style()

    style.theme_use("clam")

    style.configure(
        "Big.TCombobox",

        fieldbackground="#1E88E5",

        background="#1E88E5",

        foreground="white",

        font=("Arial", 20, "bold"),

        arrowsize=30,

        padding=12
    )

    # CATEGORY

    category_var = tk.StringVar(
        value="Length"
    )

    category_dropdown = ttk.Combobox(

        frame,

        textvariable=category_var,

        values=list(conversions.keys()),

        font=("Arial", 20, "bold"),

        style="Big.TCombobox",

        state="readonly"
    )

    category_dropdown.pack(
        fill="x",
        padx=20,
        pady=10
    )

    # CONVERSION

    conversion_var = tk.StringVar(
        value=list(conversions["Length"].keys())[0]
    )

    conversion_dropdown = ttk.Combobox(

        frame,

        textvariable=conversion_var,

        values=list(conversions["Length"].keys()),

        font=("Arial", 20, "bold"),

        style="Big.TCombobox",

        state="readonly"
    )

    conversion_dropdown.pack(
        fill="x",
        padx=20,
        pady=10
    )

    # INPUT

    input_box = tk.Entry(

        frame,

        font=("Arial", 24),

        justify="center",

        bg="#222222",

        fg="white",

        insertbackground="white"
    )

    input_box.pack(
        fill="x",
        padx=20,
        pady=10,
        ipady=12
    )

    # RESULT

    result_label = tk.Label(

        frame,

        text="Result will appear here",

        font=("Arial", 22, "bold"),

        bg="#111111",

        fg="white"
    )

    result_label.pack(
        pady=15
    )

    # UPDATE OPTIONS

    def update_conversion_options(event=None):

        category = category_var.get()

        options = list(
            conversions[category].keys()
        )

        conversion_dropdown["values"] = options

        conversion_var.set(options[0])

    category_dropdown.bind(
        "<<ComboboxSelected>>",
        update_conversion_options
    )

    # CONVERT

    def convert_value():

        try:

            value = float(
                input_box.get()
            )

            category = category_var.get()

            conversion_type = conversion_var.get()

            result = conversions[category][conversion_type](value)

            from_unit, to_unit = conversion_type.split(" → ")

            result_label.config(
                text=f"{value:g} {from_unit} = {result:.3f} {to_unit}"
            )

        except:
            result_label.config(
                text="Enter valid number"
            )

    # BUTTONS

    button_frame = tk.Frame(
        frame,
        bg="#111111"
    )

    button_frame.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=10
    )

    def big_button(text, command):

        return tk.Button(

            button_frame,

            text=text,

            command=command,

            font=("Arial", 22, "bold"),

            bg="#1E88E5",

            fg="white",

            activebackground="#1565C0",

            activeforeground="white",

            relief="flat",

            bd=0
        )

    convert_btn = big_button(
        "Convert",
        convert_value
    )

    clear_btn = big_button(
        "Clear",
        lambda: input_box.delete(0, "end")
    )

    back_btn = big_button(
        "Back",
        show_main_screen
    )

    convert_btn.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=6,
        pady=6
    )

    clear_btn.grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=6,
        pady=6
    )

    back_btn.grid(
        row=0,
        column=2,
        sticky="nsew",
        padx=6,
        pady=6
    )

    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)
    button_frame.grid_columnconfigure(2, weight=1)

    button_frame.grid_rowconfigure(0, weight=1)

# ==========================================
# PLACEHOLDERS
# ==========================================

def show_weather_screen():

    clear_screen()

    label = ctk.CTkLabel(
        app,
        text="Weather Coming Next",
        font=("Arial", 42, "bold")
    )

    label.pack(expand=True)

def show_timer_screen():

    clear_screen()

    label = ctk.CTkLabel(
        app,
        text="Timer Coming Next",
        font=("Arial", 42, "bold")
    )

    label.pack(expand=True)

def show_notes_screen():

    clear_screen()

    label = ctk.CTkLabel(
        app,
        text="Notes Coming Next",
        font=("Arial", 42, "bold")
    )

    label.pack(expand=True)

# ==========================================
# START
# ==========================================

show_idle_screen()

app.mainloop()