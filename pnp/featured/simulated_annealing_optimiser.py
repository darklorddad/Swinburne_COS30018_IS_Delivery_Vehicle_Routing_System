# DVRS Optimisation Script: Simulated Annealing
import math
import random
import copy # For deepcopying solutions

# --- Helper Functions ---
def _calculate_distance(coord1, coord2):
    """Calculates Euclidean distance."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _get_coords(stop_id, warehouse_coords, parcels_map):
    """Gets coordinates for a stop ID (parcel or warehouse)."""
    if stop_id == "Warehouse":
        return warehouse_coords
    parcel = parcels_map.get(stop_id)
    return parcel["coordinates_x_y"] if parcel else None

# --- Core SA Logic ---

def _generate_initial_solution(parcels_list, agents_list, parcels_map):
    """
    Generates a simple initial solution.
    Assigns each parcel to a random agent, or leaves it unassigned if no agents.
    Initial routes are just lists of parcel IDs for each agent.
    """
    solution_routes = {agent["id"]: [] for agent in agents_list}
    unassigned_parcels = []

    if not agents_list: # No agents, all parcels unassigned
        unassigned_parcels = [p["id"] for p in parcels_list]
        return solution_routes, unassigned_parcels

    for parcel in parcels_list:
        # Simple random assignment for initial solution
        # More sophisticated: try to fit greedily, or assign to least loaded agent
        chosen_agent = random.choice(agents_list)
        solution_routes[chosen_agent["id"]].append(parcel["id"])
    
    # For a truly naive start, can put all parcels in unassigned:
    # unassigned_parcels = [p["id"] for p in parcels_list]
    # for agent in agents_list:
    #    solution_routes[agent["id"]] = []

    return solution_routes, unassigned_parcels


def _evaluate_solution(current_routes_struct, unassigned_parcel_ids,
                       agents_map, parcels_map, warehouse_coords, params):
    """
    Evaluates the cost of a given solution.
    Cost = total_distance + penalty_over_capacity + penalty_time_window +
           penalty_op_hour_violation + penalty_unassigned_parcel.
    """
    total_cost = 0
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)
    return_to_warehouse = params.get("return_to_warehouse", True)

    # Penalty factors from params
    penalty_factor_unassigned = params.get("penalty_unassigned_parcel", 1000)
    penalty_factor_capacity = params.get("penalty_over_capacity", 100)
    penalty_factor_tw = params.get("penalty_time_window_violation", 50)
    penalty_factor_ophours = params.get("penalty_op_hour_violation", 200)

    # Cost from unassigned parcels
    total_cost += len(unassigned_parcel_ids) * penalty_factor_unassigned

    for agent_id, parcel_ids_for_agent in current_routes_struct.items():
        agent_config = agents_map[agent_id]
        agent_op_start = agent_config.get("operating_hours_start", 0)
        agent_op_end = agent_config.get("operating_hours_end", 1439) # 23:59
        agent_capacity = agent_config["capacity_weight"]

        current_route_stops = ["Warehouse"] + parcel_ids_for_agent
        if return_to_warehouse or not parcel_ids_for_agent: # Always return if empty, or if flag is true
             current_route_stops.append("Warehouse")
        
        if len(current_route_stops) <= 1 and parcel_ids_for_agent : # e.g. ["P001"] -> needs WH
            # This case should be handled by ensuring routes always start/end with WH if they have parcels
             current_route_stops = ["Warehouse"] + parcel_ids_for_agent + ["Warehouse"]
        elif not parcel_ids_for_agent : # Agent has no parcels
            continue # No distance or penalties for this agent


        current_time = float(agent_op_start)
        current_loc_coords = list(warehouse_coords) # Start at warehouse
        current_weight = 0
        route_dist = 0

        for i in range(len(current_route_stops) - 1):
            from_stop_id = current_route_stops[i]
            to_stop_id = current_route_stops[i+1]

            from_coords = _get_coords(from_stop_id, warehouse_coords, parcels_map)
            to_coords = _get_coords(to_stop_id, warehouse_coords, parcels_map)

            dist = _calculate_distance(from_coords, to_coords)
            route_dist += dist
            travel_time = dist * time_per_dist_unit
            
            arrival_at_to_stop = current_time + travel_time

            if to_stop_id == "Warehouse": # Moving to (or arriving at final) Warehouse
                current_time = arrival_at_to_stop
                if i == len(current_route_stops) - 2: # This is the final arrival at warehouse
                    if current_time > agent_op_end:
                        total_cost += (current_time - agent_op_end) * penalty_factor_ophours
            else: # Moving to a parcel
                parcel_obj = parcels_map[to_stop_id]
                parcel_tw_open = parcel_obj.get("time_window_open", 0)
                parcel_tw_close = parcel_obj.get("time_window_close", 1439)
                parcel_service_time = parcel_obj.get("service_time", default_service_time)

                service_start_time = max(arrival_at_to_stop, parcel_tw_open)
                
                if service_start_time > parcel_tw_close : # Arrived too late even before service
                     total_cost += (service_start_time - parcel_tw_close) * penalty_factor_tw * 2 # Heavier penalty

                service_end_time = service_start_time + parcel_service_time

                if service_end_time > parcel_tw_close:
                    total_cost += (service_end_time - parcel_tw_close) * penalty_factor_tw
                
                if service_end_time > agent_op_end:
                    total_cost += (service_end_time - agent_op_end) * penalty_factor_ophours

                current_weight += parcel_obj["weight"]
                if current_weight > agent_capacity:
                    total_cost += (current_weight - agent_capacity) * penalty_factor_capacity
                
                current_time = service_end_time
                current_loc_coords = list(to_coords)
        
        total_cost += route_dist # Add actual distance as part of the cost

    return total_cost


def _get_neighbor_solution(current_routes_struct, unassigned_parcel_ids,
                           parcels_list, agents_list, parcels_map, params):
    """Generates a neighbor solution by applying a random move."""
    new_routes = copy.deepcopy(current_routes_struct)
    new_unassigned = list(unassigned_parcel_ids) # Ensure it's a copy

    # All parcel IDs that could be in routes or unassigned
    all_parcel_ids_master = [p["id"] for p in parcels_list]
    
    # Move type probabilities (can be params later)
    prob_move_assigned_to_unassigned = params.get("prob_move_assigned_to_unassigned", 0.1)
    prob_move_unassigned_to_assigned = params.get("prob_move_unassigned_to_assigned", 0.3)
    prob_intra_route_swap = params.get("prob_intra_route_swap", 0.3)
    # prob_inter_route_move = 1.0 - (sum of above)
    
    rnd_val = random.random()

    if not agents_list: # No agents, no moves possible involving agents
        return new_routes, new_unassigned


    if rnd_val < prob_move_assigned_to_unassigned: # Move a parcel from a route to unassigned
        routable_agents = [aid for aid, p_ids in new_routes.items() if p_ids]
        if routable_agents:
            agent_id = random.choice(routable_agents)
            parcel_idx = random.randrange(len(new_routes[agent_id]))
            parcel_to_move = new_routes[agent_id].pop(parcel_idx)
            new_unassigned.append(parcel_to_move)

    elif rnd_val < prob_move_assigned_to_unassigned + prob_move_unassigned_to_assigned: # Move parcel from unassigned to a route
        if new_unassigned:
            parcel_to_move = random.choice(new_unassigned)
            agent_id = random.choice(agents_list)["id"]
            
            insert_idx = 0
            if new_routes[agent_id]: # If route is not empty
                insert_idx = random.randrange(len(new_routes[agent_id]) + 1)
            new_routes[agent_id].insert(insert_idx, parcel_to_move)
            new_unassigned.remove(parcel_to_move)

    elif rnd_val < prob_move_assigned_to_unassigned + prob_move_unassigned_to_assigned + prob_intra_route_swap: # Intra-route swap
        agents_with_multiple_parcels = [aid for aid, p_ids in new_routes.items() if len(p_ids) >= 2]
        if agents_with_multiple_parcels:
            agent_id = random.choice(agents_with_multiple_parcels)
            idx1, idx2 = random.sample(range(len(new_routes[agent_id])), 2)
            new_routes[agent_id][idx1], new_routes[agent_id][idx2] = \
                new_routes[agent_id][idx2], new_routes[agent_id][idx1]
    
    else: # Inter-route move (move parcel from one agent to another)
        source_agents_with_parcels = [aid for aid, p_ids in new_routes.items() if p_ids]
        if source_agents_with_parcels:
            source_agent_id = random.choice(source_agents_with_parcels)
            
            # Ensure target agent is different if possible, or handle if only one agent
            target_agent_list = [ag for ag in agents_list if ag["id"] != source_agent_id]
            if not target_agent_list: # Only one agent, or source was the only one with parcels.
                                      # This move becomes an intra-route re-insertion essentially.
                target_agent_id = source_agent_id
            else:
                target_agent_id = random.choice(target_agent_list)["id"]

            parcel_idx_to_move = random.randrange(len(new_routes[source_agent_id]))
            parcel_to_move = new_routes[source_agent_id].pop(parcel_idx_to_move)
            
            insert_idx = 0
            if new_routes[target_agent_id]: # If target route is not empty
                insert_idx = random.randrange(len(new_routes[target_agent_id]) + 1)
            new_routes[target_agent_id].insert(insert_idx, parcel_to_move)
            
    return new_routes, new_unassigned


def _format_solution_for_output(best_routes_struct, final_unassigned_ids,
                                agents_map, parcels_map, warehouse_coords, params):
    """
    Formats the best found solution into the required DVRS output structure.
    This involves detailed simulation of each route to get precise timings.
    """
    optimised_routes_output = []
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)
    return_to_warehouse_flag = params.get("return_to_warehouse", True)

    assigned_parcel_ids_globally = set()

    for agent_id, parcel_ids_in_route in best_routes_struct.items():
        if not parcel_ids_in_route and not return_to_warehouse_flag : # Skip agent if no parcels and no mandatory WH return
            continue

        agent_config = agents_map[agent_id]
        agent_op_start = agent_config.get("operating_hours_start", 0)
        
        route_stop_ids = ["Warehouse"] + parcel_ids_in_route
        if return_to_warehouse_flag or not parcel_ids_in_route :
             route_stop_ids.append("Warehouse")
        
        # Handle case where route might be just ["Warehouse", "Warehouse"] if no parcels & return_to_wh
        if len(route_stop_ids) == 2 and route_stop_ids[0] == "Warehouse" and route_stop_ids[1] == "Warehouse" and not parcel_ids_in_route:
            # This agent has an empty route but must "return" to warehouse.
            # Useful if we want to show all agents, even if unused.
             optimised_routes_output.append({
                "agent_id": agent_id,
                "parcels_assigned_ids": [],
                "parcels_assigned_details": [],
                "route_stop_ids": ["Warehouse", "Warehouse"],
                "route_stop_coordinates": [list(warehouse_coords), list(warehouse_coords)],
                "total_weight": 0,
                "capacity_weight": agent_config["capacity_weight"],
                "total_distance": 0.0,
                "arrival_times": [round(agent_op_start), round(agent_op_start)],
                "departure_times": [round(agent_op_start), round(agent_op_start)]
            })
             continue
        elif not parcel_ids_in_route : # No parcels, and not forced to have WH-WH route
            continue


        current_time = float(agent_op_start)
        current_total_weight = 0
        route_total_dist = 0.0
        
        # For output structure
        output_parcels_details = []
        output_route_stop_coords = []
        output_arrival_times = []
        output_departure_times = []

        # Initial stop (Warehouse)
        output_route_stop_coords.append(list(warehouse_coords))
        output_arrival_times.append(round(current_time)) # Arrival at WH is start time
        output_departure_times.append(round(current_time))# Departure from WH is start time

        current_loc_for_calc = list(warehouse_coords)

        for i in range(1, len(route_stop_ids)): # Start from the first actual parcel or final warehouse
            to_stop_id = route_stop_ids[i]
            to_coords = _get_coords(to_stop_id, warehouse_coords, parcels_map)
            
            dist = _calculate_distance(current_loc_for_calc, to_coords)
            route_total_dist += dist
            travel_time = dist * time_per_dist_unit
            
            arrival_at_current_physical = current_time + travel_time
            
            output_route_stop_coords.append(list(to_coords))
            output_arrival_times.append(round(arrival_at_current_physical))

            if to_stop_id == "Warehouse": # Final warehouse stop
                current_time = arrival_at_current_physical
                output_departure_times.append(round(current_time)) # Arrival and departure are same
            else: # Parcel stop
                parcel_obj = parcels_map[to_stop_id]
                output_parcels_details.append(copy.deepcopy(parcel_obj)) # Store full detail
                assigned_parcel_ids_globally.add(to_stop_id)

                parcel_tw_open = parcel_obj.get("time_window_open", 0)
                parcel_service_time = parcel_obj.get("service_time", default_service_time)
                
                # Wait if arriving early
                actual_service_start_time = max(arrival_at_current_physical, parcel_tw_open)
                departure_from_current = actual_service_start_time + parcel_service_time
                
                output_departure_times.append(round(departure_from_current))
                
                current_time = departure_from_current
                current_total_weight += parcel_obj["weight"]
                current_loc_for_calc = list(to_coords)
        
        optimised_routes_output.append({
            "agent_id": agent_id,
            "parcels_assigned_ids": [p["id"] for p in output_parcels_details],
            "parcels_assigned_details": output_parcels_details,
            "route_stop_ids": route_stop_ids,
            "route_stop_coordinates": output_route_stop_coords,
            "total_weight": current_total_weight,
            "capacity_weight": agent_config["capacity_weight"],
            "total_distance": round(route_total_dist, 2),
            "arrival_times": output_arrival_times,
            "departure_times": output_departure_times
        })

    # Determine truly unassigned parcels for the final output
    all_configured_parcel_ids = {p["id"] for p in parcels_map.values()}
    final_unassigned_output_ids = list(all_configured_parcel_ids - assigned_parcel_ids_globally)
    final_unassigned_details = [parcels_map[pid] for pid in final_unassigned_output_ids]


    return {
        "status": "success", # Or "partial_success" if unassigned_parcels exist
        "message": "Simulated Annealing optimisation completed.",
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": final_unassigned_output_ids,
        "unassigned_parcels_details": final_unassigned_details
    }

# --- Main Optimisation Function and Schema ---

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "initial_temperature", "label": "Initial Temperature",
                "type": "float", "default": 10000.0, "min": 1.0, "step": 100.0,
                "help": "Starting temperature for SA."
            },
            {
                "name": "cooling_rate", "label": "Cooling Rate",
                "type": "float", "default": 0.99, "min": 0.8, "max": 0.999, "step": 0.001,
                "help": "Factor to reduce temperature (e.g., 0.99)."
            },
            {
                "name": "min_temperature", "label": "Minimum Temperature",
                "type": "float", "default": 0.1, "min": 0.001, "step": 0.1,
                "help": "Temperature at which SA stops."
            },
            {
                "name": "iterations_per_temperature", "label": "Iterations per Temperature",
                "type": "integer", "default": 100, "min": 10, "step": 10,
                "help": "Number of neighbors to explore at each temperature."
            },
            {
                "name": "time_per_distance_unit", "label": "Time per distance unit (minutes)",
                "type": "float", "default": 2.0, "min": 0.1, "step": 0.1,
                "help": "Minutes to travel one distance unit."
            },
            {
                "name": "default_service_time", "label": "Default service time (minutes)",
                "type": "integer", "default": 10, "min": 0, "step": 1,
                "help": "Default time spent at each parcel stop."
            },
            {
                "name": "return_to_warehouse", "label": "Return to warehouse",
                "type": "boolean", "default": True,
                "help": "Vehicles must return to warehouse."
            },
            {
                "name": "penalty_unassigned_parcel", "label": "Penalty: Unassigned Parcel",
                "type": "float", "default": 1000.0, "min": 0, "step": 100.0,
                "help": "Cost penalty for each unassigned parcel."
            },
            {
                "name": "penalty_over_capacity", "label": "Penalty: Over Capacity",
                "type": "float", "default": 100.0, "min": 0, "step": 10.0,
                "help": "Cost penalty per unit of exceeding agent capacity."
            },
            {
                "name": "penalty_time_window_violation", "label": "Penalty: Time Window Violation",
                "type": "float", "default": 50.0, "min": 0, "step": 5.0,
                "help": "Cost penalty per minute of time window violation."
            },
            {
                "name": "penalty_op_hour_violation", "label": "Penalty: Operating Hour Violation",
                "type": "float", "default": 200.0, "min": 0, "step": 10.0,
                "help": "Cost penalty per minute of operating hour violation."
            },
            {
                "name": "prob_move_assigned_to_unassigned", "label": "Prob: Parcel to Unassigned",
                "type": "float", "default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01,
                "help": "Probability of moving an assigned parcel to unassigned list."
            },
            {
                "name": "prob_move_unassigned_to_assigned", "label": "Prob: Unassigned to Parcel",
                "type": "float", "default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01,
                "help": "Probability of assigning an unassigned parcel to a route."
            },
            {
                "name": "prob_intra_route_swap", "label": "Prob: Intra-Route Swap",
                "type": "float", "default": 0.30, "min": 0.0, "max": 1.0, "step": 0.01,
                "help": "Probability of swapping two parcels within the same route."
            }
            # The remaining probability is for inter-route moves
        ]
    }

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels_list = config_data.get("parcels", []) # list of dicts
    agents_list = config_data.get("delivery_agents", []) # list of dicts

    # Create maps for easy lookup
    parcels_map = {p["id"]: p for p in parcels_list}
    agents_map = {a["id"]: a for a in agents_list}

    # SA Parameters
    temperature = params.get("initial_temperature", 10000.0)
    cooling_rate = params.get("cooling_rate", 0.99)
    min_temperature = params.get("min_temperature", 0.1)
    iterations_per_temp = params.get("iterations_per_temperature", 100)

    # Initial Solution
    current_routes_struct, current_unassigned_ids = _generate_initial_solution(parcels_list, agents_list, parcels_map)
    current_cost = _evaluate_solution(current_routes_struct, current_unassigned_ids,
                                      agents_map, parcels_map, warehouse_coords, params)
    
    best_routes_struct = copy.deepcopy(current_routes_struct)
    best_unassigned_ids = list(current_unassigned_ids)
    best_cost = current_cost

    print(f"SA Initial Cost: {current_cost}")

    # SA Main Loop
    while temperature > min_temperature:
        for _ in range(iterations_per_temp):
            neighbor_routes_struct, neighbor_unassigned_ids = _get_neighbor_solution(
                current_routes_struct, current_unassigned_ids,
                parcels_list, agents_list, parcels_map, params
            )
            neighbor_cost = _evaluate_solution(neighbor_routes_struct, neighbor_unassigned_ids,
                                               agents_map, parcels_map, warehouse_coords, params)

            cost_diff = neighbor_cost - current_cost
            if cost_diff < 0 or random.random() < math.exp(-cost_diff / temperature):
                current_routes_struct = neighbor_routes_struct
                current_unassigned_ids = neighbor_unassigned_ids
                current_cost = neighbor_cost

                if current_cost < best_cost:
                    best_routes_struct = copy.deepcopy(current_routes_struct)
                    best_unassigned_ids = list(current_unassigned_ids)
                    best_cost = current_cost
        
        temperature *= cooling_rate
        # print(f"Temp: {temperature:.2f}, Current Cost: {current_cost:.2f}, Best Cost: {best_cost:.2f}")


    print(f"SA Final Best Cost: {best_cost}")
    
    # Format the best solution found for output
    return _format_solution_for_output(best_routes_struct, best_unassigned_ids,
                                       agents_map, parcels_map, warehouse_coords, params)