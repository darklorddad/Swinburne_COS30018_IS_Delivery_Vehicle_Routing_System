import copy
import config_manager # Import config_manager

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

def confirm_load_configuration(ss):
    """Handles the logic for confirming and loading an uploaded configuration file."""
    if ss.uploaded_file_buffer is None:
        return {'type': 'warning', 'message': 'No file buffer found to load.'}

    if ss.uploaded_file_buffer.file_id != ss.get("processed_file_id_for_buffer"):
        loaded_config = config_manager.load_config_from_uploaded_file(ss.uploaded_file_buffer)
        if loaded_config is not None:
            # Stash current config if any
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

            ss.config_data = loaded_config
            ss.config_filename = ss.uploaded_file_buffer.name
            ss.processed_file_id = ss.uploaded_file_buffer.file_id
            ss.last_uploaded_filename = ss.uploaded_file_buffer.name
            ss.new_config_saved_to_memory_at_least_once = False # Reset for newly loaded config
            
            ss.edit_mode = False
            ss.action_selected = None
            # Fallback is cleared because load was successful and replaced current context
            ss.fallback_config_state = None 
            ss.uploaded_file_buffer = None # Clear buffer after successful load
            # Snapshot for the newly loaded config
            ss.config_data_snapshot = copy.deepcopy(ss.config_data) 
            ss.config_filename_snapshot = ss.config_filename
            # Mark this file_id as processed for the buffer to prevent re-processing same buffer instance
            ss.processed_file_id_for_buffer = ss.processed_file_id 
            return {'type': 'success', 'message': f"Configuration '{ss.config_filename}' loaded successfully."}
        else:
            ss.processed_file_id_for_buffer = ss.uploaded_file_buffer.file_id # Mark as processed even if failed
            return {'type': 'error', 'message': f"Failed to load or parse '{ss.uploaded_file_buffer.name}'. Ensure it's valid JSON."}
    else:
        # This case means the file instance in the buffer was already processed.
        # If it's already loaded and matches current config, it's an info.
        # If it was processed and failed, it's a warning to upload a new/corrected file.
        if ss.config_data and ss.config_filename == ss.uploaded_file_buffer.name and ss.processed_file_id == ss.uploaded_file_buffer.file_id:
            ss.edit_mode = False
            ss.action_selected = None
            ss.uploaded_file_buffer = None # Clear buffer
            return {'type': 'info', 'message': f"'{ss.config_filename}' is already loaded. Returning to menu."}
        else:
            # This implies the file in buffer was processed (e.g. failed previously)
            return {'type': 'warning', 'message': "This file instance was already processed. If it failed, please select a new or corrected file."}

def clear_config_from_memory(ss):
    """Clears all configuration data from the session state."""
    ss.config_data = None
    ss.config_filename = "config.json" # Reset default
    ss.last_uploaded_filename = None
    ss.processed_file_id = None
    ss.config_data_snapshot = None
    ss.config_filename_snapshot = None
    ss.new_config_saved_to_memory_at_least_once = False
    ss.fallback_config_state = None
    ss.uploaded_file_buffer = None
    ss.processed_file_id_for_buffer = None
    ss.edit_mode = False # Ensure not in edit mode if config is cleared
    ss.action_selected = None # Reset action
    return {'type': 'info', 'message': "Configuration cleared from memory."}

def enter_edit_mode(ss):
    """Sets the application to edit mode and takes necessary snapshots."""
    ss.edit_mode = True
    # Ensure snapshot is taken if it's somehow None (e.g. direct state manipulation outside flow)
    if ss.config_data_snapshot is None and ss.config_data is not None:
        ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    # Take snapshot of filename when entering edit mode
    ss.config_filename_snapshot = ss.config_filename
    # No specific message needed, action implies UI change
