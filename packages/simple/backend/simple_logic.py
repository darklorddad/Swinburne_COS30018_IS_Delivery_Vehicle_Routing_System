import streamlit
import random
import copy
from packages.configuration.backend.state_management import DEFAULT_CONFIG_TEMPLATE, _stash_current_config_as_fallback
from packages.configuration.backend.config_logic import clear_config_from_memory
from packages.execution.backend import execution_logic
from packages.optimisation.backend import optimisation_logic
import os

def _scan_featured_scripts(ss):
    """Scans pnp/featured directory for Python scripts and stores them in session state"""
    featured_dir = os.path.join("pnp", "featured")
    if not os.path.exists(featured_dir):
        ss.featured_optimisation_scripts = []
        return
    
    try:
        files = os.listdir(featured_dir)
        ss.featured_optimisation_scripts = [
            f for f in files 
            if f.endswith('.py') and os.path.isfile(os.path.join(featured_dir, f))
        ]
    except Exception as e:
        print(f"Error scanning featured scripts: {e}")
        ss.featured_optimisation_scripts = []

def generate_quick_config(ss, num_parcels, num_agents, config_name="generated-config"):
    """
    Generates a new configuration with the specified number of parcels and delivery agents,
    and loads it into the session state.
    """
    if not isinstance(num_parcels, int) or num_parcels < 0:
        return {'type': 'error', 'message': 'Number of parcels must be a non-negative integer.'}
    if not isinstance(num_agents, int) or num_agents < 0:
        return {'type': 'error', 'message': 'Number of delivery agents must be a non-negative integer.'}

    # Stash current config as fallback before creating new one
    _stash_current_config_as_fallback(ss)

    new_config = copy.deepcopy(DEFAULT_CONFIG_TEMPLATE)
    new_config["parcels"] = []
    new_config["delivery_agents"] = []

    # Generate parcels
    for i in range(num_parcels):
        new_config["parcels"].append({
            "id": f"P{str(i+1).zfill(3)}",
            "coordinates_x_y": [random.randint(-20, 20), random.randint(-20, 20)],
            "weight": random.randint(1, 20)
        })

    # Generate delivery agents
    for i in range(num_agents):
        new_config["delivery_agents"].append({
            "id": f"DA{str(i+1).zfill(2)}",
            "capacity_weight": random.choice([50, 75, 100])
        })
    
    new_config["warehouse_coordinates_x_y"] = [0,0] # Keep warehouse at default

    ss.config_data = new_config
    ss.config_filename = f"{config_name}.json" if config_name else "generated-config.json"
    ss.config_filename_snapshot = ss.config_filename
    ss.processed_file_id = None # It's a new, generated config, not from a file
    ss.last_uploaded_filename = None # Not from upload
    ss.action_selected = None
    ss.edit_mode = False # Generated config is not in edit mode by default
    ss.config_data_snapshot = copy.deepcopy(ss.config_data)
    ss.new_config_saved_to_memory_at_least_once = True # Considered saved to memory
    
    # Clear uploaded file buffer if any
    ss.uploaded_file_buffer = None
    ss.processed_file_id_for_buffer = None

    return {'type': 'success', 'message': f"Successfully generated and loaded configuration '{ss.config_filename}' with {num_parcels} parcels and {num_agents} agents."}

def handle_simple_mode_start_workflow(ss):
    """
    Handles the full automated workflow for simple mode:
    Start JADE, create agents, send config, run optimisation, send routes, get sim results.
    """
    ss.simple_workflow_messages = [] # To store messages from each step

    # --- Step 1: Start JADE Platform ---
    if not ss.get("jade_platform_running", False):
        execution_logic.handle_start_jade(ss)
        if not ss.get("jade_platform_running"):
            ss.simple_workflow_messages.append({'type': 'error', 'message': f"Failed to start JADE platform: {ss.get('jade_platform_status_message', 'Unknown error')}"})
            return
        ss.simple_workflow_messages.append({'type': 'success', 'message': "JADE platform started successfully."})
    else:
        ss.simple_workflow_messages.append({'type': 'info', 'message': "JADE platform already running."})

    # --- Step 2: Create Agents ---
    if not ss.get("jade_agents_created", False):
        result_agents = execution_logic.handle_create_agents(ss)
        ss.simple_workflow_messages.append(result_agents)
        if result_agents.get('type') == 'error':
            return
    else:
        ss.simple_workflow_messages.append({'type': 'info', 'message': "Agents were already marked as created."})

    # --- Step 3: Send Warehouse & Parcel Data to MRA ---
    result_send_config = execution_logic.handle_send_warehouse_parcel_data_to_mra(ss)
    ss.simple_workflow_messages.append(result_send_config)
    if result_send_config.get('type') == 'error':
        return

    # --- Step 4: Fetch Delivery Agent Statuses (to ensure MRA's cache is up-to-date) ---
    result_fetch_da_statuses = optimisation_logic.fetch_delivery_agent_statuses(ss)
    ss.simple_workflow_messages.append(result_fetch_da_statuses)
    if result_fetch_da_statuses.get('type') == 'error':
        return

    # --- Step 5: Trigger MRA Optimisation Cycle ---
    result_mra_data_prep = execution_logic.handle_trigger_mra_optimisation_cycle(ss)
    ss.simple_workflow_messages.append(result_mra_data_prep)
    if result_mra_data_prep.get('type') == 'error':
        return

    # --- Step 6: Run Python Optimisation Script ---
    result_script_run = optimisation_logic.run_optimisation_script(ss)
    ss.simple_workflow_messages.append(result_script_run)
    if result_script_run.get('type') == 'error' or not ss.get("optimisation_run_complete") or not ss.get("optimisation_results"):
        return

    # --- Step 7: Send Optimised Routes to MRA ---
    optimised_routes = ss.optimisation_results.get("optimised_routes")
    if optimised_routes:
        result_send_routes = execution_logic.handle_send_optimised_routes_to_mra(ss)
        ss.simple_workflow_messages.append(result_send_routes)
        if result_send_routes.get('type') == 'error':
            return
    else:
        ss.simple_workflow_messages.append({'type': 'info', 'message': "No optimised routes to send to MRA."})

    # --- Step 8: Fetch JADE Simulation Results ---
    if ss.get("routes_sent_to_mra_successfully", False) or not optimised_routes:
        result_fetch_sim = execution_logic.handle_get_simulated_routes_from_jade(ss)
        if result_fetch_sim and result_fetch_sim.get('message'):
             ss.simple_workflow_messages.append(result_fetch_sim)
        elif not result_fetch_sim:
            ss.simple_workflow_messages.append({'type': 'warning', 'message': "Fetching simulation results returned no explicit status."})

    ss.simple_workflow_messages.append({'type': 'success', 'message': "Automated workflow completed."})
