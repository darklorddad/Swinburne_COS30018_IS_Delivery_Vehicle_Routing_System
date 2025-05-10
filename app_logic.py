import copy
import config_manager # Import config_manager
import streamlit # Allow access to streamlit.session_state

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
    config_to_save = {
        "warehouse_coordinates_x_y": config_data_internal.get("warehouse_coordinates_x_y"),
        "parcels": config_data_internal.get("parcels", []),
        "delivery_agents": config_data_internal.get("delivery_agents", [])
    }
    # Ensure snapshot reflects the state being saved
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.config_filename_snapshot = ss.config_filename # Commit current filename as snapshot

    # Set up for download
    ss.pending_download_data = config_manager.config_to_json_string(config_to_save)
    ss.pending_download_filename = ss.config_filename
    ss.initiate_download = True

    was_new_config_being_saved = ss.last_uploaded_filename is None

    ss.edit_mode = False
    ss.action_selected = None

    if was_new_config_being_saved:
        ss.new_config_saved_to_memory_at_least_once = True
    
    ss.fallback_config_state = None # Config saved/downloaded, fallback irrelevant
    # No direct message here, UI will trigger download and rerun

# --- Parcel Management Logic ---
def add_parcel(ss, parcel_id, parcel_x, parcel_y, parcel_weight):
    """Adds a new parcel to the configuration if the ID is unique."""
    if not parcel_id:
        return {'type': 'warning', 'message': "Parcel ID cannot be empty"}
    if "parcels" not in ss.config_data:
        ss.config_data["parcels"] = []
    if any(p['id'] == parcel_id for p in ss.config_data["parcels"]):
        return {'type': 'warning', 'message': f"Parcel ID '{parcel_id}' already exists"}
    
    ss.config_data["parcels"].append({
        "id": parcel_id,
        "coordinates_x_y": [parcel_x, parcel_y],
        "weight": parcel_weight
    })
    return {'type': 'success', 'message': f"Parcel '{parcel_id}' added."} # Message for potential future use

def remove_parcel(ss, parcel_id_to_remove):
    """Removes a parcel from the configuration by its ID."""
    if not parcel_id_to_remove:
        return {'type': 'warning', 'message': "No parcel selected to remove."}
    if "parcels" in ss.config_data:
        initial_len = len(ss.config_data["parcels"])
        ss.config_data["parcels"] = [p for p in ss.config_data["parcels"] if p['id'] != parcel_id_to_remove]
        if len(ss.config_data["parcels"]) < initial_len:
            return {'type': 'success', 'message': f"Parcel '{parcel_id_to_remove}' removed."} # For potential future use
        else:
            return {'type': 'warning', 'message': f"Parcel ID '{parcel_id_to_remove}' not found."}
    return {'type': 'info', 'message': "No parcels to remove from."}


# --- Delivery Agent Management Logic ---
def add_delivery_agent(ss, agent_id, capacity_weight):
    """Adds a new delivery agent to the configuration if the ID is unique."""
    if not agent_id:
        return {'type': 'warning', 'message': "Agent ID cannot be empty"}
    if "delivery_agents" not in ss.config_data:
        ss.config_data["delivery_agents"] = []
    if any(a['id'] == agent_id for a in ss.config_data["delivery_agents"]):
        return {'type': 'warning', 'message': f"Agent ID '{agent_id}' already exists"}

    ss.config_data["delivery_agents"].append({
        "id": agent_id,
        "capacity_weight": capacity_weight
    })
    return {'type': 'success', 'message': f"Agent '{agent_id}' added."} # Message for potential future use

def remove_delivery_agent(ss, agent_id_to_remove):
    """Removes a delivery agent from the configuration by its ID."""
    if not agent_id_to_remove:
        return {'type': 'warning', 'message': "No agent selected to remove."}
    if "delivery_agents" in ss.config_data:
        initial_len = len(ss.config_data["delivery_agents"])
        ss.config_data["delivery_agents"] = [a for a in ss.config_data["delivery_agents"] if a['id'] != agent_id_to_remove]
        if len(ss.config_data["delivery_agents"]) < initial_len:
            return {'type': 'success', 'message': f"Agent '{agent_id_to_remove}' removed."} # For potential future use
        else:
            return {'type': 'warning', 'message': f"Agent ID '{agent_id_to_remove}' not found."}
    return {'type': 'info', 'message': "No agents to remove from."}

# --- Edit Mode General Settings Logic ---
def handle_filename_update():
    """
    Updates the config_filename in session_state based on the
    filename_input_widget's current value.
    Called on_change of the filename text input.
    """
    ss = streamlit.session_state
    new_filename_base = ss.get("filename_input_widget") # Key of the text_input widget
    if new_filename_base: # Ensure not empty
        new_full_filename = f"{new_filename_base}.json" if not new_filename_base.endswith(".json") else new_filename_base
        ss.config_filename = new_full_filename
    # If new_filename_base is empty, ss.config_filename remains unchanged,
    # preventing it from becoming just ".json". The input field will show the empty string,
    # but the underlying config_filename won't be corrupted until valid text is entered.

def handle_warehouse_coordinates_update():
    """
    Updates the warehouse_coordinates_x_y in config_data based on
    the number input widgets' current values.
    Called on_change of either warehouse coordinate number input.
    """
    ss = streamlit.session_state
    wh_x_val = ss.get("wh_x_input_widget") # Key of the X number_input
    wh_y_val = ss.get("wh_y_input_widget") # Key of the Y number_input

    if not isinstance(ss.get("config_data"), dict):
        # This should ideally not happen if the app flow is correct and config_data is initialized.
        # Initialize with default structure if necessary for robustness.
        ss.config_data = {"warehouse_coordinates_x_y": [0, 0]}

    # Fallback to current values in config_data if widget values are somehow None
    # (though number_input usually prevents this with default values).
    current_coords = ss.config_data.get("warehouse_coordinates_x_y", [0, 0])
    
    final_wh_x = wh_x_val if wh_x_val is not None else current_coords[0]
    final_wh_y = wh_y_val if wh_y_val is not None else current_coords[1]
    
    ss.config_data["warehouse_coordinates_x_y"] = [int(final_wh_x), int(final_wh_y)]

def finalize_download(ss):
    """Resets download-related flags after a download is initiated."""
    ss.initiate_download = False
    ss.pending_download_data = None
    ss.pending_download_filename = None

def handle_file_uploader_change(ss):
    """
    Updates the uploaded_file_buffer and related state based on the
    config_uploader_buffer_widget's current value.
    Called on_change of the file_uploader.
    """
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

def handle_show_header_toggle(ss):
    """Updates the show_header state based on the toggle widget."""
    ss.show_header = ss.get("show_header_toggle_widget", False) # Key of the toggle
