# DVRS Optimisation Script: Genetic Algorithm
import math
import random
import copy

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

# --- GA Core Components ---

# 1. Representation:
# An individual solution will be a dictionary:
# {
#   "routes": {agent_id_1: [parcel_id_A, parcel_id_B], agent_id_2: [parcel_id_C]},
#   "unassigned": [parcel_id_D],
#   "fitness": float_score (lower is better for cost-based fitness)
# }

# 2. Initialization
def _create_random_individual(all_parcel_ids, agents_list, agents_map):
    """Creates a single random individual (solution)."""
    individual_routes = {agent["id"]: [] for agent in agents_list}
    individual_unassigned = []
    
    temp_parcels_to_assign = list(all_parcel_ids)
    random.shuffle(temp_parcels_to_assign)

    if not agents_list: # No agents, all unassigned
        individual_unassigned = temp_parcels_to_assign
    else:
        for parcel_id in temp_parcels_to_assign:
            # Assign to a random agent or leave unassigned (e.g. 20% chance to be unassigned)
            if random.random() < 0.2 and agents_list: # Chance to be unassigned initially
                 individual_unassigned.append(parcel_id)
            else:
                chosen_agent_id = random.choice(agents_list)['id']
                individual_routes[chosen_agent_id].append(parcel_id)
                # Optionally, shuffle parcels within a route for more randomness
                # random.shuffle(individual_routes[chosen_agent_id])


    return {"routes": individual_routes, "unassigned": individual_unassigned, "fitness": float('inf')}

def _initialize_population(population_size, all_parcel_ids, agents_list, agents_map):
    """Initializes a population of random individuals."""
    population = []
    for _ in range(population_size):
        population.append(_create_random_individual(all_parcel_ids, agents_list, agents_map))
    return population

# 3. Fitness Evaluation
def _calculate_fitness(individual, agents_map, parcels_map, warehouse_coords, params):
    """
    Evaluates the cost of an individual. Lower cost is better fitness.
    Very similar to SA's _evaluate_solution.
    """
    total_cost = 0.0 # Use float for costs
    routes_struct = individual["routes"]
    unassigned_parcel_ids = individual["unassigned"]

    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)
    return_to_warehouse = params.get("return_to_warehouse", True)

    penalty_factor_unassigned = params.get("penalty_unassigned_parcel", 1000.0)
    penalty_factor_capacity = params.get("penalty_over_capacity", 100.0)
    penalty_factor_tw = params.get("penalty_time_window_violation", 50.0)
    penalty_factor_ophours = params.get("penalty_op_hour_violation", 200.0)

    total_cost += len(unassigned_parcel_ids) * penalty_factor_unassigned

    for agent_id, parcel_ids_for_agent in routes_struct.items():
        agent_config = agents_map.get(agent_id)
        if not agent_config: continue # Should not happen if data is consistent

        agent_op_start = agent_config.get("operating_hours_start", 0)
        agent_op_end = agent_config.get("operating_hours_end", 1439)
        agent_capacity = agent_config["capacity_weight"]

        current_route_stops = ["Warehouse"] + parcel_ids_for_agent
        if return_to_warehouse or not parcel_ids_for_agent:
            current_route_stops.append("Warehouse")
        
        if not parcel_ids_for_agent and len(current_route_stops) <=2 : # Only ["Warehouse", "Warehouse"] or less
            continue


        current_time = float(agent_op_start)
        current_loc_coords = list(warehouse_coords)
        current_weight_on_agent = 0
        route_dist_for_agent = 0.0

        # First pass to check capacity only, as it's cumulative
        temp_weight_check = 0
        for parcel_id in parcel_ids_for_agent:
            parcel_obj = parcels_map.get(parcel_id)
            if parcel_obj:
                temp_weight_check += parcel_obj["weight"]
        if temp_weight_check > agent_capacity:
            total_cost += (temp_weight_check - agent_capacity) * penalty_factor_capacity


        # Simulate route for time-based penalties and distance
        for i in range(len(current_route_stops) -1):
            from_stop_id = current_route_stops[i]
            to_stop_id = current_route_stops[i+1]

            from_coords = _get_coords(from_stop_id, warehouse_coords, parcels_map)
            to_coords = _get_coords(to_stop_id, warehouse_coords, parcels_map)
            
            if from_coords is None or to_coords is None: continue # Should not happen

            dist = _calculate_distance(from_coords, to_coords)
            route_dist_for_agent += dist
            travel_time = dist * time_per_dist_unit
            arrival_at_to_stop = current_time + travel_time

            if to_stop_id == "Warehouse":
                current_time = arrival_at_to_stop
                if i == len(current_route_stops) - 2: # Final arrival at warehouse
                    if current_time > agent_op_end:
                        total_cost += (current_time - agent_op_end) * penalty_factor_ophours
            else:
                parcel_obj = parcels_map.get(to_stop_id)
                if not parcel_obj: continue

                parcel_tw_open = parcel_obj.get("time_window_open", 0)
                parcel_tw_close = parcel_obj.get("time_window_close", 1439)
                parcel_service_time = parcel_obj.get("service_time", default_service_time)

                service_start_time = max(arrival_at_to_stop, parcel_tw_open)
                
                # TW Violation at arrival (before service)
                if arrival_at_to_stop > parcel_tw_close:
                     total_cost += (arrival_at_to_stop - parcel_tw_close) * penalty_factor_tw * 1.5 # Heavier if late for window start

                service_end_time = service_start_time + parcel_service_time

                # TW Violation at departure (after service)
                if service_end_time > parcel_tw_close:
                    total_cost += (service_end_time - parcel_tw_close) * penalty_factor_tw
                
                # Operating Hour Violation
                if service_end_time > agent_op_end:
                    total_cost += (service_end_time - agent_op_end) * penalty_factor_ophours
                
                current_time = service_end_time
                current_loc_coords = list(to_coords)
        
        total_cost += route_dist_for_agent
    
    individual["fitness"] = total_cost # Store fitness in the individual
    return total_cost


# 4. Selection
def _tournament_selection(population, tournament_size):
    """Selects a parent using tournament selection."""
    if not population: return None
    tournament = random.sample(population, min(tournament_size, len(population)))
    # Assumes fitness is cost, so lower is better
    return min(tournament, key=lambda ind: ind["fitness"])


# 5. Crossover (Agent-based route swap)
def _crossover(parent1, parent2, agents_list, all_parcel_ids_set):
    """
    Performs agent-based crossover. Offspring inherit routes agent by agent
    from either parent1 or parent2. Then repairs to ensure parcel validity.
    """
    offspring1_routes = {agent["id"]: [] for agent in agents_list}
    offspring2_routes = {agent["id"]: [] for agent in agents_list}

    for agent in agents_list:
        agent_id = agent["id"]
        if random.random() < 0.5:
            offspring1_routes[agent_id] = list(parent1["routes"].get(agent_id, []))
            offspring2_routes[agent_id] = list(parent2["routes"].get(agent_id, []))
        else:
            offspring1_routes[agent_id] = list(parent2["routes"].get(agent_id, []))
            offspring2_routes[agent_id] = list(parent1["routes"].get(agent_id, []))

    # Repair offspring to ensure parcel validity
    def repair_offspring(off_routes):
        parcels_in_routes = set()
        # First pass: remove duplicates within the offspring's routes
        for agent_id_r in off_routes:
            unique_parcels_for_agent = []
            seen_on_agent = set()
            for p_id in off_routes[agent_id_r]:
                if p_id not in seen_on_agent:
                    unique_parcels_for_agent.append(p_id)
                    seen_on_agent.add(p_id)
            off_routes[agent_id_r] = unique_parcels_for_agent
            parcels_in_routes.update(unique_parcels_for_agent)
        
        # Second pass: identify overall duplicates across agents and unassign them
        # This is complex. A simpler repair for now:
        # Collect all parcels assigned in routes, then determine unassigned.
        current_assigned_parcels = set()
        for r in off_routes.values():
            current_assigned_parcels.update(r)
        
        # Rebuild routes to ensure no parcel is in multiple agent routes (greedy)
        # This simplified repair might alter routes significantly
        final_routes_repaired = {agent["id"]: [] for agent in agents_list}
        parcels_definitively_assigned = set()
        
        # Take parcels as they appear in the input `off_routes`
        # This implicitly gives priority to earlier agents or earlier parcels in lists
        for agent_id_iter, parcel_ids_iter in off_routes.items():
            for p_id_iter in parcel_ids_iter:
                if p_id_iter in all_parcel_ids_set and p_id_iter not in parcels_definitively_assigned:
                    final_routes_repaired[agent_id_iter].append(p_id_iter)
                    parcels_definitively_assigned.add(p_id_iter)

        unassigned = list(all_parcel_ids_set - parcels_definitively_assigned)
        return final_routes_repaired, unassigned

    repaired_o1_routes, unassigned_o1 = repair_offspring(offspring1_routes)
    repaired_o2_routes, unassigned_o2 = repair_offspring(offspring2_routes)
    
    return (
        {"routes": repaired_o1_routes, "unassigned": unassigned_o1, "fitness": float('inf')},
        {"routes": repaired_o2_routes, "unassigned": unassigned_o2, "fitness": float('inf')}
    )


# 6. Mutation
def _mutate(individual, agents_list, all_parcel_ids_set, mutation_rate_param, params):
    """Applies random mutations to an individual."""
    new_individual = copy.deepcopy(individual) # Work on a copy

    # Mutation 1: Swap two parcels within a random agent's route
    if random.random() < mutation_rate_param:
        eligible_agents = [aid for aid, p_ids in new_individual["routes"].items() if len(p_ids) >= 2]
        if eligible_agents:
            agent_to_mutate = random.choice(eligible_agents)
            idx1, idx2 = random.sample(range(len(new_individual["routes"][agent_to_mutate])), 2)
            route = new_individual["routes"][agent_to_mutate]
            route[idx1], route[idx2] = route[idx2], route[idx1]

    # Mutation 2: Move a parcel from one agent to another (or to a new position in same agent)
    if random.random() < mutation_rate_param:
        source_agents_with_parcels = [aid for aid, p_ids in new_individual["routes"].items() if p_ids]
        if source_agents_with_parcels and agents_list:
            source_agent_id = random.choice(source_agents_with_parcels)
            target_agent_id = random.choice(agents_list)['id'] # Can be same agent

            parcel_idx_to_move = random.randrange(len(new_individual["routes"][source_agent_id]))
            parcel_to_move = new_individual["routes"][source_agent_id].pop(parcel_idx_to_move)
            
            insert_idx = 0
            if new_individual["routes"][target_agent_id]:
                insert_idx = random.randrange(len(new_individual["routes"][target_agent_id]) + 1)
            new_individual["routes"][target_agent_id].insert(insert_idx, parcel_to_move)

    # Mutation 3: Move a parcel from a route to unassigned
    if random.random() < mutation_rate_param:
        agents_with_parcels = [aid for aid, p_ids in new_individual["routes"].items() if p_ids]
        if agents_with_parcels:
            agent_id = random.choice(agents_with_parcels)
            parcel_idx = random.randrange(len(new_individual["routes"][agent_id]))
            parcel_moved = new_individual["routes"][agent_id].pop(parcel_idx)
            if parcel_moved not in new_individual["unassigned"]:
                 new_individual["unassigned"].append(parcel_moved)
    
    # Mutation 4: Move a parcel from unassigned to a random agent's route
    if random.random() < mutation_rate_param:
        if new_individual["unassigned"] and agents_list:
            parcel_to_assign = random.choice(new_individual["unassigned"])
            agent_id = random.choice(agents_list)['id']
            
            insert_idx = 0
            if new_individual["routes"][agent_id]:
                insert_idx = random.randrange(len(new_individual["routes"][agent_id])+1)
            new_individual["routes"][agent_id].insert(insert_idx, parcel_to_assign)
            new_individual["unassigned"].remove(parcel_to_assign)
            
    # Re-calculate fitness after mutation
    _calculate_fitness(new_individual, params['agents_map_ref'], params['parcels_map_ref'], params['warehouse_coords_ref'], params)
    return new_individual

# --- Formatting Output (Similar to SA) ---
def _format_solution_for_output(best_individual, agents_map, parcels_map, warehouse_coords, params):
    """Formats the best GA individual into the required DVRS output structure."""
    optimised_routes_output = []
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)
    return_to_warehouse_flag = params.get("return_to_warehouse", True)
    
    best_routes_struct = best_individual["routes"]
    final_unassigned_ids = best_individual["unassigned"]
    assigned_parcel_ids_globally = set()

    for agent_id, parcel_ids_in_route in best_routes_struct.items():
        agent_config = agents_map.get(agent_id)
        if not agent_config: continue
        
        if not parcel_ids_in_route and not return_to_warehouse_flag:
            continue

        agent_op_start = agent_config.get("operating_hours_start", 0)
        route_stop_ids_final = ["Warehouse"] + parcel_ids_in_route
        if return_to_warehouse_flag or not parcel_ids_in_route:
            route_stop_ids_final.append("Warehouse")

        if not parcel_ids_in_route and len(route_stop_ids_final) <= 2 :
             if params.get("include_empty_routes_in_output", False): # Optional param
                optimised_routes_output.append({
                    "agent_id": agent_id, "parcels_assigned_ids": [], "parcels_assigned_details": [],
                    "route_stop_ids": ["Warehouse", "Warehouse"],
                    "route_stop_coordinates": [list(warehouse_coords), list(warehouse_coords)],
                    "total_weight": 0, "capacity_weight": agent_config["capacity_weight"],
                    "total_distance": 0.0,
                    "arrival_times": [round(agent_op_start)] * 2, "departure_times": [round(agent_op_start)] * 2
                })
             continue


        current_time_sim = float(agent_op_start)
        current_total_weight_sim = 0
        route_total_dist_sim = 0.0
        
        output_parcels_details = []
        output_route_stop_coords_sim = [list(warehouse_coords)]
        output_arrival_times_sim = [round(current_time_sim)]
        output_departure_times_sim = [round(current_time_sim)]
        current_loc_for_calc_sim = list(warehouse_coords)

        for stop_idx in range(1, len(route_stop_ids_final)):
            to_stop_id_sim = route_stop_ids_final[stop_idx]
            to_coords_sim = _get_coords(to_stop_id_sim, warehouse_coords, parcels_map)
            if to_coords_sim is None: continue

            dist_sim = _calculate_distance(current_loc_for_calc_sim, to_coords_sim)
            route_total_dist_sim += dist_sim
            travel_time_sim = dist_sim * time_per_dist_unit
            arrival_at_current_physical_sim = current_time_sim + travel_time_sim
            
            output_route_stop_coords_sim.append(list(to_coords_sim))
            output_arrival_times_sim.append(round(arrival_at_current_physical_sim))

            if to_stop_id_sim == "Warehouse":
                current_time_sim = arrival_at_current_physical_sim
                output_departure_times_sim.append(round(current_time_sim))
            else:
                parcel_obj_sim = parcels_map.get(to_stop_id_sim)
                if not parcel_obj_sim: continue

                output_parcels_details.append(copy.deepcopy(parcel_obj_sim))
                assigned_parcel_ids_globally.add(to_stop_id_sim)

                parcel_tw_open_sim = parcel_obj_sim.get("time_window_open", 0)
                parcel_service_time_sim = parcel_obj_sim.get("service_time", default_service_time)
                
                actual_service_start_time_sim = max(arrival_at_current_physical_sim, parcel_tw_open_sim)
                departure_from_current_sim = actual_service_start_time_sim + parcel_service_time_sim
                
                output_departure_times_sim.append(round(departure_from_current_sim))
                
                current_time_sim = departure_from_current_sim
                current_total_weight_sim += parcel_obj_sim["weight"]
                current_loc_for_calc_sim = list(to_coords_sim)
        
        optimised_routes_output.append({
            "agent_id": agent_id,
            "parcels_assigned_ids": [p["id"] for p in output_parcels_details],
            "parcels_assigned_details": output_parcels_details,
            "route_stop_ids": route_stop_ids_final,
            "route_stop_coordinates": output_route_stop_coords_sim,
            "total_weight": current_total_weight_sim,
            "capacity_weight": agent_config["capacity_weight"],
            "total_distance": round(route_total_dist_sim, 2),
            "arrival_times": output_arrival_times_sim,
            "departure_times": output_departure_times_sim
        })
    
    all_configured_parcel_ids = {p["id"] for p in parcels_map.values()}
    final_unassigned_output_ids = list(all_configured_parcel_ids - assigned_parcel_ids_globally)
    final_unassigned_details = [parcels_map[pid] for pid in final_unassigned_output_ids if pid in parcels_map]

    return {
        "status": "success",
        "message": "Genetic Algorithm optimisation completed.",
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": final_unassigned_output_ids,
        "unassigned_parcels_details": final_unassigned_details
    }


# --- Main Optimisation Function and Schema ---
def get_params_schema():
    return {
        "parameters": [
            # GA Control
            {
                "name": "population_size", "label": "Population Size",
                "type": "integer", "default": 50, "min": 10, "step": 10,
                "help": "Number of individuals in each generation."
            },
            {
                "name": "num_generations", "label": "Number of Generations",
                "type": "integer", "default": 100, "min": 10, "step": 10,
                "help": "Total number of generations to run."
            },
            {
                "name": "crossover_rate", "label": "Crossover Rate",
                "type": "float", "default": 0.8, "min": 0.0, "max": 1.0, "step": 0.05,
                "help": "Probability of performing crossover."
            },
            {
                "name": "mutation_rate", "label": "Mutation Rate (per individual)",
                "type": "float", "default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01,
                "help": "Probability an individual undergoes mutation."
            },
             {
                "name": "mutation_strength", "label": "Mutation Strength (per gene/op)",
                "type": "float", "default": 0.2, "min": 0.01, "max": 1.0, "step": 0.01,
                "help": "Probability of a specific mutation operation occurring if individual is selected for mutation."
            },
            {
                "name": "tournament_size", "label": "Tournament Size",
                "type": "integer", "default": 5, "min": 2, "step": 1,
                "help": "Number of individuals in a selection tournament."
            },
            {
                "name": "elitism_count", "label": "Elitism Count",
                "type": "integer", "default": 2, "min": 0, "step": 1,
                "help": "Number of best individuals to carry over to next generation."
            },
            # VRP Specifics (copied from SA, ensure steps are float for float types)
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
            # Penalties
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
                "name": "include_empty_routes_in_output", "label": "Include empty routes in output",
                "type": "boolean", "default": False,
                "help": "If true, agents with no assigned parcels will still appear in output (as Warehouse -> Warehouse)."
            }
        ]
    }

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels_list = config_data.get("parcels", [])
    agents_list = config_data.get("delivery_agents", [])

    parcels_map = {p["id"]: p for p in parcels_list}
    agents_map = {a["id"]: a for a in agents_list}
    all_parcel_ids_set = set(parcels_map.keys())
    
    # Store maps and warehouse_coords in params for easy access in fitness/mutation
    # This is a bit of a workaround to pass more data to static/helper methods
    # without changing their signatures drastically.
    params['agents_map_ref'] = agents_map
    params['parcels_map_ref'] = parcels_map
    params['warehouse_coords_ref'] = warehouse_coords


    population_size = params.get("population_size", 50)
    num_generations = params.get("num_generations", 100)
    crossover_rate = params.get("crossover_rate", 0.8)
    mutation_rate_individual = params.get("mutation_rate", 0.1) # Renamed for clarity
    mutation_strength_gene = params.get("mutation_strength", 0.2) # Renamed for clarity
    tournament_size = params.get("tournament_size", 5)
    elitism_count = params.get("elitism_count", 2)

    # Initialize population
    population = _initialize_population(population_size, list(all_parcel_ids_set), agents_list, agents_map)

    # Evaluate initial population
    for ind in population:
        _calculate_fitness(ind, agents_map, parcels_map, warehouse_coords, params)

    best_overall_individual = min(population, key=lambda ind: ind["fitness"])
    print(f"GA Initial Best Fitness: {best_overall_individual['fitness']}")

    # GA Main Loop
    for gen in range(num_generations):
        new_population = []

        # Elitism: Carry over best individuals
        if elitism_count > 0:
            population.sort(key=lambda ind: ind["fitness"]) # Sort by fitness (lower is better)
            new_population.extend(copy.deepcopy(population[:elitism_count]))

        # Fill the rest of the population
        while len(new_population) < population_size:
            parent1 = _tournament_selection(population, tournament_size)
            parent2 = _tournament_selection(population, tournament_size)
            
            if parent1 is None or parent2 is None : # Should not happen with proper population
                # Fallback: add random individuals if selection fails
                new_population.append(_create_random_individual(list(all_parcel_ids_set), agents_list, agents_map))
                _calculate_fitness(new_population[-1], agents_map, parcels_map, warehouse_coords, params)
                continue

            offspring1, offspring2 = parent1, parent2 # Default to parents if no crossover
            if random.random() < crossover_rate:
                offspring1, offspring2 = _crossover(parent1, parent2, agents_list, all_parcel_ids_set)
            
            # Mutate offspring (or parents if no crossover)
            if random.random() < mutation_rate_individual:
                offspring1 = _mutate(offspring1, agents_list, all_parcel_ids_set, mutation_strength_gene, params)
            if random.random() < mutation_rate_individual:
                offspring2 = _mutate(offspring2, agents_list, all_parcel_ids_set, mutation_strength_gene, params)

            # Calculate fitness for new offspring (if not already done in mutate)
            _calculate_fitness(offspring1, agents_map, parcels_map, warehouse_coords, params)
            _calculate_fitness(offspring2, agents_map, parcels_map, warehouse_coords, params)

            new_population.append(offspring1)
            if len(new_population) < population_size:
                new_population.append(offspring2)
        
        population = new_population
        current_gen_best_ind = min(population, key=lambda ind: ind["fitness"])

        if current_gen_best_ind["fitness"] < best_overall_individual["fitness"]:
            best_overall_individual = copy.deepcopy(current_gen_best_ind)
        
        if (gen + 1) % 10 == 0: # Log every 10 generations
             print(f"Generation {gen+1}/{num_generations} - Best Fitness: {best_overall_individual['fitness']:.2f}, Current Gen Best: {current_gen_best_ind['fitness']:.2f}")


    print(f"GA Final Best Fitness: {best_overall_individual['fitness']}")
    return _format_solution_for_output(best_overall_individual, agents_map, parcels_map, warehouse_coords, params)