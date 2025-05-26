# This module handles the core lifecycle of an optimisation script:
# loading, schema extraction, execution, and data clearing.
# It updates session state (ss) directly with script-related data and errors.

import copy
from . import script_utils

# Helper to clean up resources from a previously loaded script (schema module).
# (Moved and adapted from optimisation_logic.py)
def _cleanup_previous_schema_script(ss):
    script_utils.cleanup_script_module(
        ss.get("optimisation_script_module_name_schema"), # Use .get for safety
        ss.get("optimisation_script_temp_dir_schema")
    )
    ss.optimisation_script_temp_dir_schema = None
    ss.optimisation_script_module_name_schema = None

# Loads an optimisation script from an uploaded file, extracts its schema, and sets up parameters.
# Updates session state (ss) with script content, schema, default parameters, and any errors.
# Returns:
#   bool: True if script loaded and processed successfully, False otherwise.
def load_and_process_script(ss, uploaded_file):
    _cleanup_previous_schema_script(ss) 

    if uploaded_file is None:
        # Reset script state if no file is provided (e.g., user cleared uploader)
        # The calling function in optimisation_logic might also clear broader state.
        ss.optimisation_script_content = None
        ss.optimisation_script_filename = None
        ss.optimisation_script_param_schema = None
        ss.optimisation_script_user_values = {}
        ss.optimisation_script_user_values_snapshot = {}
        ss.optimisation_script_loaded_successfully = False
        ss.optimisation_script_error_message = "No file provided for loading."
        ss.optimisation_results = None 
        ss.optimisation_run_complete = False
        ss.optimisation_run_error = None
        return False

    try:
        file_content_bytes = uploaded_file.getvalue()
        file_content = file_content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        ss.optimisation_script_error_message = "Error: Uploaded file is not UTF-8 encoded."
        ss.optimisation_script_loaded_successfully = False
        return False
    except Exception as e:
        ss.optimisation_script_error_message = f"Error reading uploaded file: {str(e)}"
        ss.optimisation_script_loaded_successfully = False
        return False

    # Reset relevant state variables before processing the new file.
    ss.optimisation_script_content = file_content
    ss.optimisation_script_filename = uploaded_file.name
    ss.optimisation_script_param_schema = None
    ss.optimisation_script_user_values = {}
    ss.optimisation_script_user_values_snapshot = {} 
    ss.optimisation_script_loaded_successfully = False
    ss.optimisation_script_error_message = None
    ss.optimisation_results = None 
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None

    module = None
    module_name = None
    temp_dir = None
    try:
        # Use a distinct prefix for schema loading module name
        module, module_name, temp_dir = script_utils._load_module_from_string(
            ss.optimisation_script_content, 
            "user_schema_script" 
        )
        ss.optimisation_script_temp_dir_schema = temp_dir
        ss.optimisation_script_module_name_schema = module_name

        if hasattr(module, "get_params_schema") and callable(module.get_params_schema):
            schema = module.get_params_schema()
            if isinstance(schema, dict) and "parameters" in schema and isinstance(schema["parameters"], list):
                ss.optimisation_script_param_schema = schema
                # Populate default values
                for param_info in schema.get("parameters", []):
                    if "name" in param_info:
                        ss.optimisation_script_user_values[param_info["name"]] = param_info.get("default")
                ss.optimisation_script_loaded_successfully = True
                return True 
            else:
                ss.optimisation_script_error_message = "Script's get_params_schema() returned an invalid format. Expected a dictionary with a 'parameters' list."
        else:
            ss.optimisation_script_error_message = "Script must contain a callable 'get_params_schema()' function."
        
    except Exception as e:
        ss.optimisation_script_error_message = f"Error loading script or getting schema: {str(e)}"
        # Ensure cleanup if module loading itself failed partially
        if module_name and module_name in __import__('sys').modules:
            del __import__('sys').modules[module_name]
        if temp_dir and __import__('os').path.isdir(temp_dir):
            __import__('shutil').rmtree(temp_dir)
        ss.optimisation_script_temp_dir_schema = None # Ensure reset
        ss.optimisation_script_module_name_schema = None # Ensure reset
    
    ss.optimisation_script_loaded_successfully = False
    return False

# Executes the loaded optimisation script with the current configuration and parameters.
# Updates session state (ss) with results or errors.
def run_script(ss, mra_compiled_data_json_str, user_params):
    if not ss.get("optimisation_script_loaded_successfully"): 
        ss.optimisation_run_error = "Optimisation script not loaded successfully. Please upload a valid script."
        ss.optimisation_run_complete = False
        return
    
    if not mra_compiled_data_json_str:
        ss.optimisation_run_error = "No compiled data received from MRA for optimisation."
        ss.optimisation_run_complete = False
        return

    try:
        import json
        optimisation_input_data = json.loads(mra_compiled_data_json_str)
        
        # Transform data key for compatibility:
        # If "delivery_agent_statuses" exists and "delivery_agents" does not,
        # rename "delivery_agent_statuses" to "delivery_agents"
        if ("delivery_agent_statuses" in optimisation_input_data and 
            "delivery_agents" not in optimisation_input_data):
            optimisation_input_data["delivery_agents"] = optimisation_input_data.pop("delivery_agent_statuses")
            
        # Transform agent's 'agent_id' key to 'id' for compatibility
        if "delivery_agents" in optimisation_input_data and isinstance(optimisation_input_data["delivery_agents"], list):
            for agent_info in optimisation_input_data["delivery_agents"]:
                if isinstance(agent_info, dict) and "agent_id" in agent_info and "id" not in agent_info:
                    agent_info["id"] = agent_info.pop("agent_id")
            
    except Exception as e:
        ss.optimisation_run_error = f"Error parsing MRA compiled data JSON: {str(e)}"
        return

    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None

    exec_module = None
    exec_module_name = None
    exec_temp_dir = None
    try:
        # Load the script into a new, separate module for execution
        exec_module, exec_module_name, exec_temp_dir = script_utils._load_module_from_string(
            ss.optimisation_script_content, 
            "user_exec_script"
        )

        if hasattr(exec_module, "run_optimisation") and callable(exec_module.run_optimisation):
            # Pass deepcopies of the data and parameters to the user script.
            # This ensures the script gets a clean, isolated copy and prevents
            # accidental modification of shared data structures.
            cloned_input_data = copy.deepcopy(optimisation_input_data)
            cloned_user_params = copy.deepcopy(user_params)
            results = exec_module.run_optimisation(cloned_input_data, cloned_user_params)
            ss.optimisation_results = results
            ss.optimisation_run_complete = True
        else:
            ss.optimisation_run_error = "Script must contain a callable 'run_optimisation(config_data, params)' function."
            
    except Exception as e:
        ss.optimisation_run_error = f"Error executing optimisation script: {str(e)}"
    finally:
        # Clean up the module and temp directory created specifically for this execution.
        script_utils.cleanup_script_module(exec_module_name, exec_temp_dir)

# Clears data related to the currently loaded optimisation script from session state.
# This does not handle UI navigation state like 'optimisation_action_selected'.
def clear_script_data(ss):
    _cleanup_previous_schema_script(ss) 

    ss.optimisation_script_content = None
    ss.optimisation_script_filename = None
    ss.optimisation_script_param_schema = None
    ss.optimisation_script_user_values = {}
    ss.optimisation_script_user_values_snapshot = {} 
    ss.optimisation_script_loaded_successfully = False
    ss.optimisation_script_error_message = None
    
    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None
