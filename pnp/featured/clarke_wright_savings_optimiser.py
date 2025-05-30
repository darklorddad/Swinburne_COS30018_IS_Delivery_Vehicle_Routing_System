import math
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "time_per_distance_unit",
                "label": "Time per distance unit (minutes)",
                "type": "float",
                "default": 2.0,
                "min": 0.1,
                "step": 0.1,
                "help": "Minutes taken to travel one unit of distance."
            },
            {
                "name": "default_service_time",
                "label": "Default service time at stop (minutes)",
                "type": "integer",
                "default": 10,
                "min": 0,
                "help": "Default time spent at each parcel stop if not specified by the parcel."
            },
            {
                "name": "generic_vehicle_capacity",
                "label": "Generic Vehicle Capacity (for merging)",
                "type": "integer",
                "default": 100,
                "min": 1,
                "help": "Capacity constraint used during C&W route formation phase."
            },
            {
                "name": "generic_max_route_duration",
                "label": "Generic Max Route Duration (for merging, minutes)",
                "type": "integer",
                "default": 480, # 8 hours
                "min": 30,
                "help": "Maximum duration for a route (warehouse-to-warehouse) during C&W merging phase, relative to a common start time."
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _get_parcel_details(parcel_id, parcel_map):
    return parcel_map.get(parcel_id)

def _calculate_route_schedule_and_feasibility(ordered_parcel_objects, agent_constraints, warehouse_coords, params, parcel_map):
    """
    Calculates the schedule for a given sequence of parcels for a specific agent or generic constraints.
    
    Args:
        ordered_parcel_objects: List of parcel objects in delivery order.
        agent_constraints: Dict with "capacity_weight", "operating_hours_start", "operating_hours_end".
                           Or generic constraints: "generic_vehicle_capacity", "generic_max_route_duration".
        warehouse_coords: Coordinates of the warehouse.
        params: Optimisation parameters (time_per_distance_unit, default_service_time).
        parcel_map: Map of parcel_id to parcel object for easy lookup.

    Returns:
        A tuple: (is_feasible, schedule_details_dict)
        schedule_details_dict contains:
            route_stop_ids, route_stop_coordinates, arrival_times, departure_times,
            total_distance, total_load, route_duration (from WH departure to WH arrival)
    """
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)

    # Determine constraints
    is_specific_agent = "operating_hours_start" in agent_constraints
    if is_specific_agent:
        agent_capacity = agent_constraints["capacity_weight"]
        agent_op_start = agent_constraints["operating_hours_start"]
        agent_op_end = agent_constraints["operating_hours_end"]
    else: # Generic constraints for merging phase
        agent_capacity = agent_constraints["generic_vehicle_capacity"]
        agent_op_start = 0 # Relative start for generic duration check
        agent_op_end = agent_constraints["generic_max_route_duration"] # Max duration acts as op_end relative to 0

    route_stop_ids = ["Warehouse"]
    route_stop_coordinates = [list(warehouse_coords)]
    arrival_times = [agent_op_start]
    departure_times = [agent_op_start] # Depart warehouse at agent_op_start

    current_time = agent_op_start
    current_location = list(warehouse_coords)
    current_load = 0
    total_distance = 0.0

    for p_obj in ordered_parcel_objects:
        p_id = p_obj["id"]
        p_coords = p_obj["coordinates_x_y"]
        p_weight = p_obj["weight"]
        p_service_time = p_obj.get("service_time", default_service_time)
        p_tw_open = p_obj.get("time_window_open", 0)
        p_tw_close = p_obj.get("time_window_close", 1439)

        current_load += p_weight
        if current_load > agent_capacity:
            return False, {} # Exceeds capacity

        dist_to_parcel = _calculate_distance(current_location, p_coords)
        total_distance += dist_to_parcel
        travel_time = dist_to_parcel * time_per_dist_unit
        
        arrival_at_parcel = current_time + travel_time
        
        # Actual service can only start after arrival and within parcel's time window open
        service_start_time = max(arrival_at_parcel, p_tw_open)

        # If service must start after parcel's TW close, it's infeasible
        if service_start_time > p_tw_close:
            return False, {} 

        service_end_time = service_start_time + p_service_time

        # If service ends after parcel's TW close, it's infeasible
        if service_end_time > p_tw_close:
            return False, {}
        
        # If service ends after agent's operating hours (for specific agent)
        if is_specific_agent and service_end_time > agent_op_end:
            return False, {}

        route_stop_ids.append(p_id)
        route_stop_coordinates.append(list(p_coords))
        arrival_times.append(round(arrival_at_parcel))
        departure_times.append(round(service_end_time))
        
        current_time = service_end_time
        current_location = list(p_coords)

    # Return to Warehouse
    dist_to_warehouse = _calculate_distance(current_location, warehouse_coords)
    total_distance += dist_to_warehouse
    travel_time_to_wh = dist_to_warehouse * time_per_dist_unit
    arrival_at_warehouse_final = current_time + travel_time_to_wh

    if is_specific_agent and arrival_at_warehouse_final > agent_op_end:
        return False, {}
    
    route_duration = arrival_at_warehouse_final - agent_op_start # Duration from WH departure to WH arrival
    if not is_specific_agent and route_duration > agent_op_end: # agent_op_end is generic_max_route_duration here
        return False, {}


    route_stop_ids.append("Warehouse")
    route_stop_coordinates.append(list(warehouse_coords))
    arrival_times.append(round(arrival_at_warehouse_final))
    departure_times.append(round(arrival_at_warehouse_final)) # Arrive and "depart" (finish) at same time

    schedule_details = {
        "route_stop_ids": route_stop_ids,
        "route_stop_coordinates": route_stop_coordinates,
        "arrival_times": arrival_times,
        "departure_times": departure_times,
        "total_distance": round(total_distance, 2),
        "total_load": current_load,
        "route_duration": round(route_duration) # Duration of service and travel, warehouse to warehouse
    }
    return True, schedule_details

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])

    if not parcels:
        return {"status": "success", "message": "No parcels to deliver.", "optimised_routes": [], "unassigned_parcels": []}
    if not delivery_agents:
        return {"status": "success", "message": "No delivery agents available.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in parcels], "unassigned_parcels_details": parcels}

    parcel_map = {p["id"]: p for p in parcels}

    # 1. Calculate Savings
    savings_list = []
    parcel_ids = list(parcel_map.keys())
    for i in range(len(parcel_ids)):
        for j in range(i + 1, len(parcel_ids)):
            p_i_id = parcel_ids[i]
            p_j_id = parcel_ids[j]
            
            parcel_i = parcel_map[p_i_id]
            parcel_j = parcel_map[p_j_id]

            dist_wh_i = _calculate_distance(warehouse_coords, parcel_i["coordinates_x_y"])
            dist_wh_j = _calculate_distance(warehouse_coords, parcel_j["coordinates_x_y"])
            dist_i_j = _calculate_distance(parcel_i["coordinates_x_y"], parcel_j["coordinates_x_y"])
            
            saving = dist_wh_i + dist_wh_j - dist_i_j
            if saving > 0: # Only consider positive savings
                savings_list.append({"saving": saving, "i": p_i_id, "j": p_j_id})

    savings_list.sort(key=lambda x: x["saving"], reverse=True)

    # 2. Initialize Routes: Each parcel is its own route (D -> P -> D)
    # Routes are represented as a list of parcel objects in order.
    current_cw_routes = []
    for p_id in parcel_ids:
        current_cw_routes.append(
            {"id": p_id,  # Route initially identified by its single parcel
             "parcels": [copy.deepcopy(parcel_map[p_id])],
             "active": True} 
        )
    
    # Map parcel_id to the index of its route in current_cw_routes
    # This map needs to be updated carefully upon merges.
    # A simpler way: map parcel_id to the route object itself.
    # And route objects need to be mutable or replaced.
    # Let's make current_cw_routes a list of dicts that are modified.

    # Store route_id for each parcel
    parcel_to_route_id_map = {p_id: p_id for p_id in parcel_ids}


    # 3. Merge Routes
    generic_constraints_for_merging = {
        "generic_vehicle_capacity": params["generic_vehicle_capacity"],
        "generic_max_route_duration": params["generic_max_route_duration"]
    }

    for saving_entry in savings_list:
        p_i_id = saving_entry["i"]
        p_j_id = saving_entry["j"]

        route_i_id = parcel_to_route_id_map[p_i_id]
        route_j_id = parcel_to_route_id_map[p_j_id]

        # Find the actual route objects from current_cw_routes using their IDs
        route_i_obj = next((r for r in current_cw_routes if r["id"] == route_i_id and r["active"]), None)
        route_j_obj = next((r for r in current_cw_routes if r["id"] == route_j_id and r["active"]), None)

        if not route_i_obj or not route_j_obj or route_i_id == route_j_id:
            continue # Parcels already in same route or one route was deactivated

        # Check if p_i is end of route_i and p_j is start of route_j
        # (Our route["parcels"] is just the sequence of parcels, WH is implicit at ends)
        if route_i_obj["parcels"][-1]["id"] == p_i_id and \
           route_j_obj["parcels"][0]["id"] == p_j_id:
            
            # Try to merge route_i with route_j
            candidate_merged_parcels = route_i_obj["parcels"] + route_j_obj["parcels"]
            
            is_feasible_merge, _ = _calculate_route_schedule_and_feasibility(
                candidate_merged_parcels,
                generic_constraints_for_merging, # Use generic constraints for C&W merging phase
                warehouse_coords,
                params,
                parcel_map
            )

            if is_feasible_merge:
                # Perform the merge: route_i absorbs route_j
                route_i_obj["parcels"].extend(route_j_obj["parcels"])
                route_j_obj["active"] = False # Mark route_j as merged/inactive
                
                # Update parcel_to_route_id_map for all parcels from the absorbed route_j
                for p_in_j in route_j_obj["parcels"]:
                    parcel_to_route_id_map[p_in_j["id"]] = route_i_id
    
    # Collect final C&W routes (active ones)
    final_cw_formed_routes = [r for r in current_cw_routes if r["active"]]

    # 4. Assign C&W routes to specific delivery agents
    optimised_routes_output = []
    assigned_parcels_globally = set()
    
    # Sort agents (e.g., by capacity, or just iterate) - not strictly necessary for this greedy assignment
    # Sort routes (e.g., by number of parcels descending, or load)
    final_cw_formed_routes.sort(key=lambda r: len(r["parcels"]), reverse=True)
    
    # Keep track of used agents to ensure one route per agent for this simple assignment
    used_agent_ids = set()

    for cw_route in final_cw_formed_routes:
        if not cw_route["parcels"]: continue # Should not happen if active

        best_agent_for_route = None
        best_schedule_details = None

        for agent in delivery_agents:
            if agent["id"] in used_agent_ids:
                continue

            is_feasible_for_agent, schedule_details = _calculate_route_schedule_and_feasibility(
                cw_route["parcels"],
                agent, # Specific agent constraints
                warehouse_coords,
                params,
                parcel_map
            )
            if is_feasible_for_agent:
                # Found a suitable agent for this route
                # (Could add logic here to find the *best* fit if multiple agents can take it)
                best_agent_for_route = agent
                best_schedule_details = schedule_details
                break # Assign to first suitable agent

        if best_agent_for_route and best_schedule_details:
            assigned_agent_id = best_agent_for_route["id"]
            used_agent_ids.add(assigned_agent_id)
            
            parcels_in_this_route_details = [copy.deepcopy(p) for p in cw_route["parcels"]]
            parcels_in_this_route_ids = [p["id"] for p in parcels_in_this_route_details]
            for p_id in parcels_in_this_route_ids:
                assigned_parcels_globally.add(p_id)

            optimised_routes_output.append({
                "agent_id": assigned_agent_id,
                "parcels_assigned_ids": parcels_in_this_route_ids,
                "parcels_assigned_details": parcels_in_this_route_details,
                "route_stop_ids": best_schedule_details["route_stop_ids"],
                "route_stop_coordinates": best_schedule_details["route_stop_coordinates"],
                "total_weight": best_schedule_details["total_load"],
                "capacity_weight": best_agent_for_route["capacity_weight"],
                "total_distance": best_schedule_details["total_distance"],
                "arrival_times": best_schedule_details["arrival_times"],
                "departure_times": best_schedule_details["departure_times"]
            })

    unassigned_parcel_ids = [p_id for p_id in parcel_map if p_id not in assigned_parcels_globally]
    unassigned_parcels_details_list = [copy.deepcopy(parcel_map[p_id]) for p_id in unassigned_parcel_ids]

    return {
        "status": "success",
        "message": "Clarke-Wright Savings optimisation completed.",
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": unassigned_parcel_ids,
        "unassigned_parcels_details": unassigned_parcels_details_list
    }