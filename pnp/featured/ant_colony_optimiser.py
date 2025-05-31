import math
import random
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "num_iterations",
                "label": "Number of Iterations",
                "type": "integer",
                "default": 50,
                "min": 1,
                "max": 500,
                "help": "Number of iterations for the ACO algorithm."
            },
            {
                "name": "num_ants_per_iteration_factor", # Number of ants will be this factor * num_parcels
                "label": "Ants per Iteration (Factor of Parcels)",
                "type": "float",
                "default": 0.5, # e.g. 0.5 * 10 parcels = 5 ants
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "help": "Number of ants is this factor times the number of parcels. At least 1 ant."
            },
            {
                "name": "alpha",
                "label": "Alpha (Pheromone Influence)",
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 5.0,
                "step": 0.1,
                "help": "Influence of pheromone trails."
            },
            {
                "name": "beta",
                "label": "Beta (Heuristic Influence)",
                "type": "float",
                "default": 2.0,
                "min": 0.0,
                "max": 10.0,
                "step": 0.1,
                "help": "Influence of heuristic information (inverse distance)."
            },
            {
                "name": "evaporation_rate",
                "label": "Evaporation Rate (Rho)",
                "type": "float",
                "default": 0.1,
                "min": 0.01,
                "max": 1.0,
                "step": 0.01,
                "help": "Rate at which pheromones evaporate (0.0 to 1.0)."
            },
            {
                "name": "pheromone_deposit_amount",
                "label": "Pheromone Deposit Amount (Q)",
                "type": "float",
                "default": 100.0,
                "min": 1.0,
                "help": "Constant Q used in pheromone update rule."
            },
            {
                "name": "initial_pheromone_value",
                "label": "Initial Pheromone Value",
                "type": "float",
                "default": 0.1,
                "min": 0.001,
                "help": "Small initial value for pheromone trails."
            },
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
                "label": "Generic Vehicle Capacity (for ACO route building)",
                "type": "integer",
                "default": 100,
                "min": 1,
                "help": "Capacity constraint used during ACO route formation phase."
            },
            {
                "name": "generic_max_route_duration",
                "label": "Generic Max Route Duration (for ACO, minutes)",
                "type": "integer",
                "default": 480, # 8 hours
                "min": 30,
                "help": "Maximum duration for a route (warehouse-to-warehouse) during ACO route building, relative to a common start time."
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_schedule_and_feasibility(ordered_parcel_objects, agent_or_generic_constraints, warehouse_coords, params, parcel_map_for_lookup):
    """
    Calculates schedule for a sequence of parcels against specific agent or generic constraints.
    Returns: (is_feasible, schedule_details_dict) where schedule_details_dict contains "reason" key 
             explaining feasibility status
    """
    reason = "Feasible"  # Default success reason
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)

    is_specific_agent = "operating_hours_start" in agent_or_generic_constraints
    if is_specific_agent:
        vehicle_capacity = agent_or_generic_constraints["capacity_weight"]
        # Actual start time of agent for TW checks
        route_start_time = agent_or_generic_constraints["operating_hours_start"]
        # Max end time for agent
        vehicle_op_end_time = agent_or_generic_constraints["operating_hours_end"]
    else: # Generic constraints for ACO route building or C&W merging
        vehicle_capacity = agent_or_generic_constraints["generic_vehicle_capacity"]
        route_start_time = 0 # Relative start for duration check
        # Max duration acts as op_end relative to 0
        vehicle_op_end_time = agent_or_generic_constraints["generic_max_route_duration"]

    route_stop_ids = ["Warehouse"]
    route_stop_coordinates = [list(warehouse_coords)]
    # Arrival at warehouse = route_start_time (either agent's op_start or 0 for generic)
    arrival_times = [round(route_start_time)]
    # Departure from warehouse is also route_start_time
    departure_times = [round(route_start_time)]

    current_time_on_route = route_start_time # This tracks time from start of THIS route.
    current_location = list(warehouse_coords)
    current_load = 0
    total_distance = 0.0

    for p_obj_original in ordered_parcel_objects:
        # Ensure we use full parcel details from the map if only IDs were passed
        p_obj = parcel_map_for_lookup.get(p_obj_original["id"], p_obj_original)

        p_id = p_obj["id"]
        p_coords = p_obj["coordinates_x_y"]
        p_weight = p_obj["weight"]
        p_service_time = p_obj.get("service_time", default_service_time)
        p_tw_open = p_obj.get("time_window_open", 0)
        p_tw_close = p_obj.get("time_window_close", 1439)

        current_load += p_weight
        if current_load > vehicle_capacity:
            reason = f"Capacity exceeded - Current: {current_load}, Max: {vehicle_capacity}"
            print(f"    [DEBUG FEASIBILITY] Capacity check failed: {reason}")
            return False, {"reason": reason} 

        dist_to_parcel = _calculate_distance(current_location, p_coords)
        total_distance += dist_to_parcel
        travel_time = dist_to_parcel * time_per_dist_unit
        
        # Physical arrival time at parcel, accumulates from route_start_time
        physical_arrival_at_parcel = current_time_on_route + travel_time
        
        # Service start time considers waiting for time window open
        actual_service_start_time = max(physical_arrival_at_parcel, p_tw_open)

        if actual_service_start_time > p_tw_close: # Cannot start service if arrival (or TW open) is already past TW close
            reason = f"TW violation - Arrival: {physical_arrival_at_parcel}, TW: {p_tw_open}-{p_tw_close}"
            print(f"    [DEBUG FEASIBILITY] Time Window check failed: {reason}")
            return False, {"reason": reason}

        actual_service_end_time = actual_service_start_time + p_service_time

        if actual_service_end_time > p_tw_close: # Service finishes too late for parcel
            return False, {}
        
        if is_specific_agent and actual_service_end_time > vehicle_op_end_time: # Service finishes too late for agent
            return False, {}

        route_stop_ids.append(p_id)
        route_stop_coordinates.append(list(p_coords))
        arrival_times.append(round(physical_arrival_at_parcel)) # Store physical arrival
        departure_times.append(round(actual_service_end_time)) # Store service end
        
        current_time_on_route = actual_service_end_time # Update time for next leg
        current_location = list(p_coords)

    # Return to Warehouse
    dist_to_warehouse = _calculate_distance(current_location, warehouse_coords)
    total_distance += dist_to_warehouse
    travel_time_to_wh = dist_to_warehouse * time_per_dist_unit
    physical_arrival_at_warehouse_final = current_time_on_route + travel_time_to_wh

    # For specific agent, check final arrival against their op_end
    if is_specific_agent and physical_arrival_at_warehouse_final > vehicle_op_end_time:
        return False, {}
    
    # For generic route, check total duration (final arrival - 0) against max_route_duration
    # Note: vehicle_op_end_time IS generic_max_route_duration when not is_specific_agent
    route_duration_from_wh_to_wh = physical_arrival_at_warehouse_final - route_start_time
    if not is_specific_agent and route_duration_from_wh_to_wh > vehicle_op_end_time:
        return False, {}

    route_stop_ids.append("Warehouse")
    route_stop_coordinates.append(list(warehouse_coords))
    arrival_times.append(round(physical_arrival_at_warehouse_final))
    departure_times.append(round(physical_arrival_at_warehouse_final))

    schedule_details = {
        "route_stop_ids": route_stop_ids,
        "route_stop_coordinates": route_stop_coordinates,
        "arrival_times": arrival_times,
        "departure_times": departure_times,
        "total_distance": round(total_distance, 2),
        "total_load": current_load,
        "route_duration_actual": round(route_duration_from_wh_to_wh)
    }
    return True, schedule_details


def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    all_parcels_list = [copy.deepcopy(p) for p in config_data.get("parcels", [])]
    delivery_agents = config_data.get("delivery_agents", [])

    if not all_parcels_list:
        return {"status": "success", "message": "No parcels to deliver.", "optimised_routes": [], "unassigned_parcels": [], "unassigned_parcels_details": []}
    if not delivery_agents:
        return {"status": "success", "message": "No delivery agents available.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_list], "unassigned_parcels_details": all_parcels_list}

    num_parcels = len(all_parcels_list)
    parcel_map = {p["id"]: p for p in all_parcels_list}
    parcel_id_to_idx = {p["id"]: i + 1 for i, p in enumerate(all_parcels_list)} # 1 to N
    parcel_idx_to_id = {i + 1: p["id"] for i, p in enumerate(all_parcels_list)}
    # Node 0 is Warehouse

    num_nodes = num_parcels + 1 # Warehouse + Parcels

    # ACO Parameters
    num_iterations = params.get("num_iterations", 50)
    # Calculate num_ants based on factor and num_parcels, ensure at least 1
    num_ants = max(1, int(params.get("num_ants_per_iteration_factor", 0.5) * num_parcels))

    alpha = params.get("alpha", 1.0) # Pheromone influence
    beta = params.get("beta", 2.0)   # Heuristic influence
    evaporation_rate = params.get("evaporation_rate", 0.1)
    pheromone_deposit_q = params.get("pheromone_deposit_amount", 100.0)
    initial_pheromone = params.get("initial_pheromone_value", 0.1)
    
    # Determine effective generic capacity for ACO route building phase
    # It's capped by the user-defined parameter and the max capacity of actual agents
    user_set_generic_capacity = params.get("generic_vehicle_capacity", 100) # Default from schema if not set
    
    actual_max_agent_capacity = 0
    if delivery_agents: # Should always be true due to check above, but good for safety
        capacities = [agent.get("capacity_weight", 0) for agent in delivery_agents]
        if capacities:
            actual_max_agent_capacity = max(capacities)
        else: # No agents have capacity defined, fallback (unlikely if config is valid)
            actual_max_agent_capacity = user_set_generic_capacity 
    else: # Should not be reached due to earlier return
        actual_max_agent_capacity = user_set_generic_capacity

    # Ants will build routes using a capacity that is the smaller of user's param and actual max agent capacity
    # Ensure it's at least 1 if actual_max_agent_capacity was 0 for some reason.
    effective_generic_capacity_for_ants = min(user_set_generic_capacity, actual_max_agent_capacity)
    if effective_generic_capacity_for_ants <= 0: # If user set 0 or agents had 0 cap
        effective_generic_capacity_for_ants = 1 # Fallback to a minimal capacity

    print(f"ACO: User generic capacity param: {user_set_generic_capacity}, Actual max agent capacity: {actual_max_agent_capacity}, Effective generic capacity for ants: {effective_generic_capacity_for_ants}")

    generic_constraints = {
        "generic_vehicle_capacity": effective_generic_capacity_for_ants, # Use the calculated effective capacity
        "generic_max_route_duration": params.get("generic_max_route_duration", 480)
    }
    print(f"ACO: Generic constraints for ants: Capacity={generic_constraints['generic_vehicle_capacity']}, "
          f"MaxDuration={generic_constraints['generic_max_route_duration']}")

    # Initialize distance matrix
    dist_matrix = [[0.0] * num_nodes for _ in range(num_nodes)]
    for i in range(num_nodes):
        for j in range(i, num_nodes):
            coord_i = warehouse_coords if i == 0 else parcel_map[parcel_idx_to_id[i]]["coordinates_x_y"]
            coord_j = warehouse_coords if j == 0 else parcel_map[parcel_idx_to_id[j]]["coordinates_x_y"]
            dist = _calculate_distance(coord_i, coord_j)
            dist_matrix[i][j] = dist_matrix[j][i] = dist

    # Initialize pheromone matrix
    pheromone_matrix = [[initial_pheromone] * num_nodes for _ in range(num_nodes)]

    global_best_solution_routes_parcels = [] # List of lists of parcel objects
    global_best_solution_cost = float('inf')
    global_best_unassigned_count = num_parcels + 1


    print(f"ACO: Starting optimization with {num_iterations} iterations and {num_ants} ants")
    for iteration in range(num_iterations):
        iteration_solutions = [] # Store solutions (list of routes, cost) from all ants this iteration

        if iteration == 0 or (iteration+1) % 10 == 0:
            print(f"\nACO: Iteration {iteration+1}/{num_iterations}")

        for ant_idx in range(num_ants):
            ant_parcels_to_visit = set(parcel_idx_to_id.keys()) # Set of parcel indices (1 to N)
            ant_solution_routes_parcels = [] # List of lists of parcel objects for this ant's solution
            ant_solution_total_distance = 0.0

            while ant_parcels_to_visit:
                current_single_route_parcel_objects = []
                current_location_idx = 0 # Start at Warehouse
                
                # Try to build one route
                while True:
                    eligible_next_parcel_indices = []
                    for p_idx in ant_parcels_to_visit:
                        parcel_obj = parcel_map[parcel_idx_to_id[p_idx]]
                        
                        # Tentatively add this parcel to the current_single_route
                        temp_route_parcels = current_single_route_parcel_objects + [parcel_obj]
                        
                        # Check feasibility with generic constraints
                        is_feasible_addition, feasibility_details = _calculate_route_schedule_and_feasibility(
                            temp_route_parcels, generic_constraints, warehouse_coords, params, parcel_map
                        )
                        if iteration == 0 and ant_idx == 0 and not is_feasible_addition:
                            parcel_obj = parcel_map[parcel_idx_to_id[p_idx]]
                            print(f"    [DEBUG] Could not add parcel {p_idx} ({parcel_obj['id']}) to empty route.")
                            print(f"    [DEBUG] Parcel details: weight={parcel_obj['weight']}, coords={parcel_obj['coordinates_x_y']}, TW={parcel_obj.get('time_window_open')}-{parcel_obj.get('time_window_close')}")
                            print(f"    [DEBUG] Fail reason: {feasibility_details.get('reason', 'Unknown')}")
                        if is_feasible_addition:
                            eligible_next_parcel_indices.append(p_idx)
                    
                    if not eligible_next_parcel_indices:
                        if iteration == 0:
                            print(f"  Ant {ant_idx}: No eligible parcels left to add to route. Current route has {len(current_single_route_parcel_objects)} parcels.")
                        print(f"    [DEBUG] No eligible parcels to add. Current route weight: {sum(p['weight'] for p in current_single_route_parcel_objects)}")
                        break # Cannot add more parcels to this route

                    # Calculate probabilities
                    probs = []
                    total_prob_sum = 0.0
                    for next_p_idx in eligible_next_parcel_indices:
                        pheromone = pheromone_matrix[current_location_idx][next_p_idx]
                        distance = dist_matrix[current_location_idx][next_p_idx]
                        heuristic = 1.0 / (distance + 1e-6) # Add epsilon to avoid div by zero
                        
                        prob_val = (pheromone ** alpha) * (heuristic ** beta)
                        probs.append({"idx": next_p_idx, "prob": prob_val})
                        total_prob_sum += prob_val
                    
                    if total_prob_sum == 0: # No way to move, or all probs are zero
                        break 

                    # Normalize probabilities and select next parcel
                    for p_info in probs:
                        p_info["prob"] /= total_prob_sum
                    
                    # Roulette wheel selection
                    r = random.random()
                    cumulative_prob = 0.0
                    selected_parcel_idx = -1
                    for p_info in probs:
                        cumulative_prob += p_info["prob"]
                        if r <= cumulative_prob:
                            selected_parcel_idx = p_info["idx"]
                            break
                    if selected_parcel_idx == -1 and probs: # Should not happen if probs sum to 1
                         selected_parcel_idx = probs[-1]["idx"]


                    if selected_parcel_idx != -1:
                        selected_parcel_obj = parcel_map[parcel_idx_to_id[selected_parcel_idx]]
                        current_single_route_parcel_objects.append(selected_parcel_obj)
                        ant_parcels_to_visit.remove(selected_parcel_idx)
                        current_location_idx = selected_parcel_idx
                    else: # No parcel could be selected
                        break 
                
                if current_single_route_parcel_objects:
                    # Final check and details for this constructed route
                    is_valid_final, route_generic_details = _calculate_route_schedule_and_feasibility(
                        current_single_route_parcel_objects, generic_constraints, warehouse_coords, params, parcel_map
                    )
                    if is_valid_final:
                        ant_solution_routes_parcels.append(current_single_route_parcel_objects)
                        ant_solution_total_distance += route_generic_details["total_distance"]
                    else:
                        # Failed route, put parcels back (simplistic, could be smarter)
                        for p_obj_failed in current_single_route_parcel_objects:
                            ant_parcels_to_visit.add(parcel_id_to_idx[p_obj_failed["id"]])
                else: # No parcels could be added to start a new route
                    if not ant_parcels_to_visit: # All parcels assigned
                        pass
                    else: # Parcels remaining, but cannot form a new route from WH
                        if iteration == 0:
                            print(f"  Ant {ant_idx}: Could not start new route with remaining parcels: {ant_parcels_to_visit}")
                        break # Stop trying to build routes for this ant


            iteration_solutions.append({
                "routes_parcels": ant_solution_routes_parcels, 
                "cost": ant_solution_total_distance,
                "unassigned_count": len(ant_parcels_to_visit)
            })

        # Update pheromones
        # 1. Evaporation
        for r in range(num_nodes):
            for c in range(num_nodes):
                pheromone_matrix[r][c] *= (1.0 - evaporation_rate)
        
        # 2. Deposition (based on all ants' solutions this iteration)
        for sol in iteration_solutions:
            if sol["cost"] == 0: continue # Avoid division by zero for empty solutions
            pheromone_to_add = pheromone_deposit_q / sol["cost"]
            for route_p_list in sol["routes_parcels"]:
                path_indices = [0] # Start at WH
                for p_obj in route_p_list:
                    path_indices.append(parcel_id_to_idx[p_obj["id"]])
                path_indices.append(0) # End at WH
                
                for i in range(len(path_indices) - 1):
                    u, v = path_indices[i], path_indices[i+1]
                    pheromone_matrix[u][v] += pheromone_to_add
                    pheromone_matrix[v][u] += pheromone_to_add # Symmetric

        # Log iteration results
        if iteration == 0 or (iteration+1) % 10 == 0:
            best_iter_unassigned = min(sol["unassigned_count"] for sol in iteration_solutions) if iteration_solutions else num_parcels
            print(f"ACO: Iter {iteration+1}: Best unassigned={best_iter_unassigned}/{num_parcels}")

        # Update global best solution
        # Prioritize fewer unassigned parcels, then lower cost
        for sol in iteration_solutions:
            if sol["unassigned_count"] < global_best_unassigned_count:
                global_best_unassigned_count = sol["unassigned_count"]
                global_best_solution_cost = sol["cost"]
                global_best_solution_routes_parcels = sol["routes_parcels"]
            elif sol["unassigned_count"] == global_best_unassigned_count:
                if sol["cost"] < global_best_solution_cost:
                    global_best_solution_cost = sol["cost"]
                    global_best_solution_routes_parcels = sol["routes_parcels"]
    
    # --- Assignment of globally best routes to specific delivery agents ---
    print(f"\nACO: Starting agent assignment with {len(global_best_solution_routes_parcels)} best routes")
    optimised_routes_output = []
    assigned_parcels_globally_ids = set()
    
    # Sort agents (e.g., by capacity, or just iterate) - not strictly necessary for this greedy assignment
    # Sort routes (e.g., by number of parcels descending, or load)
    # Make copies of parcel lists for sorting
    sorted_global_best_routes = [list(r) for r in global_best_solution_routes_parcels]
    sorted_global_best_routes.sort(key=lambda r_list: len(r_list), reverse=True)
    
    used_agent_ids = set()

    for route_parcel_obj_list in sorted_global_best_routes:
        if not route_parcel_obj_list: continue

        best_agent_for_route = None
        best_schedule_details_for_agent = None

        print(f"\nACO: Trying to assign route with parcels: {[p['id'] for p in route_parcel_obj_list]}")
        for agent_config in delivery_agents:
            if agent_config["id"] in used_agent_ids:
                print(f"  - Skipping agent {agent_config['id']} (already assigned)")
                continue
            print(f"  - Checking agent {agent_config['id']} "
                  f"(Capacity: {agent_config['capacity_weight']}, "
                  f"Hours: {agent_config.get('operating_hours_start', 0)}-{agent_config.get('operating_hours_end', 1440)})")

            is_feasible_for_agent, schedule_details = _calculate_route_schedule_and_feasibility(
                route_parcel_obj_list,
                agent_config, # Specific agent constraints
                warehouse_coords,
                params,
                parcel_map 
            )
            if is_feasible_for_agent:
                print(f"    -> FEASIBLE - Assigned to agent {agent_config['id']}")
                # Simple greedy: assign to first feasible agent
                best_agent_for_route = agent_config
                best_schedule_details_for_agent = schedule_details
                break 
            else:
                print(f"    -> INFEASIBLE - Reason: {schedule_details.get('reason', 'Unknown')}")

        if best_agent_for_route and best_schedule_details_for_agent:
            assigned_agent_id = best_agent_for_route["id"]
            used_agent_ids.add(assigned_agent_id)
            
            # Parcels in this route (IDs and full details)
            current_route_parcel_ids = [p["id"] for p in route_parcel_obj_list]
            current_route_parcels_details = [copy.deepcopy(p) for p in route_parcel_obj_list] # Get full details
            for p_id in current_route_parcel_ids:
                assigned_parcels_globally_ids.add(p_id)

            optimised_routes_output.append({
                "agent_id": assigned_agent_id,
                "parcels_assigned_ids": current_route_parcel_ids,
                "parcels_assigned_details": current_route_parcels_details, # Use the full details
                "route_stop_ids": best_schedule_details_for_agent["route_stop_ids"],
                "route_stop_coordinates": best_schedule_details_for_agent["route_stop_coordinates"],
                "total_weight": best_schedule_details_for_agent["total_load"],
                "capacity_weight": best_agent_for_route["capacity_weight"],
                "total_distance": best_schedule_details_for_agent["total_distance"],
                "arrival_times": best_schedule_details_for_agent["arrival_times"],
                "departure_times": best_schedule_details_for_agent["departure_times"]
            })

    final_unassigned_parcel_ids = [p["id"] for p in all_parcels_list if p["id"] not in assigned_parcels_globally_ids]
    final_unassigned_parcels_details = [copy.deepcopy(parcel_map[p_id]) for p_id in final_unassigned_parcel_ids]
    
    message = f"ACO completed. Iterations: {iteration+1}/{num_iterations}. Best cost: {global_best_solution_cost:.2f}. Unassigned: {len(final_unassigned_parcel_ids)}"
    if not global_best_solution_routes_parcels and all_parcels_list : # No routes formed at all
        message = "ACO completed, but no feasible routes could be formed for any agent."


    return {
        "status": "success",
        "message": message,
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": final_unassigned_parcel_ids,
        "unassigned_parcels_details": final_unassigned_parcels_details
    }
