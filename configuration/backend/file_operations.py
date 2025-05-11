import json

# Loads configuration from a Streamlit UploadedFile object.
# Returns a Python dictionary, or None if an error occurs.
def load_config_from_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        try:
            # Ensure the file pointer is at the beginning.
            uploaded_file.seek(0)
            config_data = json.load(uploaded_file)
            return config_data
        except json.JSONDecodeError as e:
            # Logs decoding errors; calling code might handle UI notification.
            print(f"Error decoding JSON: {e}")
            return None
        except Exception as e:
            # Logs other unexpected errors during file loading.
            print(f"An unexpected error occurred during file loading: {e}")
            return None
    return None

# Converts a Python dictionary configuration to a JSON formatted string.
# Returns an empty string if config_data is None.
# Returns "{}" on a serialisation error.
def config_to_json_string(config_data, indent=2):
    if config_data is None:
        return "" # Maintains original behaviour for None input.
    try:
        return json.dumps(config_data, indent=indent)
    except Exception as e: # Catches a broad range of potential serialisation errors.
        print(f"Error serialising config to JSON: {e}")
        return "{}" # Returns an empty JSON object string on error.

# Parses a JSON formatted string into a Python dictionary.
# Returns a Python dictionary, or None if an error occurs (e.g., empty string or invalid JSON).
def json_string_to_config(json_string):
    if not json_string: # Handles empty string case.
        return None
    try:
        config_data = json.loads(json_string)
        return config_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON string: {e}")
        return None
