from . import jade_controller 
from . import py4j_gateway

# Default JADE agent names and classes
DEFAULT_MRA_NAME = "MRA"
DEFAULT_MRA_CLASS = "MasterRoutingAgent" # Updated package
DEFAULT_DA_CLASS = "DeliveryAgent"     # Updated package

def initialise_session_state(ss, clear_all_flag_for_other_modules=False): # Added dummy flag
    # If the init flag is not present (or if we were to implement a direct clear_all for this module),
    # proceed to initialize/reset all execution-specific states.
    # The dvrs.py will handle deleting this flag if a full reset is intended.
    if "execution_module_initialised_v1" not in ss: # Use a versioned key
        ss.execution_module_initialised_v1 = True
        
        ss.jade_platform_running = False
        ss.jade_platform_status_message = None
        ss.jade_agents_created = False
        ss.jade_agent_creation_status_message = None
        ss.jade_dispatch_status_message = None # Renamed from jade_execution_status_message
        ss.mra_config_subset_data = None # For warehouse/parcels from MRA
        ss.mra_config_subset_message = None
        ss.data_for_optimisation_script = None # Data bundle from MRA for script
        ss.mra_optimisation_trigger_message = None
        ss.routes_sent_to_mra_successfully = None

        # Store JADE process info (e.g., Popen object from subprocess or simulated dict)
        ss.jade_process_info = None 
        # Store Py4J gateway object if used
        ss.py4j_gateway_object = None 
        # Event to stop JADE log reader threads
        ss.jade_log_stop_event = None

        # Store the simulated routes data from JADE
        ss.jade_simulated_routes_data = None
        ss.jade_simulated_routes_message = None

def handle_start_jade(ss):
    if ss.get("jade_platform_running", False):
        ss.jade_platform_status_message = "JADE is already running"
        return

    # Attempt to compile Java agents first, before starting JADE.
    compile_success, compile_message = jade_controller.compile_java_agents()
    if not compile_success:
        ss.jade_platform_status_message = f"JADE startup failed: {compile_message}"
        # Ensure platform is marked as not running and clear related states
        ss.jade_platform_running = False
        ss.jade_process_info = None
        ss.py4j_gateway_object = None
        ss.jade_log_stop_event = None # Clear stop event
        ss.jade_agents_created = False # Reset as platform didn't start
        ss.jade_agent_creation_status_message = None
        ss.jade_dispatch_status_message = None 
        return

    # If compilation was successful, proceed with starting JADE.
    # start_jade_platform now returns: success, message, process_obj, gateway_obj, log_stop_event_obj
    is_simple_mode = ss.get("simple_mode", True) # Default to True to align with new app default
    success, message, process_obj, gateway_obj, log_stop_event = jade_controller.start_jade_platform(hide_gui=is_simple_mode)
    
    ss.jade_platform_status_message = message # Store the detailed message from start_jade_platform

    if success: # JADE process started (Py4J connection might have succeeded or failed, message reflects this)
        ss.jade_platform_running = True # Mark platform as "running" if process started
        ss.jade_process_info = process_obj
        ss.jade_log_stop_event = log_stop_event # Store the stop event
        if gateway_obj:
            ss.py4j_gateway_object = gateway_obj
        else:
            ss.py4j_gateway_object = None
    else: # JADE process failed to start
        ss.jade_platform_running = False
        ss.jade_process_info = None 
        ss.py4j_gateway_object = None
        ss.jade_log_stop_event = None # Clear stop event
        ss.jade_platform_status_message = message or "Failed to start JADE"
    
    # Reset downstream states as platform state changed
    ss.jade_agents_created = False
    ss.jade_agent_creation_status_message = None
    ss.jade_dispatch_status_message = None 
    ss.routes_sent_to_mra_successfully = False

def handle_stop_jade(ss):
    if not ss.get("jade_platform_running", False):
        ss.jade_platform_status_message = "JADE is not running"
        return

    success, message = jade_controller.stop_jade_platform(
        ss.get("jade_process_info"), 
        ss.get("py4j_gateway_object"),
        ss.get("jade_log_stop_event") # Pass the stop event
    )
    if success:
        ss.jade_platform_running = False
        ss.jade_process_info = None
        ss.py4j_gateway_object = None
        ss.jade_log_stop_event = None # Clear stop event
        ss.jade_platform_status_message = message or "JADE stopped successfully"
    else:
        # If stop fails, the platform might still be considered running or in an indeterminate state.
        # For execution, we'll assume it failed to stop and remains "running" to reflect the error.
        ss.jade_platform_status_message = message or "Failed to stop JADE"
    
    # Reset downstream states
    ss.jade_agents_created = False
    ss.jade_agent_creation_status_message = None
    ss.jade_dispatch_status_message = None
    ss.mra_config_subset_data = None
    ss.data_for_optimisation_script = None
    ss.jade_simulated_routes_data = None
    ss.jade_simulated_routes_message = None
    ss.routes_sent_to_mra_successfully = False

def handle_create_agents(ss):
    if not ss.get("jade_platform_running"):
        ss.jade_agent_creation_status_message = "Cannot create agents: JADE is not running"
        ss.jade_agents_created = False
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}
    
    py4j_gateway = ss.get("py4j_gateway_object")
    if not py4j_gateway:
        ss.jade_agent_creation_status_message = "Cannot create agents: Py4J Gateway to JADE is not available. Ensure JADE started with Py4J support"
        ss.jade_agents_created = False
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

    if not ss.config_data:
        ss.jade_agent_creation_status_message = "Cannot create agents: Configuration data not loaded"
        ss.jade_agents_created = False
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

    # Reset previous status for this operation
    ss.jade_agent_creation_status_message = None
    ss.jade_agents_created = False
    ss.routes_sent_to_mra_successfully = False

    # Create MRA - it starts "fresh" without initial full config
    mra_success, mra_msg = jade_controller.create_mra_agent(
        py4j_gateway, # Pass the gateway object
        DEFAULT_MRA_NAME,
        DEFAULT_MRA_CLASS,
        {} # Pass an empty dictionary, or a specific minimal set of args MRA might need for its own identity
    )

    if not mra_success:
        ss.jade_agents_created = False
        ss.jade_agent_creation_status_message = f"Failed to create MRA: {mra_msg}"
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

    # MRA creation was successful, now proceed with DAs
    da_creation_messages = [f"MRA '{DEFAULT_MRA_NAME}' creation: {mra_msg}"]
    all_required_agents_successfully_created = True
    delivery_agents_config = ss.config_data.get("delivery_agents", [])

    if not delivery_agents_config:
        da_creation_messages.append("No delivery agents found in configuration to create.")
    else:
        for agent_config in delivery_agents_config:
            da_id = agent_config.get("id")
            if not da_id:
                da_creation_messages.append(f"Skipping DA with no ID (config: {agent_config}).")
                all_required_agents_successfully_created = False
                continue

            da_success, da_msg = jade_controller.create_da_agent(
                py4j_gateway, # Pass the gateway object
                da_id, # Use DA ID from config as agent name
                DEFAULT_DA_CLASS,
                agent_config # Pass individual DA's config
            )
            da_creation_messages.append(f"DA '{da_id}': {da_msg}")
            if not da_success:
                all_das_successfully_created = False
    
    ss.jade_agents_created = all_required_agents_successfully_created

    if all_required_agents_successfully_created:
        if not delivery_agents_config:
            final_message = f"MRA '{DEFAULT_MRA_NAME}' created successfully. No delivery agents were configured."
        else:
            final_message = f"All agents created successfully"
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'success', 'message': final_message}
    else:
        final_message = "Agent creation partially failed. MRA may be created, but errors occurred with Delivery Agents. Details: " + " | ".join(da_creation_messages)
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'error', 'message': final_message}


def handle_send_optimised_routes_to_mra(ss): # Renamed from handle_trigger_mra_processing
    ss.jade_simulated_routes_data = None
    ss.jade_simulated_routes_message = None
    ss.routes_sent_to_mra_successfully = False
    ss.jade_dispatch_status_message = None

    if not ss.get("jade_platform_running"):
        ss.jade_dispatch_status_message = "Cannot send routes to MRA: JADE is not running"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
    
    py4j_gateway = ss.get("py4j_gateway_object")
    if not py4j_gateway:
        ss.jade_dispatch_status_message = "Cannot send routes to MRA: Py4J Gateway to JADE is not available"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
        
    if not ss.get("jade_agents_created"):
        ss.jade_dispatch_status_message = "Cannot send routes to MRA: Agents have not been created in JADE"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
    if not ss.get("optimisation_run_complete") or not ss.get("optimisation_results"):
        ss.jade_dispatch_status_message = "Cannot send routes to MRA: Optimisation results not available. Please run optimisation first."
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}

    optimisation_results = ss.optimisation_results
    # Send full optimisation results to MRA via Py4jGatewayAgent
    success, message = jade_controller.send_optimisation_results_to_mra(
        py4j_gateway,
        DEFAULT_MRA_NAME, # Name of the MRA agent in JADE
        optimisation_results
    )

    if success:
        ss.jade_dispatch_status_message = message or "Optimised routes sent to MRA for dispatch"
        ss.routes_sent_to_mra_successfully = True
        return {'type': 'info', 'message': ss.jade_dispatch_status_message}
    else:
        ss.jade_dispatch_status_message = message or "Failed to send optimised routes to MRA"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}

def handle_send_warehouse_parcel_data_to_mra(ss):
    """
    Called when user clicks "Send Warehouse & Parcel Data to MRA".
    Sends only warehouse and parcel data from Python's ss.config_data to the MRA.
    MRA will discover DAs via DF rather than receiving IDs from Python.
    """
    ss.mra_initialization_message = None 
    gateway = ss.get("py4j_gateway_object")
    mra_name = DEFAULT_MRA_NAME

    if not gateway:
        msg = "JADE Gateway not available. Cannot send warehouse/parcel data to MRA."
        ss.mra_initialization_message = msg
        return {'type': 'error', 'message': msg}
    if not ss.get("jade_agents_created"): # MRA must exist
        msg = "MRA not created. Cannot send warehouse/parcel data."
        ss.mra_initialization_message = msg
        return {'type': 'error', 'message': msg} 
    if not ss.config_data or \
       "parcels" not in ss.config_data or \
       "warehouse_coordinates_x_y" not in ss.config_data: 
        msg = "Required configuration (parcels, warehouse coordinates) not found in Python session state."
        ss.mra_initialization_message = msg
        return {'type': 'error', 'message': msg}

    warehouse_parcel_data = {
        "warehouse_coordinates_x_y": ss.config_data.get("warehouse_coordinates_x_y"),
        "parcels": ss.config_data.get("parcels")
        # DA information is explicitly omitted
    }
    import json
    warehouse_parcel_json = json.dumps(warehouse_parcel_data)

    success, message = py4j_gateway.send_warehouse_parcel_data_to_mra(gateway, mra_name, warehouse_parcel_json)
    if success:
        ss.mra_initialization_message = "Warehouse and parcel data sent successfully"
        return {'type': 'info', 'message': ss.mra_initialization_message}
    else:
        ss.mra_initialization_message = message
        return {'type': 'error', 'message': message}

def handle_trigger_mra_optimisation_cycle(ss):
    ss.data_for_optimisation_script = None # Clear previous data
    ss.mra_optimisation_trigger_message = None
    gateway = ss.get("py4j_gateway_object")
    mra_name = DEFAULT_MRA_NAME

    if not gateway:
        msg = "JADE Gateway not available. Cannot trigger MRA optimisation cycle."
        ss.mra_optimisation_trigger_message = msg
        return {'type': 'error', 'message': msg}
    if not ss.get("jade_agents_created"): # MRA must exist
        msg = "MRA not created. Cannot trigger MRA optimisation cycle."
        ss.mra_optimisation_trigger_message = msg
        return {'type': 'error', 'message': msg}

    json_data_bundle, err_msg = py4j_gateway.trigger_mra_optimisation_cycle(gateway, mra_name)

    if err_msg:
        ss.mra_optimisation_trigger_message = err_msg
        return {'type': 'error', 'message': err_msg}
    try:
        import json
        parsed_bundle = json.loads(json_data_bundle)
        # Check for our specific error key from MRA or a general error key from Py4jGatewayAgent
        if isinstance(parsed_bundle, dict) and \
           ("error_mra" in parsed_bundle or "error" in parsed_bundle): 
            error_detail = parsed_bundle.get("error_mra", parsed_bundle.get("error", "Unknown MRA error"))
            msg = f"MRA reported an issue during optimisation data preparation: {error_detail}"
            ss.mra_optimisation_trigger_message = msg
            return {'type': 'error', 'message': msg}
        ss.data_for_optimisation_script = parsed_bundle # Store the whole bundle
        ss.mra_optimisation_trigger_message = None
        return {'type': 'info', 'message': None}
    except Exception as e:
        msg = f"Error parsing optimisation data bundle from MRA: {str(e)}. Data: {json_data_bundle[:200]}"
        ss.mra_optimisation_trigger_message = msg
        return {'type': 'error', 'message': msg}

def handle_get_simulated_routes_from_jade(ss):
    ss.jade_simulated_routes_data = None
    ss.jade_simulated_routes_message = None

    gateway = ss.get("py4j_gateway_object")
    if not gateway:
        msg = "JADE Gateway not available. Cannot fetch simulated routes."
        ss.jade_simulated_routes_message = msg
        return {'type': 'error', 'message': msg}

    if not ss.get("jade_platform_running"):
        msg = "JADE platform is not running. Cannot fetch simulated routes."
        ss.jade_simulated_routes_message = msg
        return {'type': 'error', 'message': msg}

    routes_data, error_msg = py4j_gateway.get_jade_simulated_routes_data(gateway)

    if error_msg:
        ss.jade_simulated_routes_message = error_msg
        # routes_data would be None in this case as per py4j_gateway.get_jade_simulated_routes_data
        return {'type': 'error', 'message': error_msg}
    
    # If no error, routes_data should be the parsed JSON (e.g., a list)
    ss.jade_simulated_routes_data = routes_data
    print(routes_data);
    if routes_data is not None and isinstance(routes_data, list): # Check if it's a list as expected
        msg = f"Successfully fetched {len(routes_data)} simulated routes from JADE."
        ss.jade_simulated_routes_message = msg
        return {'type': 'info', 'message': msg}
    elif routes_data is None:
        msg = "Fetched data from JADE, but it was null."
        ss.jade_simulated_routes_message = msg
        return {'type': 'warning', 'message': msg} # Or error
    else: # Data is not None, not a list, but no error_msg (unexpected state)
        msg = f"Fetched data from JADE, but it was not in the expected list format. Type: {type(routes_data)}"
        ss.jade_simulated_routes_message = msg
        return {'type': 'warning', 'message': msg}
