import copy
from .file_operations import config_to_json_string
from .state_management import DEFAULT_CONFIG_TEMPLATE # For structuring the download content

# Handles logic for saving, preparing for download, and exiting edit mode.
# This function is called when the user intends to save the current configuration
# and immediately download it as a JSON file.
def handle_save_and_download(ss):
    # Prepares config_to_save strictly according to DEFAULT_CONFIG_TEMPLATE.
    # This ensures that the downloaded file has a consistent structure,
    # including all expected top-level keys, even if some are empty lists/default values.
    config_data_internal = ss.config_data
    config_to_save = {}
    for key in DEFAULT_CONFIG_TEMPLATE.keys():
        config_to_save[key] = config_data_internal.get(key, copy.deepcopy(DEFAULT_CONFIG_TEMPLATE[key]))
        
    # Ensures snapshot reflects the state being saved (current edits in ss.config_data).
    # This makes the in-memory state consistent with what's being downloaded.
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.config_filename_snapshot = ss.config_filename # Commits current filename as snapshot.

    # Sets up session state variables for the download process.
    # The frontend will use these to trigger the actual browser download.
    ss.pending_download_data = config_to_json_string(config_to_save)
    ss.pending_download_filename = ss.config_filename
    ss.initiate_download = True # Flag for the frontend to start the download.

    # Checks if the configuration being saved and downloaded was a "new" configuration
    # (i.e., not loaded from a file). This affects the 'new_config_saved_to_memory_at_least_once' flag.
    was_new_config_being_saved = ss.last_uploaded_filename is None

    # Exits edit mode and resets the selected action, as the save/download action is complete.
    ss.edit_mode = False
    ss.action_selected = None

    # If it was a new configuration, mark it as having been saved at least once.
    # This influences behaviour in handle_cancel_edit if the user later cancels further edits
    # to this (now saved and downloaded) new configuration.
    if was_new_config_being_saved:
        ss.new_config_saved_to_memory_at_least_once = True
    
    # Clears any fallback state, as the current configuration has been successfully
    # saved (to memory snapshot) and initiated for download. The fallback is no longer relevant.
    ss.fallback_config_state = None
    # No direct message is returned here; the UI will trigger the download
    # and then typically rerun, which will reflect the exit from edit mode.

# Resets download-related flags after a download is initiated by the frontend.
# This is typically called after the frontend has processed the download trigger.
def finalize_download(ss):
    ss.initiate_download = False
    ss.pending_download_data = None
    ss.pending_download_filename = None
