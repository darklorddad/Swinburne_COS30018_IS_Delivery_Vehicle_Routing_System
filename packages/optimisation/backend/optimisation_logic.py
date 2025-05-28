# This module acts as a controller/facade for the optimisation backend.
# It manages UI navigation state (optimisation_action_selected) and
# orchestrates calls to script_lifecycle.py for script operations
# and parameter_logic.py for parameter editing state.

from . import script_utils
from . import parameter_logic
from . import script_lifecycle
from packages.execution.backend import execution_logic
from packages.execution.backend import py4j_gateway

# Initialises session state variables specific to the optimisation module.
def initialise_session_state(ss, clear_all_flag_for_other_modules=False): # Added dummy flag
    # If the init flag is not present (or if we were to implement a direct clear_all for this module),
    # proceed to initialize/reset all optimisation-specific states.
    # The dvrs.py will handle deleting this flag if a full reset is intended.
    if "optimisation_module_initialised_v2" not in ss:
        ss.optimisation_module_initialised_v2 = True
        
        # State for uploaded optimisation script
        ss.optimisation_script_content = None
        ss.optimisation_script_filename = None
        ss.optimisation_script_param_schema = None
        ss.optimisation_script_user_values = {}
        ss.optimisation_script_user_values_snapshot = {}
        ss.optimisation_script_loaded_successfully = False
        ss.optimisation_script_error_message = None
        
        # State for script execution results
        ss.optimisation_results = None
        ss.optimisation_run_complete = False
        ss.optimisation_run_error = None

        # Fetched DA statuses
        ss.fetched_delivery_agent_statuses = None # Will store the list of DA status dicts
        ss.da_status_fetch_message = None # Status message for DA fetch operation
        ss.optimisation_execution_tab_run_status_message = None

        # Store temp dir and module name for cleanup
        ss.optimisation_script_temp_dir_schema = None
        ss.optimisation_script_module_name_schema = None

        # UI view state
        ss.optimisation_action_selected = None

        # For featured scripts
        ss.featured_optimisation_scripts = [] # List of dicts {'name': str, 'path': str}
        ss.selected_featured_script_path = None # Store the path of the chosen featured script
        ss.featured_optimisation_scripts = discover_featured_scripts() # Discover on init

        # Clean up old state variables
        old_keys = [
            "optimisation_module_initialised", "selected_optimisation_technique_id",
            "available_optimisation_techniques", "optimisation_params", 
            "optimisation_technique_loaded", "selected_optimisation_technique_id_widget"
        ]
        for key in old_keys:
            if key in ss:
                del ss[key]

def discover_featured_scripts():
    """Scans the 'featured_scripts' directory and returns a list of script names and paths."""
    scripts = []
    # Define the path to your featured scripts directory
    # Look in pnp/featured directory which is a sibling to packages
    packages_dir = os.path.dirname(os.path.dirname(__file__))  # Goes up from packages/optimisation/backend
    scripts_dir = os.path.join(packages_dir, "..", "pnp", "featured")  # Go up to root then into pnp/featured
    if os.path.isdir(scripts_dir):
        for filename in os.listdir(scripts_dir):
            if filename.endswith(".py"):
                scripts.append({"name": filename, "path": os.path.join(scripts_dir, filename)})
    else:
        # Optionally, log or handle the case where the directory doesn't exist
        print(f"Warning: Featured scripts directory not found at {os.path.abspath(scripts_dir)}")
    return scripts

# Handles the upload of an optimisation script.
# Delegates to script_lifecycle.load_and_process_script and updates UI view state.
def handle_optimisation_file_upload(ss):
    uploaded_file = ss.get("optimisation_file_uploader_widget") 

    # script_lifecycle.load_and_process_script will update ss with content, schema, errors etc.
    # and will also handle clearing previous script data if uploaded_file is None.
    success = script_lifecycle.load_and_process_script_from_uploaded_file(ss, uploaded_file)

    if success:
        ss.optimisation_action_selected = None # Return to initial view on successful load
        ss.selected_featured_script_path = None # Clear selected featured script
    else:
        # If loading failed, an error message is already set in ss by load_and_process_script.
        # The user remains in the "load_script" view to see the error.
        # If uploaded_file was None, load_and_process_script also sets an error message.
        pass

# Handles loading a selected featured optimisation script.
def handle_load_featured_script(ss):
    script_path_to_load = ss.get("selected_featured_script_path_widget") # From selectbox
    if script_path_to_load and script_path_to_load != "None":
        ss.selected_featured_script_path = script_path_to_load
        success = script_lifecycle.load_and_process_script_from_path(ss, ss.selected_featured_script_path)
        if success:
            ss.optimisation_action_selected = None # Return to initial view
            # Clear the file uploader widget if a featured script is successfully loaded
            if "optimisation_file_uploader_widget" in ss:
                ss.optimisation_file_uploader_widget = None
        # Error message is handled by load_and_process_script_from_path
    else:
        ss.selected_featured_script_path = None # User selected "None" or no selection

# Executes the loaded optimisation script.
# Delegates to script_lifecycle.run_script.
def fetch_delivery_agent_statuses(ss):
    ss.fetched_delivery_agent_statuses = None
    ss.da_status_fetch_message = None

    if not ss.get("py4j_gateway_object"):
        msg = "JADE Gateway not available. Cannot fetch DA statuses. Ensure JADE is running."
        ss.da_status_fetch_message = msg
        return {'type': 'error', 'message': msg}
    
    if not ss.get("jade_agents_created"):
        msg = "JADE MRA not created. Please create agents first to fetch DA statuses."
        ss.da_status_fetch_message = msg
        return {'type': 'error', 'message': msg}

    mra_name = execution_logic.DEFAULT_MRA_NAME
    
    try:
        # This function now returns a JSON string like {"delivery_agent_statuses": [...]}
        da_statuses_json_str, error_msg = py4j_gateway.get_compiled_optimization_data_from_mra(ss.py4j_gateway_object, mra_name)

        if error_msg:
            msg = f"Failed to get DA statuses from MRA '{mra_name}': {error_msg}"
            ss.da_status_fetch_message = msg
            return {'type': 'error', 'message': msg}
        if not da_statuses_json_str:
            msg = f"MRA '{mra_name}' returned no data for DA statuses."
            ss.da_status_fetch_message = msg
            return {'type': 'warning', 'message': msg}
        
        import json
        try:
            parsed_json = json.loads(da_statuses_json_str)
            if isinstance(parsed_json, dict) and "delivery_agent_statuses" in parsed_json:
                ss.fetched_delivery_agent_statuses = parsed_json["delivery_agent_statuses"]
                if not isinstance(ss.fetched_delivery_agent_statuses, list):
                    msg = f"MRA '{mra_name}' returned 'delivery_agent_statuses' but it's not a list. Data: {da_statuses_json_str[:200]}"
                    ss.da_status_fetch_message = msg
                    ss.fetched_delivery_agent_statuses = None # Clear if invalid format
                    return {'type': 'error', 'message': msg}
            else:
                msg = f"MRA returned JSON but without 'delivery_agent_statuses' key. Data: {da_statuses_json_str[:200]}" # Removed MRA name from msg
                ss.da_status_fetch_message = msg
                return {'type': 'error', 'message': msg}
        except json.JSONDecodeError as json_e:
            msg = f"MRA '{mra_name}' returned invalid JSON for DA statuses: {str(json_e)}. Data: {da_statuses_json_str[:200]}"
            ss.da_status_fetch_message = msg
            return {'type': 'error', 'message': msg}

        msg = "DA statuses successfully fetched" # Changed message
        ss.da_status_fetch_message = msg
        return {'type': 'info', 'message': msg} # Changed from success to info

    except Exception as e:
        msg = f"An unexpected error occurred while fetching DA statuses from MRA: {str(e)}"
        ss.da_status_fetch_message = msg
        return {'type': 'error', 'message': msg}

def run_optimisation_script(ss):
    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.optimisation_execution_tab_run_status_message = None

    if not ss.get("optimisation_script_loaded_successfully"):
        msg = "Optimisation script not loaded. Please load a script in the 'Optimisation' tab."
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}

    # Use ss.data_for_optimisation_script which comes from MRA's TriggerOptimisationCycle
    # This bundle already contains warehouse, parcels, and delivery_agents (statuses)
    input_data_from_mra = ss.get("data_for_optimisation_script")

    if not isinstance(input_data_from_mra, dict) or not input_data_from_mra:
        msg = "Optimisation data from MRA is missing or invalid. Please ensure MRA prepared data."
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}
    
    # Validate essential keys expected by script_lifecycle.run_script
    # MRA's OptimisationDataBundle should contain "warehouse_coordinates_x_y", "parcels", and "delivery_agents".
    missing_keys = []
    if "parcels" not in input_data_from_mra:
        missing_keys.append("parcels")
    if "warehouse_coordinates_x_y" not in input_data_from_mra:
        missing_keys.append("warehouse_coordinates_x_y")
    if "delivery_agents" not in input_data_from_mra: # MRA provides this key directly
        missing_keys.append("delivery_agents")
    
    if missing_keys:
        msg = f"MRA data bundle is missing essential keys: {', '.join(missing_keys)}. Cannot run optimisation."
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}

    import json
    try:
        current_input_data_json_str = json.dumps(input_data_from_mra)
    except Exception as e_json:
        msg = f"Error serializing MRA data to JSON for script: {str(e_json)}"
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}

    script_lifecycle.run_script(
        ss, 
        current_input_data_json_str, # Pass the newly constructed JSON string
        ss.optimisation_script_user_values
    )

    if ss.get("optimisation_run_error"):
        msg = f"Optimisation script execution failed: {ss.optimisation_run_error}"
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}
    elif ss.get("optimisation_run_complete"): # This is set by script_lifecycle.run_script
        # script_lifecycle.run_script also sets ss.optimisation_results
        if ss.get("optimisation_results") is None:
            msg = "Optimisation completed but returned no results"
            ss.optimisation_execution_tab_run_status_message = msg
            return {
                'type': 'warning', 
                'message': msg,
                'results': None # Explicitly indicate no results in the return dict
            }
        else:
            msg = "Optimisation completed successfully"
            ss.optimisation_execution_tab_run_status_message = msg
            return {
                'type': 'success', # Changed to 'success' to better reflect completion with results
                'message': msg,
                'results': ss.get("optimisation_results") # Ensure we get from ss
            }
    else:
        msg = "Optimisation did not complete"
        ss.optimisation_execution_tab_run_status_message = msg
        return {'type': 'error', 'message': msg}

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
