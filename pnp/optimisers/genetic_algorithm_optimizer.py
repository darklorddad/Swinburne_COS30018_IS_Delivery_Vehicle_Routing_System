# DVRS Optimisation Script: Genetic Algorithm
import math
import random
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "population_size",
                "label": "Population Size",
                "type": "integer",
                "default": 50,
                "min": 10,
                "max": 200,
                "step": 5,
                "help": "Number of solutions in the population"
            },
            {
                "name": "generations",
                "label": "Number of Generations",
                "type": "integer",
                "default": 100,
                "min": 10,
                "max": 500,
                "step": 10,
                "help": "Number of generations to evolve"
            },
            {
                "name": "crossover_rate",
                "label": "Crossover Rate",
                "type": "float",
                "default": 0.8,
                "min": 0.5,
                "max": 1.0,
                "step": 0.05,
                "help": "Probability of crossover"
            },
            {
                "name": "mutation_rate",
                "label": "Mutation Rate",
                "type": "float",
                "default": 0.2,
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "help": "Probability of mutation"
            },
            {
                "name": "elitism_count",
                "label": "Elitism Count",
                "type": "integer",
                "default": 5,
                "min": 1,
                "max": 20,
                "step": 1,
                "help": "Number of best solutions to keep unchanged"
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries"
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_distance(route, warehouse_coords, return_to_warehouse):
    """Calculate total distance for a route."""
    if not route:
        return 0.0
    
    total_distance = _calculate_distance(warehouse_coords, route[0]["coordinates_x_y"])
    
    for i in range(len(route) - 1):
        total_distance += _calculate_distance(route[i]["coordinates_x_y"], route[i+1]["coordinates_x_y"])
    
    if return_to_warehouse and route:
        total_distance += _calculate_distance(route[-1]["coordinates_x_y"], warehouse_coords)
    
    return total_distance

# MODIFIED: _calculate_solution_fitness
def _calculate_solution_fitness(solution, delivery_agents, warehouse_coords, return_to_warehouse, all_parcels_list):
    """
    Calculate fitness (inverse of total cost) for a solution.
    Major penalties for capacity violations and unassigned parcels.
    Minor penalty for unused agents if all parcels are assigned.
    """
    actual_travel_distance = 0.0
    assigned_parcel_ids_in_solution = set()
    num_total_parcels = len(all_parcels_list)
    num_agents = len(delivery_agents)

    # 1. Check capacity constraints and collect assigned parcel IDs
    for route_idx, route in enumerate(solution):
        current_route_weight = 0
        if route: # If route is not empty
            for parcel in route:
                current_route_weight += parcel["weight"]
                assigned_parcel_ids_in_solution.add(parcel["id"])
        
        if current_route_weight > delivery_agents[route_idx]["capacity_weight"]:
            return 0.00001  # Very low fitness for capacity violation

        # Accumulate actual travel distance for this route
        actual_travel_distance += _calculate_route_distance(route, warehouse_coords, return_to_warehouse)

    # 2. Check if all parcels are assigned (PRIMARY CONSTRAINT)
    if num_total_parcels > 0 and len(assigned_parcel_ids_in_solution) < num_total_parcels:
        unassigned_count = num_total_parcels - len(assigned_parcel_ids_in_solution)
        # Effective cost is massively increased by unassigned parcels.
        # This ensures solutions that fail to assign all parcels are heavily penalized.
        # The penalty is proportional to the number of unassigned parcels.
        # A large constant (e.g., 100,000) makes this dominant over travel distance.
        penalty_constant_unassigned = 100000  
        effective_cost = (penalty_constant_unassigned * unassigned_count) + actual_travel_distance
        return 1.0 / (effective_cost + 0.1) # Add 0.1 to avoid division by zero

    # At this point, solution is valid w.r.t. capacity and all parcels are assigned (if any parcels exist).
    # actual_travel_distance holds the sum of route distances.

    cost_to_invert = actual_travel_distance

    # 3. Secondary goal: Encourage using all agents (if there are parcels to deliver)
    if num_total_parcels > 0: # Only apply this penalty if there's work to do
        num_active_agents = sum(1 for r in solution if r) # Count agents with actual deliveries
        if num_active_agents < num_agents:
            # Add a penalty for each inactive agent.
            # This penalty should be noticeable but smaller than typical route distances,
            # acting as a tie-breaker or a gentle nudge towards utilizing more agents.
            # This value might need tuning based on typical problem scales.
            penalty_per_inactive_agent = 50  # Heuristic value
            cost_to_invert += (num_agents - num_active_agents) * penalty_per_inactive_agent
    
    return 1.0 / (cost_to_invert + 0.1) # Add 0.1 to avoid division by zero

def _generate_random_solution(parcels, delivery_agents):
    """Generate a random initial solution."""
    solution = [[] for _ in delivery_agents] # One empty route for each agent
    
    parcel_indices = list(range(len(parcels)))
    random.shuffle(parcel_indices)
    
    for parcel_idx in parcel_indices:
        parcel = parcels[parcel_idx]
        
        agent_indices = list(range(len(delivery_agents)))
        random.shuffle(agent_indices)
        
        assigned_this_parcel = False
        for agent_idx in agent_indices:
            current_weight = sum(p["weight"] for p in solution[agent_idx])
            if current_weight + parcel["weight"] <= delivery_agents[agent_idx]["capacity_weight"]:
                solution[agent_idx].append(parcel)
                assigned_this_parcel = True
                break
        # If parcel is not assigned after trying all agents, it remains unassigned.
        # The fitness function will heavily penalize this.
    
    return solution

def _initialize_population(population_size, parcels, delivery_agents):
    """Initialize the population with random solutions."""
    return [_generate_random_solution(parcels, delivery_agents) for _ in range(population_size)]

def _select_parent(population, fitnesses):
    """Select parent using tournament selection."""
    tournament_size = 3
    # Ensure tournament size is not larger than population size
    actual_tournament_size = min(tournament_size, len(population))
    if actual_tournament_size == 0: # Should not happen if population exists
        return random.choice(population) if population else None


    tournament_indices = random.sample(range(len(population)), actual_tournament_size)
    tournament_fitnesses = [fitnesses[i] for i in tournament_indices]
    winner_idx = tournament_indices[tournament_fitnesses.index(max(tournament_fitnesses))]
    return population[winner_idx]

# MODIFIED: _crossover to accept all_parcels_list for repair
def _crossover(parent1, parent2, delivery_agents, all_parcels_list):
    """
    Perform crossover between two parents.
    Includes a phase to attempt assignment of any globally missing parcels.
    """
    if len(parent1) != len(parent2): # Should be guaranteed by solution structure
        raise ValueError("Parents must have the same number of routes (agents)")
    
    child = [[] for _ in range(len(parent1))] # Initialize empty routes for the child
    parcels_assigned_to_child_ids = set() # Track IDs of parcels assigned to the child

    # --- Phase 1: Inherit routes/parcels from parents ---
    for route_idx in range(len(parent1)):
        # Choose which parent's route to primarily draw from for this child's route
        source_parent_route = parent1[route_idx] if random.random() < 0.5 else parent2[route_idx]
        
        for parcel in source_parent_route:
            parcel_id = parcel["id"]
            # Check if this parcel is already assigned in the child
            if parcel_id not in parcels_assigned_to_child_ids:
                # Check capacity for the current child route
                current_child_route_weight = sum(p["weight"] for p in child[route_idx])
                if current_child_route_weight + parcel["weight"] <= delivery_agents[route_idx]["capacity_weight"]:
                    child[route_idx].append(copy.deepcopy(parcel)) # Store a copy of the parcel
                    parcels_assigned_to_child_ids.add(parcel_id)

    # --- Phase 2: Attempt to assign any globally unassigned parcels ---
    # This phase tries to ensure all parcels from the original problem are considered.
    if all_parcels_list: # Proceed if there's a list of all parcels
        parcels_map = {p["id"]: p for p in all_parcels_list}
        all_required_parcel_ids = set(parcels_map.keys())
        
        missing_parcel_ids = all_required_parcel_ids - parcels_assigned_to_child_ids

        if missing_parcel_ids:
            # Shuffle agent indices to try assigning to different agents randomly
            shuffled_agent_indices = list(range(len(delivery_agents)))
            random.shuffle(shuffled_agent_indices)

            for parcel_id_to_assign in missing_parcel_ids:
                parcel_object_to_add = parcels_map[parcel_id_to_assign]
                
                for agent_idx in shuffled_agent_indices:
                    current_child_route_weight = sum(p["weight"] for p in child[agent_idx])
                    if current_child_route_weight + parcel_object_to_add["weight"] <= delivery_agents[agent_idx]["capacity_weight"]:
                        child[agent_idx].append(copy.deepcopy(parcel_object_to_add))
                        # parcels_assigned_to_child_ids.add(parcel_id_to_assign) # Not strictly needed to re-add here
                        break # Parcel assigned, move to next missing parcel
    
    return child

def _mutate(solution, parcels, delivery_agents, mutation_rate):
    """Apply mutation to a solution. Ensures parcels are not lost."""
    mutated_solution = copy.deepcopy(solution) # Work on a deep copy
    
    # Overall mutation chance for the entire solution
    if random.random() < mutation_rate:
        # Choose a mutation type
        # More mutation types can be added (e.g., 2-opt for route optimization within an agent)
        mutation_type = random.choice(["swap_parcels_between_routes", "relocate_parcel", "shuffle_route_order"])
        
        num_agents = len(mutated_solution)

        if mutation_type == "swap_parcels_between_routes" and num_agents >= 2:
            # Attempt to swap one parcel between two different, non-empty routes
            # Find two distinct routes that are not empty
            non_empty_route_indices = [i for i, r in enumerate(mutated_solution) if r]
            if len(non_empty_route_indices) >= 2:
                route1_idx, route2_idx = random.sample(non_empty_route_indices, 2)
                
                # Select a random parcel from each chosen route
                parcel1_idx_in_route = random.randint(0, len(mutated_solution[route1_idx]) - 1)
                parcel2_idx_in_route = random.randint(0, len(mutated_solution[route2_idx]) - 1)
                
                parcel1 = mutated_solution[route1_idx][parcel1_idx_in_route]
                parcel2 = mutated_solution[route2_idx][parcel2_idx_in_route]
                
                # Check if swap is valid capacity-wise
                route1_weight_after_swap = (sum(p["weight"] for p in mutated_solution[route1_idx]) - parcel1["weight"] + parcel2["weight"])
                route2_weight_after_swap = (sum(p["weight"] for p in mutated_solution[route2_idx]) - parcel2["weight"] + parcel1["weight"])

                if (route1_weight_after_swap <= delivery_agents[route1_idx]["capacity_weight"] and
                    route2_weight_after_swap <= delivery_agents[route2_idx]["capacity_weight"]):
                    # Perform swap
                    mutated_solution[route1_idx][parcel1_idx_in_route] = parcel2
                    mutated_solution[route2_idx][parcel2_idx_in_route] = parcel1
        
        elif mutation_type == "relocate_parcel":
            # Attempt to move a parcel from one route to another (or within the same route)
            # Find a route with at least one parcel (source route)
            source_route_indices = [i for i, r in enumerate(mutated_solution) if r]
            if source_route_indices:
                source_idx = random.choice(source_route_indices)
                
                # Select a parcel to relocate
                parcel_idx_in_source_route = random.randint(0, len(mutated_solution[source_idx]) - 1)
                parcel_to_relocate = mutated_solution[source_idx].pop(parcel_idx_in_source_route) # Remove from source

                # Find a target route (can be the same or different)
                # Try to place it in a random position in any route, respecting capacity
                possible_target_agent_indices = list(range(num_agents))
                random.shuffle(possible_target_agent_indices)
                
                relocated = False
                for target_idx in possible_target_agent_indices:
                    current_target_route_weight = sum(p["weight"] for p in mutated_solution[target_idx])
                    if current_target_route_weight + parcel_to_relocate["weight"] <= delivery_agents[target_idx]["capacity_weight"]:
                        # Insert at a random position in the target route
                        target_pos = random.randint(0, len(mutated_solution[target_idx]))
                        mutated_solution[target_idx].insert(target_pos, parcel_to_relocate)
                        relocated = True
                        break
                
                if not relocated: # Could not find a valid spot
                    # Add parcel back to its original route (or try another strategy)
                    # For simplicity, we add it back to the source route. This might exceed capacity
                    # temporarily if the route was full, but fitness will penalize.
                    # A better approach might be to try harder to place it or revert mutation.
                    # However, GA can often recover from temporarily invalid states.
                    mutated_solution[source_idx].insert(parcel_idx_in_source_route, parcel_to_relocate)


        elif mutation_type == "shuffle_route_order":
            # Shuffle the order of parcels within a randomly selected non-empty route
            non_empty_route_indices = [i for i, r in enumerate(mutated_solution) if r]
            if non_empty_route_indices:
                route_to_shuffle_idx = random.choice(non_empty_route_indices)
                if len(mutated_solution[route_to_shuffle_idx]) > 1: # Shuffle only if more than one parcel
                    random.shuffle(mutated_solution[route_to_shuffle_idx])
    
    return mutated_solution

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels_input = config_data.get("parcels", [])
    delivery_agents_input = config_data.get("delivery_agents", [])
    
    population_size = params.get("population_size", 50)
    generations = params.get("generations", 100)
    crossover_rate = params.get("crossover_rate", 0.8)
    mutation_rate = params.get("mutation_rate", 0.2)
    elitism_count = params.get("elitism_count", 5)
    return_to_warehouse = params.get("return_to_warehouse", True)
    
    # Create deep copies to avoid modifying original input data structures
    parcels_copy = copy.deepcopy(parcels_input)
    delivery_agents_copy = copy.deepcopy(delivery_agents_input)

    if not parcels_copy and not delivery_agents_copy:
         return {
            "status": "success",
            "message": "No parcels or delivery agents provided. Optimisation not applicable.",
            "optimised_routes": [],
            "unassigned_parcels": [],
            "unassigned_parcels_details": []
        }
    if not delivery_agents_copy: # No agents to deliver
        return {
            "status": "error",
            "message": "No delivery agents available. Cannot assign parcels.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels_copy],
            "unassigned_parcels_details": parcels_copy
        }


    population = _initialize_population(population_size, parcels_copy, delivery_agents_copy)
    
    best_solution_overall = None
    best_fitness_overall = -1.0 # Initialize with a very low fitness

    for generation in range(generations):
        fitnesses = [
            _calculate_solution_fitness(sol, delivery_agents_copy, warehouse_coords, return_to_warehouse, parcels_copy) 
            for sol in population
        ]
        
        current_gen_best_idx = -1
        current_gen_best_fitness = -1.0
        if fitnesses: # Ensure fitnesses list is not empty
            current_gen_best_fitness = max(fitnesses)
            current_gen_best_idx = fitnesses.index(current_gen_best_fitness)

        if current_gen_best_idx != -1 and current_gen_best_fitness > best_fitness_overall:
            best_fitness_overall = current_gen_best_fitness
            best_solution_overall = copy.deepcopy(population[current_gen_best_idx])
            # print(f"Generation {generation}: New best fitness: {best_fitness_overall}") # For debugging

        next_population = []
        
        # Elitism
        if population: # Ensure population is not empty
            # Sort population by fitness (descending)
            sorted_population_indices = sorted(range(len(population)), key=lambda i: fitnesses[i], reverse=True)
            
            # Add elite individuals to the next generation
            num_elite_to_carry = min(elitism_count, len(population))
            for i in range(num_elite_to_carry):
                elite_idx = sorted_population_indices[i]
                next_population.append(copy.deepcopy(population[elite_idx]))
        
        # Generate the rest of the new population
        while len(next_population) < population_size:
            if not population: break # Should not happen if elitism added some, or if initial pop was > 0

            parent1 = _select_parent(population, fitnesses)
            parent2 = _select_parent(population, fitnesses)
            
            if parent1 is None or parent2 is None: # Safety check
                # Fallback: if selection fails, might add random individuals or skip
                # For now, if selection fails (e.g. empty population somehow), break
                if not population and len(next_population) < population_size: # try to re-initialize if pop is empty
                    next_population.extend(_initialize_population(population_size - len(next_population), parcels_copy, delivery_agents_copy))
                break


            child = copy.deepcopy(parent1) # Default to parent1 if no crossover
            if random.random() < crossover_rate:
                # MODIFIED: Pass all_parcels_list to crossover
                child = _crossover(parent1, parent2, delivery_agents_copy, parcels_copy)
            
            # MODIFIED: Pass all_parcels_list to mutate (though current mutate doesn't use it directly, good practice if it evolves)
            child = _mutate(child, parcels_copy, delivery_agents_copy, mutation_rate)
            
            next_population.append(child)
        
        population = next_population
        if not population and generations > 0 : # Population died out
            # print(f"Warning: Population empty at generation {generation}. Re-initializing.") # For debugging
            population = _initialize_population(population_size, parcels_copy, delivery_agents_copy)


    # --- Prepare results using the best solution found ---
    optimised_routes_output = []
    all_assigned_parcel_ids_in_best_solution = set()

    if best_solution_overall: # If a best solution was found
        for agent_idx, route_parcels in enumerate(best_solution_overall):
            agent_details = delivery_agents_copy[agent_idx]
            
            current_route_stop_ids = ["Warehouse"] # Start at warehouse
            current_route_parcels_details = []
            current_route_parcel_ids = []
            current_route_total_weight = 0

            if route_parcels: # If the agent has parcels assigned
                for parcel in route_parcels:
                    current_route_stop_ids.append(parcel["id"])
                    current_route_parcel_ids.append(parcel["id"])
                    current_route_parcels_details.append(parcel)
                    all_assigned_parcel_ids_in_best_solution.add(parcel["id"])
                    current_route_total_weight += parcel["weight"]
                
                if return_to_warehouse:
                    current_route_stop_ids.append("Warehouse") # Return to warehouse
            else: # Agent has no parcels
                if return_to_warehouse: # If policy is to return, an empty route implies Warehouse -> Warehouse (0 dist)
                    current_route_stop_ids.append("Warehouse")
                # If not return_to_warehouse, and no parcels, route_stop_ids remains ["Warehouse"]
            
            route_dist = _calculate_route_distance(route_parcels, warehouse_coords, return_to_warehouse)

            optimised_routes_output.append({
                "agent_id": agent_details["id"],
                "parcels_assigned_ids": current_route_parcel_ids,
                "parcels_assigned_details": current_route_parcels_details,
                "route_stop_ids": current_route_stop_ids,
                "total_weight": current_route_total_weight,
                "capacity_weight": agent_details["capacity_weight"],
                "total_distance": round(route_dist, 2),
            })
    else: # No solution found (e.g., if population size was 0 or generations 0 and no init pop)
          # Create empty routes for all agents if no solution was found but agents exist
        for agent_details in delivery_agents_copy:
            optimised_routes_output.append({
                "agent_id": agent_details["id"],
                "parcels_assigned_ids": [],
                "parcels_assigned_details": [],
                "route_stop_ids": ["Warehouse", "Warehouse"] if return_to_warehouse else ["Warehouse"],
                "total_weight": 0,
                "capacity_weight": agent_details["capacity_weight"],
                "total_distance": 0.0,
            })


    # Determine unassigned parcels based on the best solution
    unassigned_parcels_ids_final = []
    unassigned_parcels_details_final = []
    if parcels_copy: # Only if there were parcels to begin with
        all_initial_parcel_ids = {p["id"] for p in parcels_copy}
        parcels_actually_unassigned_ids = list(all_initial_parcel_ids - all_assigned_parcel_ids_in_best_solution)
        
        if parcels_actually_unassigned_ids: # If there are genuinely unassigned parcels
            unassigned_parcels_ids_final = parcels_actually_unassigned_ids
            unassigned_parcels_details_final = [p for p in parcels_copy if p["id"] in unassigned_parcels_ids_final]
            # This indicates the GA might not have found a perfect solution or capacities are too restrictive.
            # The fitness function already heavily penalizes this.

    message = "Genetic Algorithm optimisation completed."
    if unassigned_parcels_ids_final and parcels_copy: # If there were parcels and some are unassigned
        message += f" Warning: {len(unassigned_parcels_ids_final)} parcel(s) could not be assigned."
    elif not parcels_copy:
        message = "Genetic Algorithm optimisation completed. No parcels to assign."
    elif not best_solution_overall and parcels_copy:
         message = "Genetic Algorithm optimisation failed to find a valid solution for assigning parcels."


    return {
        "status": "success" if not (unassigned_parcels_ids_final and parcels_copy) else "warning", # or "error" if unassigned is critical
        "message": message,
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": unassigned_parcels_ids_final,
        "unassigned_parcels_details": unassigned_parcels_details_final
    }

