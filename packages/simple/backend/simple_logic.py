import streamlit
import random
import copy
from packages.configuration.backend.state_management import DEFAULT_CONFIG_TEMPLATE, _stash_current_config_as_fallback
from packages.configuration.backend.config_logic import clear_config_from_memory

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
