# This module acts as a controller/facade for the optimisation backend.
# It manages UI navigation state (optimisation_action_selected) and
# orchestrates calls to script_lifecycle.py for script operations
# and parameter_logic.py for parameter editing state.

from . import script_utils # Retained if any direct utility use, but likely not needed
from . import parameter_logic
from . import script_lifecycle # Import the new script lifecycle module

# Initialises session state variables specific to the optimisation module.
def initialise_session_state(ss):
    # Use a new key to ensure this initialisation logic runs if old state exists.
    if "optimisation_module_initialised_v2" not in ss:
        ss.optimisation_module_initialised_v2 = True
        
        # State for uploaded optimisation script
        ss.optimisation_script_content = None
        ss.optimisation_script_filename = None
        ss.optimisation_script_param_schema = None # Schema extracted from the script
        ss.optimisation_script_user_values = {} # User-defined values for the script's parameters
        ss.optimisation_script_user_values_snapshot = {} # Snapshot for cancelling parameter edits
        ss.optimisation_script_loaded_successfully = False
        ss.optimisation_script_error_message = None
        
        # State for script execution results
        ss.optimisation_results = None
        ss.optimisation_run_complete = False
        ss.optimisation_run_error = None

        # Store temp dir and module name for cleanup of the schema-loaded module
        ss.optimisation_script_temp_dir_schema = None
        ss.optimisation_script_module_name_schema = None

        # UI view state for optimisation tab
        ss.optimisation_action_selected = None # None for initial view, "load_script" for loading view

        # Clean up old state variables from any previous version of this module.
        old_keys = [
            "optimisation_module_initialised", "selected_optimisation_technique_id",
            "available_optimisation_techniques", "optimisation_params", 
            "optimisation_technique_loaded", "selected_optimisation_technique_id_widget"
        ]
        for key in old_keys:
            if key in ss:
                del ss[key]

# Handles the upload of an optimisation script.
# Delegates to script_lifecycle.load_and_process_script and updates UI view state.
def handle_optimisation_file_upload(ss):
    uploaded_file = ss.get("optimisation_file_uploader_widget") 

    # script_lifecycle.load_and_process_script will update ss with content, schema, errors etc.
    # and will also handle clearing previous script data if uploaded_file is None.
    success = script_lifecycle.load_and_process_script(ss, uploaded_file)

    if success:
        ss.optimisation_action_selected = None # Return to initial view on successful load
    else:
        # If loading failed, an error message is already set in ss by load_and_process_script.
        # The user remains in the "load_script" view to see the error.
        # If uploaded_file was None, load_and_process_script also sets an error message.
        pass

# Executes the loaded optimisation script.
# Delegates to script_lifecycle.run_script.
def execute_optimisation_script(ss):
    # Pre-checks are handled within script_lifecycle.run_script
    script_lifecycle.run_script(ss)
    # No direct UI navigation change; results/errors are displayed in the current view.

# Clears all state related to the currently loaded optimisation script.
# Delegates data clearing to script_lifecycle.clear_script_data and resets UI view.
def clear_optimisation_script(ss):
    script_lifecycle.clear_script_data(ss)
    ss.optimisation_action_selected = None # Reset to initial view


# --- Optimisation Tab View Management ---
# These functions manage the 'optimisation_action_selected' state variable,
# which controls which UI view is displayed in the Optimisation tab.

# Switches the UI to the script loading view.
def handle_initiate_load_script_action(ss):
    ss.optimisation_action_selected = "load_script"
    # Clear any previous error messages when initiating a new load action
    ss.optimisation_script_error_message = None 

# Handles cancelling the script loading process and returns to the initial optimisation view.
def handle_cancel_load_script_action(ss):
    ss.optimisation_action_selected = None
    # Clear our application's concept of a pending file by resetting script content/filename if necessary,
    # though typically this action is about navigating away, not clearing a loaded script.
    # The file uploader widget itself will retain its state until the user interacts with it again
    # or the page structure changes significantly.
    # Clearing ss.optimisation_script_error_message is good.
    ss.optimisation_script_error_message = None
    
    ss.optimisation_action_selected = None # Reset to initial view


# --- Optimisation Parameter Editing View Management ---

# Switches the UI to the parameter editing view, taking a snapshot of current parameter values.
def handle_edit_parameters_action(ss):
    parameter_logic.take_parameter_snapshot(ss)
    ss.optimisation_action_selected = "edit_parameters"

# Saves the edited parameters and returns to the initial optimisation view.
def handle_save_parameters_action(ss):
    # Parameters are already updated in ss.optimisation_script_user_values by form widgets.
    # Delegate committing changes (like clearing snapshot) to parameter_logic.
    result = parameter_logic.commit_parameter_changes(ss)
    ss.optimisation_action_selected = None # Return to initial view
    return result

# Cancels parameter editing, reverting values to their state before editing, and returns to the initial view.
def handle_cancel_edit_parameters_action(ss):
    parameter_logic.revert_parameter_changes(ss)
    ss.optimisation_action_selected = None # Return to initial view
