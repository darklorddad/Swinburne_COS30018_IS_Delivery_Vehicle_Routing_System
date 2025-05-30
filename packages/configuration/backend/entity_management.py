# --- Entity Management Helpers ---
# Helper to add an entity to a list in config_data if the ID is unique.
def _add_entity(ss, entities_key, entity_id, entity_data, entity_name_singular):
    if not entity_id:
        return {'type': 'warning', 'message': f"{entity_name_singular} ID cannot be empty"}
    
    if entities_key not in ss.config_data:
        ss.config_data[entities_key] = []
        
    if any(e['id'] == entity_id for e in ss.config_data[entities_key]):
        return {'type': 'warning', 'message': f"{entity_name_singular} ID '{entity_id}' already exists"}
    
    ss.config_data[entities_key].append(entity_data)
    return {'type': 'success', 'message': f"{entity_name_singular} '{entity_id}' added"}

# Helper to remove an entity from a list in config_data by its ID.
def _remove_entity(ss, entities_key, entity_id_to_remove, entity_name_singular):
    if not entity_id_to_remove:
        return {'type': 'warning', 'message': f"No {entity_name_singular.lower()} selected to remove"}
        
    if entities_key in ss.config_data and ss.config_data[entities_key]:
        initial_len = len(ss.config_data[entities_key])
        ss.config_data[entities_key] = [e for e in ss.config_data[entities_key] if e['id'] != entity_id_to_remove]
        if len(ss.config_data[entities_key]) < initial_len:
            return {'type': 'success', 'message': f"{entity_name_singular} '{entity_id_to_remove}' removed"}
        else:
            return {'type': 'warning', 'message': f"{entity_name_singular} ID '{entity_id_to_remove}' not found"}
            
    return {'type': 'info', 'message': f"No {entity_name_singular.lower()}s to remove from"}

# --- Parcel Management ---
# Adds a new parcel to the configuration if the ID is unique.
def add_parcel(ss, parcel_id, parcel_x, parcel_y, parcel_weight, earliest_delivery=None, latest_delivery=None):
    parcel_data = {
        "id": parcel_id,
        "coordinates_x_y": [parcel_x, parcel_y],
        "weight": parcel_weight
    }
    
    if earliest_delivery:
        parcel_data["earliest_delivery"] = earliest_delivery
    if latest_delivery:
        parcel_data["latest_delivery"] = latest_delivery

    return _add_entity(ss, "parcels", parcel_id, parcel_data, "Parcel")

# Removes a parcel from the configuration by its ID.
def remove_parcel(ss, parcel_id_to_remove):
    return _remove_entity(ss, "parcels", parcel_id_to_remove, "Parcel")


# --- Delivery Agent Management ---
# Adds a new delivery agent to the configuration if the ID is unique.
def add_delivery_agent(ss, agent_id, capacity_weight, shift_start=None, shift_end=None):
    agent_data = {
        "id": agent_id,
        "capacity_weight": capacity_weight
    }

    # Add optional shift timing fields if provided
    if shift_start:
        agent_data["shift_start"] = shift_start
    if shift_end:
        agent_data["shift_end"] = shift_end

    return _add_entity(ss, "delivery_agents", agent_id, agent_data, "Agent")

# Removes a delivery agent from the configuration by its ID.
def remove_delivery_agent(ss, agent_id_to_remove):
    return _remove_entity(ss, "delivery_agents", agent_id_to_remove, "Agent")


# --- General Settings in Edit Mode ---
# Triggered by changes in the filename input widget.
def handle_filename_update(ss):
    new_filename_base = ss.get("filename_input_widget")
    if new_filename_base:
        new_full_filename = f"{new_filename_base}.json" if not new_filename_base.endswith(".json") else new_filename_base
        ss.config_filename = new_full_filename
    # If new_filename_base is empty, config_filename remains unchanged.
    # This prevents the filename from becoming just ".json".

# Triggered by changes in warehouse coordinate input widgets.
def handle_warehouse_coordinates_update(ss):
    wh_x_val = ss.get("wh_x_input_widget")
    wh_y_val = ss.get("wh_y_input_widget")

    if not isinstance(ss.get("config_data"), dict):
        # Ensures config_data is a dictionary; initialises if necessary.
        # This case should ideally not occur if application flow is correct.
        ss.config_data = {"warehouse_coordinates_x_y": [0, 0]}

    # Uses current coordinates as fallback if widget values are None.
    current_coords = ss.config_data.get("warehouse_coordinates_x_y", [0, 0])
    
    final_wh_x = wh_x_val if wh_x_val is not None else current_coords[0]
    final_wh_y = wh_y_val if wh_y_val is not None else current_coords[1]
    
    ss.config_data["warehouse_coordinates_x_y"] = [int(final_wh_x), int(final_wh_y)]
