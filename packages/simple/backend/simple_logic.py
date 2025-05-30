import streamlit
import random
import copy
from packages.configuration.backend.state_management import DEFAULT_CONFIG_TEMPLATE, _stash_current_config_as_fallback
from packages.configuration.backend.config_logic import clear_config_from_memory
from packages.execution.backend import execution_logic
from packages.optimisation.backend import optimisation_logic
import os
import time

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

def calculate_and_store_basic_metrics(ss):
    """Calculates basic performance metrics and stores them in session state."""
    metrics = {}
    config_data = ss.get("config_data")
    optimisation_results = ss.get("optimisation_results")

    if not config_data or not ss.get("optimisation_run_complete") or not optimisation_results:
        ss.performance_metrics = {"error": "Optimisation did not complete or data is missing for metrics calculation."}
        return

    # 1. Input - Total Parcels
    total_parcels = len(config_data.get("parcels", []))
    metrics["total_parcels_configured"] = total_parcels

    # 2. Input - Total Agents
    metrics["total_agents_configured"] = len(config_data.get("delivery_agents", []))

    unassigned_parcels_details = optimisation_results.get("unassigned_parcels_details", [])
    optimised_routes = optimisation_results.get("optimised_routes", [])

    # 3. Optimisation Output - Parcels Assigned
    parcels_assigned = total_parcels - len(unassigned_parcels_details)
    metrics["parcels_assigned_for_delivery"] = parcels_assigned

    # 4. Optimisation Output - Percentage of Parcels Assigned
    metrics["percentage_parcels_assigned"] = round((parcels_assigned / total_parcels) * 100, 2) if total_parcels > 0 else 0.0

    # 5. Optimisation Output - Total Planned Distance
    metrics["total_planned_distance_units"] = round(sum(r.get("total_distance", 0) for r in optimised_routes), 2)

    # 6. Optimisation Output - Average Capacity Utilisation
    utilisations = [(r.get("total_weight", 0) / r.get("capacity_weight", 1)) for r in optimised_routes if r.get("capacity_weight", 0) > 0]
    metrics["average_capacity_utilisation_percentage"] = round((sum(utilisations) / len(utilisations)) * 100, 2) if utilisations else 0.0
        
    # 7. Optimisation Output - Number of Agents Utilised
    metrics["number_of_agents_utilised"] = len(optimised_routes)

    ss.performance_metrics = metrics

def handle_simple_mode_start_workflow(ss):
    """
    Handles the full automated workflow for simple mode:
    Start JADE, create agents, send config, run optimisation, send routes, get sim results.
    """
    ss.simple_workflow_messages = [] # To store messages from each step
    # Clear previous workflow messages and results before starting
    ss.simple_workflow_final_status = None 
    ss.optimisation_results = None
    ss.optimisation_run_complete = False
    ss.jade_simulated_routes_data = None
    ss.performance_metrics = None # Clear previous metrics

    def _log_step(step_name, result_dict):
        if result_dict and isinstance(result_dict, dict) and 'message' in result_dict:
            print(f"Simple Workflow - {step_name}: {result_dict.get('type','info').upper()} - {result_dict['message']}")
        elif isinstance(result_dict, str): # Fallback if a string is somehow passed
            print(f"Simple Workflow - {step_name}: INFO - {result_dict}")

    # --- Step 1: Start JADE Platform ---
    if not ss.get("jade_platform_running", False):
        execution_logic.handle_start_jade(ss)
        if not ss.get("jade_platform_running"):
            msg = f"Failed to start JADE platform: {ss.get('jade_platform_status_message', 'Unknown error')}"
            print(f"Simple Workflow - Step 1 ERROR: {msg}")
            ss.simple_workflow_final_status = {'type': 'error', 'message': msg}
            return
        _log_step("Step 1: Start JADE", {'type': 'success', 'message': "JADE platform started successfully."})
    else:
        _log_step("Step 1: Start JADE", {'type': 'info', 'message': "JADE platform already running."})

    # --- Step 2: Create Agents ---
    if not ss.get("jade_agents_created", False):
        result_agents = execution_logic.handle_create_agents(ss)
        _log_step("Step 2: Create Agents", result_agents)
        if result_agents.get('type') == 'error':
            ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed at Agent Creation: {result_agents.get('message')}"}
            return
    else:
        _log_step("Step 2: Create Agents", {'type': 'info', 'message': "Agents were already marked as created."})

    # --- Step 3: Send Warehouse & Parcel Data to MRA ---
    result_send_config = execution_logic.handle_send_warehouse_parcel_data_to_mra(ss)
    _log_step("Step 3: Send Config to MRA", result_send_config)
    if result_send_config.get('type') == 'error':
        ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed sending config to MRA: {result_send_config.get('message')}"}
        return

    # --- Step 4: Fetch Delivery Agent Statuses (to ensure MRA's cache is up-to-date) ---
    result_fetch_da_statuses = optimisation_logic.fetch_delivery_agent_statuses(ss)
    _log_step("Step 4: Fetch DA Statuses", result_fetch_da_statuses)
    if result_fetch_da_statuses.get('type') == 'error':
        ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed fetching DA statuses: {result_fetch_da_statuses.get('message')}"}
        return

    # --- Step 5: Trigger MRA Optimisation Cycle ---
    result_mra_data_prep = execution_logic.handle_trigger_mra_optimisation_cycle(ss)
    _log_step("Step 5: Trigger MRA Data Prep", result_mra_data_prep)
    if result_mra_data_prep.get('type') == 'error':
        ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed at MRA data preparation: {result_mra_data_prep.get('message')}"}
        return

    # --- Step 6: Run Python Optimisation Script ---
    result_script_run = optimisation_logic.run_optimisation_script(ss)
    _log_step("Step 6: Run Optimisation Script", result_script_run)
    if result_script_run.get('type') == 'error' or not ss.get("optimisation_run_complete") or not ss.get("optimisation_results"):
        er_msg = result_script_run.get('message', 'Script did not complete or return results.')
        ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed at Script Execution: {er_msg}"}
        return

    # --- Step 7: Send Optimised Routes to MRA ---
    optimised_routes = ss.optimisation_results.get("optimised_routes")
    if optimised_routes:
        result_send_routes = execution_logic.handle_send_optimised_routes_to_mra(ss)
        _log_step("Step 7: Send Routes to MRA", result_send_routes)
        time.sleep(1)
        if result_send_routes.get('type') == 'error':
            ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow failed sending routes to MRA: {result_send_routes.get('message')}"}
            return
    else:
        _log_step("Step 7: Send Routes to MRA", {'type': 'info', 'message': "No optimised routes to send to MRA."})

    # --- Step 8: Fetch JADE Simulation Results ---
    if ss.get("routes_sent_to_mra_successfully", False) or not optimised_routes:
        result_fetch_sim = execution_logic.handle_get_simulated_routes_from_jade(ss)
        _log_step("Step 8: Fetch Simulation Results", result_fetch_sim if result_fetch_sim else "No explicit status from fetch.")

    # --- Step 9: Stop JADE Platform ---
    # Calculate metrics before stopping JADE, as optimisation_results are needed
    if ss.get("optimisation_run_complete"):
        calculate_and_store_basic_metrics(ss)
    if ss.get("jade_platform_running", False):
        result_stop = execution_logic.handle_stop_jade(ss)
        if result_stop is None:
            result_stop = {'type': 'error', 'message': 'Failed to stop JADE (no result returned)'}
        _log_step("Step 9: Stop JADE", result_stop)
        if result_stop.get('type') == 'error':
            ss.simple_workflow_final_status = {'type': 'error', 'message': f"Workflow completed but failed to stop JADE: {result_stop.get('message', 'Unknown error')}"}
            return

    ss.simple_workflow_final_status = {'type': 'success', 'message': "Workflow completed successfully"}
    print("Simple Workflow: All steps completed successfully.")
