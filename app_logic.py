import copy

DEFAULT_CONFIG_TEMPLATE = {
    # Filename is managed by streamlit.session_state.config_filename, not in config data content
    "warehouse_coordinates_x_y": [0, 0], # Example: [X, Y]
    "parcels": [
        # Example structure:
        # { "id": "P001", "coordinates_x_y": [2, 3], "weight": 10 }
    ],
    "delivery_agents": [
        # Example structure:
        # { "id": "DA01", "capacity_weight": 100 }
    ]
}

def initialize_session_state(ss):
    """Initializes session state variables if they don't exist."""
    defaults = {
        "show_header": False,
        "config_data": None,
        "config_filename": "config.json",
        "processed_file_id": None,
        "edit_mode": False,
        "last_uploaded_filename": None,
        "action_selected": None,
        "initiate_download": False,
        "pending_download_data": None,
        "pending_download_filename": None,
        "uploaded_file_buffer": None,
        "config_data_snapshot": None,
        "new_config_saved_to_memory_at_least_once": False,
        "fallback_config_state": None,
        "config_filename_snapshot": None,
        "processed_file_id_for_buffer": None # Added this as it was in app.py init block
    }
    for key, value in defaults.items():
        if key not in ss:
            ss[key] = value

def handle_new_config_action(ss):
    """Handles the logic for creating a new configuration."""
    # If there's any config in memory (loaded or new-saved), stash it as fallback
    if ss.config_data is not None:
        ss.fallback_config_state = {
            'data': copy.deepcopy(ss.config_data),
            'filename': ss.config_filename,
            'snapshot': copy.deepcopy(ss.config_data_snapshot),
            'filename_snapshot': copy.deepcopy(ss.config_filename_snapshot),
            'last_uploaded': ss.last_uploaded_filename,
            'saved_once': ss.new_config_saved_to_memory_at_least_once
        }
    else:
        ss.fallback_config_state = None

    # Initialize new config
    ss.config_data = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE) # Use deepcopy for the template
    ss.config_filename = "new-config.json"
    ss.config_filename_snapshot = ss.config_filename
    ss.processed_file_id = None
    ss.last_uploaded_filename = None
    ss.action_selected = None # This might be reset in app.py based on flow
    ss.edit_mode = True
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.new_config_saved_to_memory_at_least_once = False
