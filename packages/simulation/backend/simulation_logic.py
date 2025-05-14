from . import jade_controller 

# Default JADE agent names and classes (placeholders)
DEFAULT_MRA_NAME = "MasterRouter"
DEFAULT_MRA_CLASS = "dld.jadeagents.MasterRoutingAgent" # Example Java class path
DEFAULT_DA_CLASS = "dld.jadeagents.DeliveryAgent"     # Example Java class path

def initialise_session_state(ss):
    if "simulation_module_initialised_v1" not in ss: # Use a versioned key
        ss.simulation_module_initialised_v1 = True
        
        ss.jade_platform_running = False
        ss.jade_platform_status_message = None
        ss.jade_agents_created = False
        ss.jade_agent_creation_status_message = None
        ss.jade_simulation_status_message = None
        
        # Store JADE process info (e.g., Popen object from subprocess or simulated dict)
        ss.jade_process_info = None 
        # Store Py4J gateway object if used
        ss.py4j_gateway_object = None # Renamed to avoid conflict if 'gateway' is a common var name

def handle_start_jade(ss):
    if ss.get("jade_platform_running", False):
        ss.jade_platform_status_message = "JADE platform is already running."
        return

    # start_jade_platform now returns: success, message, process_obj, gateway_obj
    success, message, process_obj, gateway_obj = jade_controller.start_jade_platform()
    
    ss.jade_platform_status_message = message # Store the detailed message from start_jade_platform

    if success: # JADE process started (Py4J connection might have succeeded or failed, message reflects this)
        ss.jade_platform_running = True # Mark platform as "running" if process started
        ss.jade_process_info = process_obj
        if gateway_obj:
            ss.py4j_gateway_object = gateway_obj
            # Message already includes Py4J status, no need to overwrite here unless adding more info
        else:
            ss.py4j_gateway_object = None
            # Message from start_jade_platform should indicate Py4J failure if process_obj is not None
    else: # JADE process failed to start
        ss.jade_platform_running = False
        ss.jade_process_info = None # Ensure process_info is None if start failed
        ss.jade_platform_status_message = message or "Failed to start JADE platform."
    
    # Reset downstream states as platform state changed
    ss.jade_agents_created = False
    ss.jade_agent_creation_status_message = None
    ss.jade_simulation_status_message = None

def handle_stop_jade(ss):
    if not ss.get("jade_platform_running", False):
        ss.jade_platform_status_message = "JADE platform is not running."
        return

    success, message = jade_controller.stop_jade_platform(ss.get("jade_process_info"), ss.get("py4j_gateway_object"))
    if success:
        ss.jade_platform_running = False
        ss.jade_process_info = None
        ss.py4j_gateway_object = None
        ss.jade_platform_status_message = message or "JADE platform stopped successfully."
    else:
        # If stop fails, the platform might still be considered running or in an indeterminate state.
        # For simulation, we'll assume it failed to stop and remains "running" to reflect the error.
        ss.jade_platform_status_message = message or "Failed to stop JADE platform."
    
    # Reset downstream states
    ss.jade_agents_created = False
    ss.jade_agent_creation_status_message = None
    ss.jade_simulation_status_message = None

def handle_create_agents(ss):
    if not ss.get("jade_platform_running"):
        ss.jade_agent_creation_status_message = "Cannot create agents: JADE platform is not running."
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}
    
    py4j_gateway = ss.get("py4j_gateway_object")
    if not py4j_gateway:
        ss.jade_agent_creation_status_message = "Cannot create agents: Py4J Gateway to JADE is not available. Ensure JADE started with Py4J support."
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

    if not ss.config_data:
        ss.jade_agent_creation_status_message = "Cannot create agents: Configuration data not loaded."
        return {'type': 'error', 'message': ss.jade_agent_creation_status_message}

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

    # Create DAs
    da_creation_messages = [f"MRA '{DEFAULT_MRA_NAME}' creation: {mra_msg}"]
    all_das_successfully_created = True
    delivery_agents_config = ss.config_data.get("delivery_agents", [])

    if not delivery_agents_config:
         da_creation_messages.append("No delivery agents found in configuration to create.")
    else:
        for agent_config in delivery_agents_config:
            da_id = agent_config.get("id")
            if not da_id:
                da_creation_messages.append("Skipping DA with no ID in configuration.")
                all_das_successfully_created = False # Consider this a partial failure
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
    
    if mra_success and all_das_successfully_created:
        ss.jade_agents_created = True
        final_message = "All agents (MRA and DAs) processed for creation (simulated). Details: " + " | ".join(da_creation_messages)
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'success', 'message': final_message}
    else:
        ss.jade_agents_created = False
        final_message = "One or more agents failed to be created (simulated). Details: " + " | ".join(da_creation_messages)
        ss.jade_agent_creation_status_message = final_message
        return {'type': 'error', 'message': final_message}


def handle_run_simulation(ss):
    if not ss.get("jade_platform_running"):
        ss.jade_simulation_status_message = "Cannot run simulation: JADE platform is not running."
        return {'type': 'error', 'message': ss.jade_simulation_status_message}
    
    py4j_gateway = ss.get("py4j_gateway_object")
    if not py4j_gateway:
        ss.jade_simulation_status_message = "Cannot run simulation: Py4J Gateway to JADE is not available."
        return {'type': 'error', 'message': ss.jade_simulation_status_message}
        
    if not ss.get("jade_agents_created"):
        ss.jade_simulation_status_message = "Cannot run simulation: Agents have not been created in JADE."
        return {'type': 'error', 'message': ss.jade_simulation_status_message}
    if not ss.get("optimisation_run_complete") or not ss.get("optimisation_results"):
        ss.jade_simulation_status_message = "Cannot run simulation: Optimisation results not available. Please run optimisation in the 'Optimisation' tab first."
        return {'type': 'warning', 'message': ss.jade_simulation_status_message}

    optimisation_results = ss.optimisation_results

    # Tell the MRA in JADE to start the process, passing it the optimisation_results.
    success, message = jade_controller.trigger_mra_optimisation_and_notify_das(
        py4j_gateway, # Pass the gateway object
        DEFAULT_MRA_NAME, # Name of the MRA agent in JADE
        optimisation_results
    )

    if success:
        ss.jade_simulation_status_message = message or "JADE simulation triggered successfully."
        return {'type': 'success', 'message': ss.jade_simulation_status_message}
    else:
        ss.jade_simulation_status_message = message or "Failed to trigger JADE simulation."
        return {'type': 'error', 'message': ss.jade_simulation_status_message}
