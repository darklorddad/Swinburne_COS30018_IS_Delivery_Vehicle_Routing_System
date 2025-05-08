import json

def load_config_from_uploaded_file(uploaded_file):
    """
    Loads configuration from a Streamlit UploadedFile object.
    Returns a Python dictionary or None if an error occurs.
    """
    if uploaded_file is not None:
        try:
            # Ensure the file pointer is at the beginning if it was read before
            uploaded_file.seek(0)
            config_data = json.load(uploaded_file)
            return config_data
        except json.JSONDecodeError as e:
            # In a real app, you might use streamlit.error in the calling code
            print(f"Error decoding JSON: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during file loading: {e}")
            return None
    return None

def config_to_json_string(config_data, indent=2):
    """
    Converts a Python dictionary configuration to a JSON formatted string.
    Returns an empty string if config_data is None.
    """
    if config_data is None:
        return ""
    try:
        return json.dumps(config_data, indent=indent)
    except TypeError as e:
        print(f"Error serializing config to JSON: {e}")
        # Return a string representation of an empty JSON object or an error message
        return "{}" 
    return ""

def json_string_to_config(json_string):
    """
    Parses a JSON formatted string into a Python dictionary.
    Returns a Python dictionary or None if an error occurs (e.g., empty string or invalid JSON).
    """
    if not json_string: # Handle empty string case
        return None
    try:
        config_data = json.loads(json_string)
        return config_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON string: {e}")
        return None
