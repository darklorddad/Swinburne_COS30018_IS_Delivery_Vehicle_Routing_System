# --- Parcel Management Logic ---
def add_parcel(ss, parcel_id, parcel_x, parcel_y, parcel_weight):
    """Adds a new parcel to the configuration if the ID is unique"""
    if not parcel_id:
        return {'type': 'warning', 'message': "Parcel ID cannot be empty"}
    if "parcels" not in ss.config_data:
        ss.config_data["parcels"] = []
    if any(p['id'] == parcel_id for p in ss.config_data["parcels"]):
        return {'type': 'warning', 'message': f"Parcel ID '{parcel_id}' already exists"}
    
    ss.config_data["parcels"].append({
        "id": parcel_id,
        "coordinates_x_y": [parcel_x, parcel_y],
        "weight": parcel_weight
    })
    return {'type': 'success', 'message': f"Parcel '{parcel_id}' added"} # Message for potential future use

def remove_parcel(ss, parcel_id_to_remove):
    """Removes a parcel from the configuration by its ID"""
    if not parcel_id_to_remove:
        return {'type': 'warning', 'message': "No parcel selected to remove"}
    if "parcels" in ss.config_data:
        initial_len = len(ss.config_data["parcels"])
        ss.config_data["parcels"] = [p for p in ss.config_data["parcels"] if p['id'] != parcel_id_to_remove]
        if len(ss.config_data["parcels"]) < initial_len:
            return {'type': 'success', 'message': f"Parcel '{parcel_id_to_remove}' removed"} # For potential future use
        else:
            return {'type': 'warning', 'message': f"Parcel ID '{parcel_id_to_remove}' not found"}
    return {'type': 'info', 'message': "No parcels to remove from"}


# --- Delivery Agent Management Logic ---
def add_delivery_agent(ss, agent_id, capacity_weight):
    """Adds a new delivery agent to the configuration if the ID is unique"""
    if not agent_id:
        return {'type': 'warning', 'message': "Agent ID cannot be empty"}
    if "delivery_agents" not in ss.config_data:
        ss.config_data["delivery_agents"] = []
    if any(a['id'] == agent_id for a in ss.config_data["delivery_agents"]):
        return {'type': 'warning', 'message': f"Agent ID '{agent_id}' already exists"}

    ss.config_data["delivery_agents"].append({
        "id": agent_id,
        "capacity_weight": capacity_weight
    })
    return {'type': 'success', 'message': f"Agent '{agent_id}' added"} # Message for potential future use

def remove_delivery_agent(ss, agent_id_to_remove):
    """Removes a delivery agent from the configuration by its ID"""
    if not agent_id_to_remove:
        return {'type': 'warning', 'message': "No agent selected to remove"}
    if "delivery_agents" in ss.config_data:
        initial_len = len(ss.config_data["delivery_agents"])
        ss.config_data["delivery_agents"] = [a for a in ss.config_data["delivery_agents"] if a['id'] != agent_id_to_remove]
        if len(ss.config_data["delivery_agents"]) < initial_len:
            return {'type': 'success', 'message': f"Agent '{agent_id_to_remove}' removed"} # For potential future use
        else:
            return {'type': 'warning', 'message': f"Agent ID '{agent_id_to_remove}' not found"}
    return {'type': 'info', 'message': "No agents to remove from"}

# --- Edit Mode General Settings Logic ---
def handle_filename_update(ss):
    """
    Updates the config_filename in session_state based on the
    filename_input_widget's current value.
    Called on_change of the filename text input.
    """
    # ss = streamlit.session_state # Now passed as parameter
    new_filename_base = ss.get("filename_input_widget") # Key of the text_input widget
    if new_filename_base: # Ensure not empty
        new_full_filename = f"{new_filename_base}.json" if not new_filename_base.endswith(".json") else new_filename_base
        ss.config_filename = new_full_filename
    # If new_filename_base is empty, ss.config_filename remains unchanged,
    # preventing it from becoming just ".json". The input field will show the empty string,
    # but the underlying config_filename won't be corrupted until valid text is entered.

def handle_warehouse_coordinates_update(ss):
    """
    Updates the warehouse_coordinates_x_y in config_data based on
    the number input widgets' current values.
    Called on_change of either warehouse coordinate number input.
    """
    # ss = streamlit.session_state # Now passed as parameter
    wh_x_val = ss.get("wh_x_input_widget") # Key of the X number_input
    wh_y_val = ss.get("wh_y_input_widget") # Key of the Y number_input

    if not isinstance(ss.get("config_data"), dict):
        # This should ideally not happen if the app flow is correct and config_data is initialized.
        # Initialise with default structure if necessary for robustness.
        ss.config_data = {"warehouse_coordinates_x_y": [0, 0]}

    # Fallback to current values in config_data if widget values are somehow None
    # (though number_input usually prevents this with default values).
    current_coords = ss.config_data.get("warehouse_coordinates_x_y", [0, 0])
    
    final_wh_x = wh_x_val if wh_x_val is not None else current_coords[0]
    final_wh_y = wh_y_val if wh_y_val is not None else current_coords[1]
    
    ss.config_data["warehouse_coordinates_x_y"] = [int(final_wh_x), int(final_wh_y)]
