import copy
# import json # Not directly used for json.load/dumps, but for type hints if any
from .file_operations import load_config_from_uploaded_file, config_to_json_string

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
        loaded_config = load_config_from_uploaded_file(ss.uploaded_file_buffer)
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
    
    # Ensure 'parcels' and 'delivery_agents' keys exist in config_data
    if isinstance(ss.config_data, dict):
        if "parcels" not in ss.config_data:
            ss.config_data["parcels"] = []
        if "delivery_agents" not in ss.config_data:
            ss.config_data["delivery_agents"] = []
    # No specific message needed, action implies UI change

def handle_cancel_edit(ss):
    """Handles the logic for canceling edits and reverting or clearing the configuration."""
    # Revert to the snapshot
    if ss.config_data_snapshot is not None:
        ss.config_data = copy.deepcopy(ss.config_data_snapshot)
        # Also revert filename if its snapshot exists
        if ss.config_filename_snapshot is not None:
            ss.config_filename = ss.config_filename_snapshot
    else:
        # This case implies config_data_snapshot is None.
        # If it's a new config and has no snapshot, it means it was never properly initialized.
        if ss.last_uploaded_filename is None: # It's a new config
            ss.config_data = None
            ss.config_filename = "config.json" # Reset filename
            ss.config_filename_snapshot = None # No snapshot for a cleared new config

    ss.edit_mode = False
    ss.action_selected = None

    is_current_config_new = ss.last_uploaded_filename is None
    current_new_config_never_saved_via_save_edits = not ss.new_config_saved_to_memory_at_least_once

    if is_current_config_new and current_new_config_never_saved_via_save_edits:
        # Current new config should be discarded. Check for fallback.
        if ss.fallback_config_state is not None:
            # Restore from fallback
            fallback = ss.fallback_config_state
            ss.config_data = fallback['data']
            ss.config_filename = fallback['filename']
            ss.last_uploaded_filename = fallback['last_uploaded']
            ss.config_data_snapshot = fallback['snapshot']
            ss.config_filename_snapshot = fallback.get('filename_snapshot', fallback['filename']) # Restore filename_snapshot
            ss.new_config_saved_to_memory_at_least_once = fallback['saved_once']
        else:
            # No fallback, so clear to None (data, filename, and snapshots)
            ss.config_data = None
            ss.config_filename = "config.json"
            ss.config_data_snapshot = None
            ss.config_filename_snapshot = None
            # new_config_saved_to_memory_at_least_once is already False for the discarded config
    # else: current config (loaded, or new+saved_via_SE) remains (reverted to its snapshot for data and filename).

    ss.fallback_config_state = None # Fallback is consumed or no longer relevant

def handle_save_edits(ss):
    """Handles the logic for saving edits to the configuration in memory."""
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.config_filename_snapshot = ss.config_filename # Commit current filename as snapshot
    if ss.last_uploaded_filename is None:
        ss.new_config_saved_to_memory_at_least_once = True

    ss.edit_mode = False
    ss.action_selected = None
    ss.fallback_config_state = None # Edits committed, fallback irrelevant
    return {'type': 'success', 'message': "Edits saved to memory."}

def handle_save_and_download(ss):
    """Handles logic for saving, preparing for download, and exiting edit mode."""
    # Prepare config_to_save strictly according to DEFAULT_CONFIG_TEMPLATE
    config_data_internal = ss.config_data
    config_to_save = {}
    for key in DEFAULT_CONFIG_TEMPLATE.keys():
        config_to_save[key] = config_data_internal.get(key, copy.deepcopy(DEFAULT_CONFIG_TEMPLATE[key]))
        
    # Ensure snapshot reflects the state being saved
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.config_filename_snapshot = ss.config_filename # Commit current filename as snapshot

    # Set up for download
    ss.pending_download_data = config_to_json_string(config_to_save)
    ss.pending_download_filename = ss.config_filename
    ss.initiate_download = True

    was_new_config_being_saved = ss.last_uploaded_filename is None

    ss.edit_mode = False
    ss.action_selected = None

    if was_new_config_being_saved:
        ss.new_config_saved_to_memory_at_least_once = True
    
    ss.fallback_config_state = None # Config saved/downloaded, fallback irrelevant
    # No direct message here, UI will trigger download and rerun

def finalize_download(ss):
    """Resets download-related flags after a download is initiated."""
    ss.initiate_download = False
    ss.pending_download_data = None
    ss.pending_download_filename = None

def handle_file_uploader_change(ss): # Added 'ss' parameter
    """
    Updates the uploaded_file_buffer and related state based on the
    config_uploader_buffer_widget's current value.
    Called on_change of the file_uploader.
    """
    # ss = streamlit.session_state # Now passed as parameter
    uploaded_file_widget_val = ss.get("config_uploader_buffer_widget") # Key of the file_uploader
    if uploaded_file_widget_val is not None:
        ss.uploaded_file_buffer = uploaded_file_widget_val
        # Reset processed_file_id_for_buffer when a new file is selected by the uploader
        ss.processed_file_id_for_buffer = None
    else:  # User cleared the file from the uploader widget
        if ss.uploaded_file_buffer is not None:
            # If there was a file in our buffer, clear it
            ss.uploaded_file_buffer = None
            ss.processed_file_id_for_buffer = None

def handle_cancel_load_action(ss):
    """Handles the cancel action from the load configuration view."""
    ss.action_selected = None
    ss.uploaded_file_buffer = None
    ss.processed_file_id_for_buffer = None

def handle_load_config_action(ss):
    """Switches to the load configuration view."""
    ss.action_selected = "load"

def handle_show_header_toggle(ss): # Added 'ss' parameter
    """Updates the show_header state based on the toggle widget."""
    # ss = streamlit.session_state # Now passed as parameter
    ss.show_header = ss.get("show_header_toggle_widget", False) # Key of the toggle

def validate_edit_mode_preconditions(ss):
    """
    Validates if the necessary preconditions for entering edit mode are met.
    Specifically, checks if config_data exists.
    If not, sets edit_mode to False and returns an appropriate status.
    """
    if ss.config_data is None:
        ss.edit_mode = False
        return {'valid': False, 'message': "No configuration data found. Returning to selection.", 'type': 'warning'}
    return {'valid': True}
