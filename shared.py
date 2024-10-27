# shared.py

# Verbosity settings for the logging
debug = True
info = True
error = True
warn = True


import json
import os

def update_shared(attr_name, value):
    globals()[attr_name] = value

# Path to the settings file
SETTINGS_FILE = 'config.json'

# Default settings structure
default_settings = {
    'modules': {}
}

# Load existing settings or create new default settings
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
    else:
        settings = default_settings
        save_settings(settings)  # Save defaults if no config exists
    return settings

# Save settings to file
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, indent=4)

# Add or update module settings
def add_module_settings(module_name, settings):
    config = load_settings()
    # Only add if module settings don’t already exist
    if module_name not in config['modules']:
        config['modules'][module_name] = settings
        save_settings(config)
    return config['modules'][module_name]  # Return updated or existing settings

# Load module settings
def get_module_settings(module_name):
    config = load_settings()
    return config['modules'].get(module_name, {})

# Expose settings for easy access
settings = load_settings()
