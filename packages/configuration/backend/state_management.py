import copy
from .file_operations import load_config_from_uploaded_file, config_to_json_string

# Default structure for a new configuration.
# Filename is managed by ss.config_filename, not within this data structure.
DEFAULT_CONFIG_TEMPLATE = {
    "warehouse_coordinates_x_y": [0, 0], # Default warehouse coordinates [X, Y].
    "parcels": [
        # Example parcel structure:
        # { "id": "P001", "coordinates_x_y": [2, 3], "weight": 10 }
    ],
    "delivery_agents": [
        # Example delivery agent structure:
        # { "id": "DA01", "capacity_weight": 100 }
    ]
}

# Initialises session state variables if they do not already exist.
def initialise_session_state(ss, clear_all=False): # Added clear_all
    CONFIG_DATA_AND_UI_DEFAULTS = {
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
        "processed_file_id_for_buffer": None, # Tracks the file ID of the current buffer content.
        "simple_num_parcels_to_generate": 5, # Default for simple generator
        "simple_num_agents_to_generate": 2, # Default for simple generator
        "simple_config_action_selected": None, # Controls the view within the Simple tab
        "simple_show_generate_options": False # To control visibility of generate inputs
    }
    if clear_all:
        # Set all config-specific session state keys to their defaults
        for key, value in CONFIG_DATA_AND_UI_DEFAULTS.items():
            ss[key] = copy.deepcopy(value) if isinstance(value, (list, dict)) else value
    else: # Original behavior: initialize only if key is not present
        for key, value in CONFIG_DATA_AND_UI_DEFAULTS.items():
            if key not in ss:
                ss[key] = copy.deepcopy(value) if isinstance(value, (list, dict)) else value

# Helper function to stash the current configuration state as a fallback.
def _stash_current_config_as_fallback(ss):
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

# Handles the logic for creating a new configuration.
def handle_new_config_action(ss):
    # Stashes the current configuration, if any, as a fallback.
    _stash_current_config_as_fallback(ss)

    # Initializes a new configuration using the default template.
    ss.config_data = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE) # Ensures template is not modified.
    ss.config_filename = "new-config.json"
    # Reset standard mode state
    ss.action_selected = None
    # Set simple mode navigation if applicable
    if ss.get("simple_mode", False):
        ss.simple_config_action_selected = "new_edit"
    ss.config_filename_snapshot = ss.config_filename
    ss.processed_file_id = None
    ss.last_uploaded_filename = None
    ss.edit_mode = True
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.new_config_saved_to_memory_at_least_once = False

# Handles the logic for confirming and loading an uploaded configuration file.
def confirm_load_configuration(ss):
    if ss.uploaded_file_buffer is None:
        return {'type': 'warning', 'message': 'No file buffer found to load.'}

    # Processes the file if it has not been processed already.
    if ss.uploaded_file_buffer.file_id != ss.get("processed_file_id_for_buffer"):
        loaded_config = load_config_from_uploaded_file(ss.uploaded_file_buffer)
        if loaded_config is not None:
            # Stashes current configuration, if any, before loading the new one.
            _stash_current_config_as_fallback(ss)

            # Updates session state with the loaded configuration.
            ss.config_data = loaded_config
            ss.config_filename = ss.uploaded_file_buffer.name
            ss.processed_file_id = ss.uploaded_file_buffer.file_id
            ss.last_uploaded_filename = ss.uploaded_file_buffer.name
            ss.new_config_saved_to_memory_at_least_once = False # Reset for the newly loaded config.
            
            ss.edit_mode = False
            if ss.get("simple_mode"):
                ss.simple_config_action_selected = None
            else:
                ss.action_selected = None
            ss.fallback_config_state = None # Clears fallback as load was successful.
            ss.uploaded_file_buffer = None # Clears buffer after successful load.
            # Creates a snapshot of the newly loaded configuration.
            ss.config_data_snapshot = copy.deepcopy(ss.config_data) 
            ss.config_filename_snapshot = ss.config_filename
            # Marks this file_id as processed to prevent re-processing the same buffer instance.
            ss.processed_file_id_for_buffer = ss.processed_file_id 
            return {'type': 'info', 'message': f"Configuration '{ss.config_filename}' loaded successfully"}
        else:
            # Marks as processed even if loading failed.
            ss.processed_file_id_for_buffer = ss.uploaded_file_buffer.file_id 
            return {'type': 'error', 'message': f"Failed to load or parse '{ss.uploaded_file_buffer.name}'. Ensure it's valid JSON"}
    else:
        # Handles cases where the file in the buffer has already been processed.
        if ss.config_data and ss.config_filename == ss.uploaded_file_buffer.name and ss.processed_file_id == ss.uploaded_file_buffer.file_id:
            # If already loaded and matches current config, inform user and clear buffer.
            ss.edit_mode = False
            if ss.get("simple_mode"):
                ss.simple_config_action_selected = None
            else:
                ss.action_selected = None
            ss.uploaded_file_buffer = None
            return {'type': 'info', 'message': f"'{ss.config_filename}' is already loaded. Returning to menu"}
        else:
            # If processed but failed previously, prompt for a new or corrected file.
            return {'type': 'warning', 'message': "This file instance was already processed. If it failed, please select a new or corrected file"}

# Clears all configuration data from the session state.
def clear_config_from_memory(ss):
    ss.config_data = None
    ss.config_filename = "config.json" # Resets to default filename.
    ss.last_uploaded_filename = None
    ss.processed_file_id = None
    ss.config_data_snapshot = None
    ss.config_filename_snapshot = None
    ss.new_config_saved_to_memory_at_least_once = False
    ss.fallback_config_state = None
    ss.uploaded_file_buffer = None
    ss.processed_file_id_for_buffer = None

# Resets the simple config action.
def reset_simple_config_action(ss):
    ss.simple_config_action_selected = None

# Sets the application to edit action.
def handle_edit_config_action(ss):
    ss.simple_config_action_selected = "edit"
    ss.edit_mode = False # Ensures not in edit mode if config is cleared.
    ss.action_selected = None # Resets action.
    return {'type': 'info', 'message': "Configuration cleared from memory"}

# Sets the application to edit mode and takes necessary snapshots.
def enter_edit_mode(ss):
    ss.edit_mode = True
    # Ensures a snapshot is taken if one does not exist.
    if ss.config_data_snapshot is None and ss.config_data is not None:
        ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    # Takes a snapshot of the filename when entering edit mode.
    ss.config_filename_snapshot = ss.config_filename
    
    # Ensures 'parcels' and 'delivery_agents' keys exist in config_data.
    if isinstance(ss.config_data, dict):
        if "parcels" not in ss.config_data:
            ss.config_data["parcels"] = []
        if "delivery_agents" not in ss.config_data:
            ss.config_data["delivery_agents"] = []
    # No specific message needed; action implies UI change.

# Handles the logic for cancelling edits and reverting or clearing the configuration.
def handle_cancel_edit(ss):
    # Reverts to the snapshot if available.
    if ss.config_data_snapshot is not None:
        ss.config_data = copy.deepcopy(ss.config_data_snapshot)
        # Also reverts filename if its snapshot exists.
        if ss.config_filename_snapshot is not None:
            ss.config_filename = ss.config_filename_snapshot
    else:
        # Handles cases where config_data_snapshot is None (e.g., if config_data itself is None or was cleared).
        # If it was conceptually a 'new' config (never loaded from file) and is now effectively empty, ensure filename is also reset.
        if ss.last_uploaded_filename is None: # Indicates a new config.
            ss.config_data = None # Ensure data is None if snapshot was None.
            ss.config_filename = "config.json" # Resets filename.
            ss.config_filename_snapshot = None # No snapshot for a cleared new config.

    ss.edit_mode = False
    
    if ss.get("simple_mode"):
        ss.simple_config_action_selected = None
    else:
        ss.action_selected = None

    is_current_config_new = ss.last_uploaded_filename is None
    current_new_config_never_saved_via_save_edits = not ss.new_config_saved_to_memory_at_least_once

    if is_current_config_new and current_new_config_never_saved_via_save_edits:
        # The current new config should be discarded. Checks for a fallback.
        if ss.fallback_config_state is not None:
            # Restores from fallback.
            fallback = ss.fallback_config_state
            ss.config_data = fallback['data']
            ss.config_filename = fallback['filename']
            ss.last_uploaded_filename = fallback['last_uploaded']
            ss.config_data_snapshot = fallback['snapshot']
            ss.config_filename_snapshot = fallback.get('filename_snapshot', fallback['filename']) # Restores filename_snapshot.
            ss.new_config_saved_to_memory_at_least_once = fallback['saved_once']
        else:
            # No fallback exists, so clear current config data, filename, and snapshots.
            ss.config_data = None
            ss.config_filename = "config.json"
            ss.config_data_snapshot = None
            ss.config_filename_snapshot = None
            # new_config_saved_to_memory_at_least_once is already False for the discarded config.
    # Otherwise, the current config (loaded, or new and saved via "Save Edits") remains,
    # reverted to its snapshot for data and filename.

    ss.fallback_config_state = None # Fallback is consumed or no longer relevant.

# Handles the logic for saving edits to the configuration in memory.
def handle_save_edits(ss):
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.config_filename_snapshot = ss.config_filename # Commits current filename as snapshot.
    if ss.last_uploaded_filename is None: # Indicates a new config.
        ss.new_config_saved_to_memory_at_least_once = True

    ss.edit_mode = False
    ss.action_selected = None
    ss.fallback_config_state = None # Edits committed, fallback is irrelevant.
    return {'type': 'success', 'message': "Edits saved to memory"}

# Updates the uploaded_file_buffer and related state.
# Called on_change of the file_uploader widget.
def handle_file_uploader_change(ss):
    uploaded_file_widget_val = ss.get("config_uploader_buffer_widget")
    if uploaded_file_widget_val is not None:
        ss.uploaded_file_buffer = uploaded_file_widget_val
        # Resets processed_file_id_for_buffer when a new file is selected.
        ss.processed_file_id_for_buffer = None
    else:  # User cleared the file from the uploader widget.
        if ss.uploaded_file_buffer is not None:
            # If there was a file in our buffer, clear it.
            ss.uploaded_file_buffer = None
            ss.processed_file_id_for_buffer = None

# Handles the cancel action from the load configuration view.
def handle_cancel_load_action(ss):
    if ss.get("simple_mode"):
        ss.simple_config_action_selected = None
    else:
        ss.action_selected = None
    ss.uploaded_file_buffer = None
    ss.processed_file_id_for_buffer = None

# Switches to the load configuration view.
def handle_load_config_action(ss):
    ss.action_selected = "load"

# Toggles the visibility of the Streamlit header.
def handle_show_header_toggle(ss):
    ss.show_header = ss.get("show_header_toggle_widget", False)

# Validates if preconditions for entering edit mode are met.
# Specifically, checks if config_data exists.
# If not, sets edit_mode to False and returns an appropriate status.
def validate_edit_mode_preconditions(ss):
    if ss.config_data is None:
        ss.edit_mode = False
        return {'valid': False, 'message': "No configuration data found. Returning to selection", 'type': 'warning'}
    return {'valid': True}
