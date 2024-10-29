# shared.py

# Verbosity settings for the logging
debug = True
info = True
error = True
warn = True


# binary_locations for check_binary
binary_locations = {}


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


def load_data(key):
    """
    Loads data for the specified key within the 'modules' section of the JSON settings file.
    
    Parameters:
    ----------
    key : str
        The key for the data to retrieve under 'modules'.
    
    Returns:
    -------
    data : dict or None
        The data corresponding to the key, or None if not found.
    """
    if not os.path.exists(SETTINGS_FILE):
        # If the file doesn't exist, initialize it with default settings
        save_default_settings()

    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)
    return data.get("modules", {}).get(key)

def save_data(key, value):
    """
    Saves data for the specified key to the 'modules' section of the JSON settings file.
    
    Parameters:
    ----------
    key : str
        The key for the data to store under 'modules'.
    value : dict
        The data to store under the specified key within 'modules'.
    """
    if not os.path.exists(SETTINGS_FILE):
        save_default_settings()

    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)

    # Ensure 'modules' structure exists, then update the key-value pair
    data.setdefault("modules", {})[key] = value

    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_default_settings():
    """
    Saves the default settings to the JSON settings file if it does not exist.
    """
    with open(SETTINGS_FILE, "w") as f:
        json.dump(default_settings, f, indent=4)












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
