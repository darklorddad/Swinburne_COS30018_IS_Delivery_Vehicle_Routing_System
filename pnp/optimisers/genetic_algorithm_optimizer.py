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
    
    # Distance from warehouse to first stop
    total_distance = _calculate_distance(warehouse_coords, route[0]["coordinates_x_y"])
    
    # Distance between consecutive stops
    for i in range(len(route) - 1):
        total_distance += _calculate_distance(route[i]["coordinates_x_y"], route[i+1]["coordinates_x_y"])
    
    # Distance from last stop back to warehouse if required
    if return_to_warehouse and route:
        total_distance += _calculate_distance(route[-1]["coordinates_x_y"], warehouse_coords)
    
    return total_distance

def _calculate_solution_fitness(solution, delivery_agents, warehouse_coords, return_to_warehouse):
    """Calculate fitness (inverse of total distance) for a solution."""
    total_distance = 0.0
    
    # Check capacity constraints
    for route_idx, route in enumerate(solution):
        if route and sum(parcel["weight"] for parcel in route) > delivery_agents[route_idx]["capacity_weight"]:
            # Penalize invalid solutions with a high distance
            return 0.0001  # Very low fitness for invalid solutions
        
        total_distance += _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
    
    # Add penalty for unassigned parcels
    return 1.0 / (total_distance + 0.1)  # Add small constant to avoid division by zero

def _generate_random_solution(parcels, delivery_agents):
    """Generate a random initial solution."""
    solution = [[] for _ in delivery_agents]
    
    # Create a list of parcel indices to assign
    parcel_indices = list(range(len(parcels)))
    random.shuffle(parcel_indices)
    
    # Try to assign each parcel to a random agent
    for parcel_idx in parcel_indices:
        parcel = parcels[parcel_idx]
        
        # Create a list of agents in random order
        agent_indices = list(range(len(delivery_agents)))
        random.shuffle(agent_indices)
        
        assigned = False
        for agent_idx in agent_indices:
            # Calculate current route weight
            current_weight = sum(p["weight"] for p in solution[agent_idx])
            
            # Check if parcel fits in this agent's capacity
            if current_weight + parcel["weight"] <= delivery_agents[agent_idx]["capacity_weight"]:
                solution[agent_idx].append(parcel)
                assigned = True
                break
    
    return solution

def _initialize_population(population_size, parcels, delivery_agents):
    """Initialize the population with random solutions."""
    return [_generate_random_solution(parcels, delivery_agents) for _ in range(population_size)]

def _select_parent(population, fitnesses):
    """Select parent using tournament selection."""
    tournament_size = 3
    tournament_indices = random.sample(range(len(population)), tournament_size)
    tournament_fitnesses = [fitnesses[i] for i in tournament_indices]
    winner_idx = tournament_indices[tournament_fitnesses.index(max(tournament_fitnesses))]
    return population[winner_idx]

def _crossover(parent1, parent2, delivery_agents):
    """Perform crossover between two parents to create a child."""
    if len(parent1) != len(parent2):
        raise ValueError("Parents must have the same number of routes")
    
    child = [[] for _ in range(len(parent1))]
    
    # Set to keep track of assigned parcels
    assigned_parcels = set()
    
    # First inherit routes using uniform crossover
    for route_idx in range(len(parent1)):
        # Decide which parent to inherit from for this route
        if random.random() < 0.5:
            selected_parent = parent1
        else:
            selected_parent = parent2
        
        # Try to inherit the route
        for parcel in selected_parent[route_idx]:
            parcel_id = parcel["id"]
            
            if parcel_id not in assigned_parcels:
                # Check capacity
                current_weight = sum(p["weight"] for p in child[route_idx])
                if current_weight + parcel["weight"] <= delivery_agents[route_idx]["capacity_weight"]:
                    child[route_idx].append(parcel)
                    assigned_parcels.add(parcel_id)
    
    return child

def _mutate(solution, parcels, delivery_agents, mutation_rate):
    """Apply mutation to a solution."""
    mutated = copy.deepcopy(solution)
    
    # With some probability, apply one of several mutation operators
    if random.random() < mutation_rate:
        mutation_type = random.choice(["swap", "relocate", "shuffle"])
        
        if mutation_type == "swap" and len(mutated) >= 2:
            # Swap parcels between two routes
            route1_idx = random.randint(0, len(mutated) - 1)
            route2_idx = random.randint(0, len(mutated) - 1)
            
            if mutated[route1_idx] and mutated[route2_idx]:
                parcel1_idx = random.randint(0, len(mutated[route1_idx]) - 1)
                parcel2_idx = random.randint(0, len(mutated[route2_idx]) - 1)
                
                parcel1 = mutated[route1_idx][parcel1_idx]
                parcel2 = mutated[route2_idx][parcel2_idx]
                
                # Check capacity constraints
                weight_route1 = sum(p["weight"] for p in mutated[route1_idx])
                weight_route2 = sum(p["weight"] for p in mutated[route2_idx])
                
                if (weight_route1 - parcel1["weight"] + parcel2["weight"] <= delivery_agents[route1_idx]["capacity_weight"] and
                    weight_route2 - parcel2["weight"] + parcel1["weight"] <= delivery_agents[route2_idx]["capacity_weight"]):
                    
                    mutated[route1_idx][parcel1_idx] = parcel2
                    mutated[route2_idx][parcel2_idx] = parcel1
        
        elif mutation_type == "relocate":
            # Move a parcel from one route to another
            if len(mutated) >= 2:
                source_idx = random.randint(0, len(mutated) - 1)
                
                if mutated[source_idx]:
                    parcel_idx = random.randint(0, len(mutated[source_idx]) - 1)
                    parcel = mutated[source_idx][parcel_idx]
                    
                    # Find a route with enough capacity
                    possible_routes = []
                    for i in range(len(mutated)):
                        if i != source_idx:
                            current_weight = sum(p["weight"] for p in mutated[i])
                            if current_weight + parcel["weight"] <= delivery_agents[i]["capacity_weight"]:
                                possible_routes.append(i)
                    
                    if possible_routes:
                        target_idx = random.choice(possible_routes)
                        target_pos = random.randint(0, len(mutated[target_idx]))
                        
                        # Relocate the parcel
                        mutated[source_idx].pop(parcel_idx)
                        mutated[target_idx].insert(target_pos, parcel)
        
        elif mutation_type == "shuffle":
            # Shuffle a route
            if mutated:
                route_idx = random.randint(0, len(mutated) - 1)
                
                if len(mutated[route_idx]) > 2:
                    random.shuffle(mutated[route_idx])
    
    return mutated

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract genetic algorithm parameters
    population_size = params.get("population_size", 50)
    generations = params.get("generations", 100)
    crossover_rate = params.get("crossover_rate", 0.8)
    mutation_rate = params.get("mutation_rate", 0.2)
    elitism_count = params.get("elitism_count", 5)
    return_to_warehouse = params.get("return_to_warehouse", True)
    
    # Create deep copies to avoid modifying original data
    parcels_copy = copy.deepcopy(parcels)
    delivery_agents_copy = copy.deepcopy(delivery_agents)
    
    # Initialize population
    population = _initialize_population(population_size, parcels_copy, delivery_agents_copy)
    
    best_solution = None
    best_fitness = 0.0
    
    # Evolution process
    for generation in range(generations):
        # Calculate fitness for all solutions
        fitnesses = [_calculate_solution_fitness(solution, delivery_agents_copy, warehouse_coords, return_to_warehouse) 
                    for solution in population]
        
        # Find the best solution in this generation
        gen_best_idx = fitnesses.index(max(fitnesses))
        gen_best_solution = population[gen_best_idx]
        gen_best_fitness = fitnesses[gen_best_idx]
        
        # Update overall best solution if needed
        if gen_best_fitness > best_fitness:
            best_solution = copy.deepcopy(gen_best_solution)
            best_fitness = gen_best_fitness
        
        # Create next generation
        next_population = []
        
        # Elitism: Keep the best solutions unchanged
        sorted_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)
        for i in range(min(elitism_count, len(population))):
            next_population.append(copy.deepcopy(population[sorted_indices[i]]))
        
        # Generate the rest of the population through crossover and mutation
        while len(next_population) < population_size:
            # Select parents
            parent1 = _select_parent(population, fitnesses)
            parent2 = _select_parent(population, fitnesses)
            
            # Crossover with some probability
            if random.random() < crossover_rate:
                child = _crossover(parent1, parent2, delivery_agents_copy)
            else:
                child = copy.deepcopy(parent1)
            
            # Mutation
            child = _mutate(child, parcels_copy, delivery_agents_copy, mutation_rate)
            
            next_population.append(child)
        
        # Update population
        population = next_population
    
    # Prepare results using the best solution found
    optimised_routes = []
    assigned_parcels_ids = set()
    
    for agent_idx, route in enumerate(best_solution):
        agent = delivery_agents[agent_idx]
        route_stop_ids = ["Warehouse"]
        
        for parcel in route:
            route_stop_ids.append(parcel["id"])
            assigned_parcels_ids.add(parcel["id"])
        
        if return_to_warehouse:
            route_stop_ids.append("Warehouse")
        
        if route:  # Only include routes with assigned parcels
            route_distance = _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
            optimised_routes.append({
                "agent_id": agent["id"],
                "parcels_assigned_ids": [p["id"] for p in route],
                "parcels_assigned_details": route,
                "route_stop_ids": route_stop_ids,
                "total_weight": sum(p["weight"] for p in route),
                "capacity_weight": agent["capacity_weight"],
                "total_distance": round(route_distance, 2),
            })
    
    # Get unassigned parcels
    unassigned_parcels_ids = [p["id"] for p in parcels if p["id"] not in assigned_parcels_ids]
    unassigned_parcels_details = [p for p in parcels if p["id"] not in assigned_parcels_ids]
    
    return {
        "status": "success",
        "message": "Genetic Algorithm optimisation completed.",
        "optimised_routes": optimised_routes,
        "unassigned_parcels": unassigned_parcels_ids,
        "unassigned_parcels_details": unassigned_parcels_details
    }
