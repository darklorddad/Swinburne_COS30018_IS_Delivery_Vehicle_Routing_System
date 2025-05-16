from . import jade_controller 

# Default JADE agent names and classes
DEFAULT_MRA_NAME = "MRA"
DEFAULT_MRA_CLASS = "MasterRoutingAgent" # Updated package
DEFAULT_DA_CLASS = "DeliveryAgent"     # Updated package

def initialise_session_state(ss):
    if "execution_module_initialised_v1" not in ss: # Use a versioned key
        ss.execution_module_initialised_v1 = True
        
        ss.jade_platform_running = False
        ss.jade_platform_status_message = None
        ss.jade_agents_created = False
        ss.jade_agent_creation_status_message = None
        ss.jade_dispatch_status_message = None # Renamed from jade_execution_status_message
        
        # Store JADE process info (e.g., Popen object from subprocess or simulated dict)
        ss.jade_process_info = None 
        # Store Py4J gateway object if used
        ss.py4j_gateway_object = None 
        # Event to stop JADE log reader threads
        ss.jade_log_stop_event = None

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
    success, message, process_obj, gateway_obj, log_stop_event = jade_controller.start_jade_platform()
    
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
    ss.jade_dispatch_status_message = None # Renamed

def handle_create_agents(ss):
    if not ss.get("jade_platform_running"):
        ss.jade_agent_creation_status_message = "Cannot create agents: JADE is not running"
        ss.jade_agents_created = False
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

    # Compilation is now handled by handle_start_jade.
    # We assume if the platform is running, compilation was successful.
    
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

    # Create MRA
    mra_success, mra_msg = jade_controller.create_mra_agent(
        py4j_gateway, # Pass the gateway object
        DEFAULT_MRA_NAME,
        DEFAULT_MRA_CLASS,
        ss.config_data 
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
            final_message = f"Routes dispatched to {len(delivery_agents_config)} agents via MRA"
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'success', 'message': final_message}
    else:
        final_message = "Agent creation partially failed. MRA may be created, but errors occurred with Delivery Agents. Details: " + " | ".join(da_creation_messages)
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'error', 'message': final_message}


def handle_trigger_mra_processing(ss): # Renamed from handle_dispatch_routes
    if not ss.get("jade_platform_running"):
        ss.jade_dispatch_status_message = "Cannot trigger MRA processing: JADE is not running"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
    
    py4j_gateway = ss.get("py4j_gateway_object")
    if not py4j_gateway:
        ss.jade_dispatch_status_message = "Cannot trigger MRA processing: Py4J Gateway to JADE is not available"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
        
    if not ss.get("jade_agents_created"):
        ss.jade_dispatch_status_message = "Cannot trigger MRA processing: Agents have not been created in JADE"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
    if not ss.get("optimisation_run_complete") or not ss.get("optimisation_results"):
        ss.jade_dispatch_status_message = "Cannot trigger MRA processing: Optimisation results not available. Please run optimisation in the 'Optimisation' tab first"
        return {'type': 'warning', 'message': ss.jade_dispatch_status_message}

    optimisation_results = ss.optimisation_results

    # Send full optimisation results to MRA via Py4jGatewayAgent
    success, message = jade_controller.send_optimisation_results_to_mra(
        py4j_gateway,
        DEFAULT_MRA_NAME, # Name of the MRA agent in JADE
        optimisation_results
    )

    if success:
        ss.jade_dispatch_status_message = message or "Optimisation results sent to MRA for processing and dispatch"
        return {'type': 'success', 'message': ss.jade_dispatch_status_message}
    else:
        ss.jade_dispatch_status_message = message or "Failed to send optimisation results to MRA"
        return {'type': 'error', 'message': ss.jade_dispatch_status_message}
