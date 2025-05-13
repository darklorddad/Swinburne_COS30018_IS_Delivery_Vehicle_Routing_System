
import importlib.util
import sys
import os
import tempfile # For temporary file creation
import shutil # For removing temp directory

# Helper to load a Python script content as a module.
# Manages temporary file creation and basic module loading.
def _load_module_from_string(script_content, module_name_prefix="user_opt_script"):
    temp_dir = tempfile.mkdtemp()
    module_name = f"{module_name_prefix}_{os.path.basename(temp_dir)}" # Unique module name
    temp_file_path = os.path.join(temp_dir, f"{module_name}.py")

    try:
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        spec = importlib.util.spec_from_file_location(module_name, temp_file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_name}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module # Add to sys.modules before exec_module
        
        spec.loader.exec_module(module)
    except Exception as e:
        # If any error occurs during file writing, spec creation, or module execution,
        # ensure cleanup of the temp directory and module from sys.modules.
        if module_name in sys.modules:
            del sys.modules[module_name]
        if os.path.isdir(temp_dir): # Check if temp_dir was created
            shutil.rmtree(temp_dir)
        raise e # Re-raise the original exception

    # Return module, its name, and temp_dir for caller to manage (especially for cleanup)
    return module, module_name, temp_dir


def initialise_session_state(ss):
    # Use a new key to ensure this initialisation logic runs if old state exists.
    if "optimisation_module_initialised_v2" not in ss:
        ss.optimisation_module_initialised_v2 = True
        
        # State for uploaded optimisation script
        ss.optimisation_script_content = None
        ss.optimisation_script_filename = None
        ss.optimisation_script_param_schema = None # Schema extracted from the script
        ss.optimisation_script_user_values = {} # User-defined values for the script's parameters
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

# Cleans up resources (temp directory, loaded module) from a previously loaded script (schema module).
def _cleanup_previous_schema_script(ss):
    if ss.optimisation_script_module_name_schema and ss.optimisation_script_module_name_schema in sys.modules:
        del sys.modules[ss.optimisation_script_module_name_schema]
    if ss.optimisation_script_temp_dir_schema and os.path.isdir(ss.optimisation_script_temp_dir_schema):
        shutil.rmtree(ss.optimisation_script_temp_dir_schema)
    
    ss.optimisation_script_temp_dir_schema = None
    ss.optimisation_script_module_name_schema = None

# Handles the upload of an optimisation script.
def handle_optimisation_file_upload(ss):
    _cleanup_previous_schema_script(ss) # Clean up any old script resources first.

    # Key for the file uploader widget, defined in the UI.
    uploaded_file = ss.get("optimisation_file_uploader_widget") 

    if uploaded_file is None:
        # This might be called if the file is cleared from UI; ensure state is reset.
        # However, explicit clear via button is preferred. If called with no file, reset.
        clear_optimisation_script(ss) # Call full clear to be safe
        return

    try:
        file_content_bytes = uploaded_file.getvalue()
        file_content = file_content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        ss.optimisation_script_error_message = "Error: Uploaded file is not UTF-8 encoded."
        ss.optimisation_script_loaded_successfully = False
        return
    except Exception as e:
        ss.optimisation_script_error_message = f"Error reading uploaded file: {str(e)}"
        ss.optimisation_script_loaded_successfully = False
        return

    # Reset relevant state variables before processing the new file.
    ss.optimisation_script_content = file_content
    ss.optimisation_script_filename = uploaded_file.name
    ss.optimisation_script_param_schema = None
    ss.optimisation_script_user_values = {}
    ss.optimisation_script_loaded_successfully = False
    ss.optimisation_script_error_message = None
    ss.optimisation_results = None 
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None

    module = None
    module_name = None
    temp_dir = None
    try:
        module, module_name, temp_dir = _load_module_from_string(ss.optimisation_script_content, "user_schema_script")
        # Store these to be cleaned up later by _cleanup_previous_schema_script or clear_optimisation_script
        ss.optimisation_script_temp_dir_schema = temp_dir
        ss.optimisation_script_module_name_schema = module_name

        if hasattr(module, "get_params_schema") and callable(module.get_params_schema):
            schema = module.get_params_schema()
            if isinstance(schema, dict) and "parameters" in schema and isinstance(schema["parameters"], list):
                ss.optimisation_script_param_schema = schema
                for param_info in schema.get("parameters", []):
                    if "name" in param_info:
                        ss.optimisation_script_user_values[param_info["name"]] = param_info.get("default")
                ss.optimisation_script_loaded_successfully = True
            else:
                ss.optimisation_script_error_message = "Script's get_params_schema() returned an invalid format. Expected a dictionary with a 'parameters' list."
        else:
            ss.optimisation_script_error_message = "Script must contain a callable 'get_params_schema()' function."
        
        if ss.optimisation_script_loaded_successfully:
            ss.optimisation_action_selected = None # Return to initial view on success
            
    except Exception as e:
        ss.optimisation_script_error_message = f"Error loading script or getting schema: {str(e)}"
        # If module loading failed, _load_module_from_string should have cleaned up its own temp_dir and sys.modules entry.
        # Ensure ss state for these are also None.
        # Keep user on load_script view by not changing ss.optimisation_action_selected
        ss.optimisation_script_temp_dir_schema = None
        ss.optimisation_script_module_name_schema = None
        ss.optimisation_script_loaded_successfully = False


# Executes the loaded optimisation script.
def execute_optimisation_script(ss):
    if not ss.optimisation_script_loaded_successfully: # ss.optimisation_script_content would be set if loaded_successfully is True.
        ss.optimisation_run_error = "Optimisation script not loaded successfully. Please upload a valid script."
        ss.optimisation_run_complete = False
        return
    
    if not ss.config_data:
        ss.optimisation_run_error = "Configuration data not loaded. Please load a configuration in the 'Configuration' tab first."
        ss.optimisation_run_complete = False
        return

    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None

    exec_module = None
    exec_module_name = None
    exec_temp_dir = None
    try:
        # Load the script into a new, separate module for execution to ensure isolation.
        exec_module, exec_module_name, exec_temp_dir = _load_module_from_string(ss.optimisation_script_content, "user_exec_script")

        if hasattr(exec_module, "run_optimisation") and callable(exec_module.run_optimisation):
            results = exec_module.run_optimisation(ss.config_data, ss.optimisation_script_user_values)
            ss.optimisation_results = results
            ss.optimisation_run_complete = True
        else:
            ss.optimisation_run_error = "Script must contain a callable 'run_optimisation(config_data, params)' function."
            
    except Exception as e:
        ss.optimisation_run_error = f"Error executing optimisation script: {str(e)}"
    finally:
        # Clean up the module and temp directory created specifically for this execution.
        if exec_module_name and exec_module_name in sys.modules:
            del sys.modules[exec_module_name]
        if exec_temp_dir and os.path.isdir(exec_temp_dir):
            shutil.rmtree(exec_temp_dir)

# Clears all state related to the optimisation script.
def clear_optimisation_script(ss):
    _cleanup_previous_schema_script(ss) # Clean up schema module and temp files.

    ss.optimisation_script_content = None
    ss.optimisation_script_filename = None
    ss.optimisation_script_param_schema = None
    ss.optimisation_script_user_values = {}
    ss.optimisation_script_loaded_successfully = False
    ss.optimisation_script_error_message = None
    
    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.optimisation_run_error = None
    
    # Reset the file uploader widget by setting its session state key to None.
    # This should make the uploader appear empty on the next UI rerun.
    if "optimisation_file_uploader_widget" in ss: # Key used in the UI.
        ss.optimisation_file_uploader_widget = None
    
    ss.optimisation_action_selected = None # Reset to initial view


# --- Optimisation Tab View Management ---

# Switches to the script loading view.
def handle_initiate_load_script_action(ss):
    ss.optimisation_action_selected = "load_script"
    # Clear any previous error messages when initiating a new load action
    ss.optimisation_script_error_message = None 

# Handles cancelling the script loading process.
def handle_cancel_load_script_action(ss):
    ss.optimisation_action_selected = None
    # Clear the file uploader widget buffer if a file was selected but not loaded
    if "optimisation_file_uploader_widget" in ss:
        ss.optimisation_file_uploader_widget = None
    # Clear any error messages from a failed load attempt
    ss.optimisation_script_error_message = None
    
    ss.optimisation_action_selected = None # Reset to initial view
