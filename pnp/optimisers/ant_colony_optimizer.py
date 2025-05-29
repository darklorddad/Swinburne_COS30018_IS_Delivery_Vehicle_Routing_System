# DVRS Optimisation Script: Ant Colony Optimization (ACO)
import math
import random
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "num_ants",
                "label": "Number of Ants",
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 100,
                "step": 5,
                "help": "Number of ants in the colony"
            },
            {
                "name": "iterations",
                "label": "Number of Iterations",
                "type": "integer",
                "default": 50,
                "min": 10,
                "max": 200,
                "step": 10,
                "help": "Number of iterations to run the algorithm"
            },
            {
                "name": "alpha",
                "label": "Pheromone Importance (α)",
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "help": "Importance of pheromone trails"
            },
            {
                "name": "beta",
                "label": "Distance Importance (β)",
                "type": "float", 
                "default": 2.0,
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "help": "Importance of distance (heuristic information)"
            },
            {
                "name": "evaporation_rate",
                "label": "Evaporation Rate",
                "type": "float",
                "default": 0.1,
                "min": 0.01,
                "max": 0.5,
                "step": 0.01,
                "help": "Rate at which pheromones evaporate"
            },
            {
                "name": "q0",
                "label": "Exploitation vs Exploration",
                "type": "float",
                "default": 0.8,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "help": "Probability of choosing best option (vs random selection)"
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

def _initialize_pheromones(num_parcels):
    """Initialize pheromone matrix."""
    # Include warehouse (index 0) + all parcels
    size = num_parcels + 1
    initial_pheromone = 1.0
    return [[initial_pheromone for _ in range(size)] for _ in range(size)]

def _calculate_distances_matrix(warehouse_coords, parcels):
    """Calculate distance matrix between all locations."""
    all_coords = [warehouse_coords] + [p["coordinates_x_y"] for p in parcels]
    size = len(all_coords)
    distances = [[0.0 for _ in range(size)] for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            if i != j:
                distances[i][j] = _calculate_distance(all_coords[i], all_coords[j])
    
    return distances

def _select_next_parcel(current_idx, available_parcels, pheromones, distances, alpha, beta, q0):
    """Select next parcel using ACO probability rules."""
    if not available_parcels:
        return None
    
    # Calculate probabilities for each available parcel
    probabilities = []
    total_attractiveness = 0
    
    for parcel_idx in available_parcels:
        # Pheromone factor
        pheromone = pheromones[current_idx][parcel_idx] ** alpha
        
        # Heuristic factor (inverse of distance)
        if distances[current_idx][parcel_idx] > 0:
            heuristic = (1.0 / distances[current_idx][parcel_idx]) ** beta
        else:
            heuristic = 1.0
        
        attractiveness = pheromone * heuristic
        probabilities.append(attractiveness)
        total_attractiveness += attractiveness
    
    if total_attractiveness == 0:
        # If all attractiveness is 0, choose randomly
        return random.choice(available_parcels)
    
    # Normalize probabilities
    probabilities = [p / total_attractiveness for p in probabilities]
    
    # Exploitation vs exploration
    if random.random() < q0:
        # Exploitation: choose best option
        best_idx = probabilities.index(max(probabilities))
        return available_parcels[best_idx]
    else:
        # Exploration: choose based on probability distribution
        r = random.random()
        cumulative_prob = 0
        for i, prob in enumerate(probabilities):
            cumulative_prob += prob
            if r <= cumulative_prob:
                return available_parcels[i]
        
        # Fallback (shouldn't reach here)
        return available_parcels[-1]

def _construct_solution(parcels, delivery_agents, pheromones, distances, alpha, beta, q0, warehouse_coords, return_to_warehouse):
    """Construct a solution using ACO rules."""
    routes = []
    all_available_parcels = set(range(1, len(parcels) + 1))  # Parcel indices (1-based, 0 is warehouse)
    
    for agent in delivery_agents:
        if not all_available_parcels:
            routes.append([])
            continue
        
        route = []
        current_weight = 0
        current_idx = 0  # Start at warehouse
        available_parcels = all_available_parcels.copy()
        agent_capacity = agent["capacity_weight"]
        
        while available_parcels:
            # Filter parcels that fit in remaining capacity
            feasible_parcels = []
            for parcel_idx in available_parcels:
                parcel = parcels[parcel_idx - 1]  # Convert to 0-based index
                if current_weight + parcel["weight"] <= agent_capacity:
                    feasible_parcels.append(parcel_idx)
            
            if not feasible_parcels:
                break
            
            # Select next parcel using ACO rules
            next_parcel_idx = _select_next_parcel(current_idx, feasible_parcels, pheromones, distances, alpha, beta, q0)
            
            if next_parcel_idx is None:
                break
            
            # Add parcel to route
            parcel = parcels[next_parcel_idx - 1]  # Convert to 0-based index
            route.append(parcel)
            current_weight += parcel["weight"]
            current_idx = next_parcel_idx
            
            # Remove from available parcels
            available_parcels.remove(next_parcel_idx)
            all_available_parcels.remove(next_parcel_idx)
        
        routes.append(route)
    
    return routes

def _update_pheromones(pheromones, all_routes, evaporation_rate, warehouse_coords, return_to_warehouse):
    """Update pheromone trails based on solution quality."""
    # Evaporation
    for i in range(len(pheromones)):
        for j in range(len(pheromones[i])):
            pheromones[i][j] *= (1 - evaporation_rate)
    
    # Pheromone deposit
    for routes_solution in all_routes:
        total_distance = 0
        route_segments = []
        
        for route in routes_solution:
            if not route:
                continue
            
            # Calculate route distance and collect segments
            route_distance = _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
            total_distance += route_distance
            
            # Add segments for pheromone update
            current_idx = 0  # Start at warehouse
            for parcel in route:
                parcel_idx = next(i for i, p in enumerate(parcels_global) if p["id"] == parcel["id"]) + 1
                route_segments.append((current_idx, parcel_idx))
                current_idx = parcel_idx
            
            if return_to_warehouse and route:
                route_segments.append((current_idx, 0))  # Return to warehouse
        
        # Deposit pheromones (inversely proportional to total distance)
        if total_distance > 0:
            pheromone_deposit = 1.0 / total_distance
            for i, j in route_segments:
                pheromones[i][j] += pheromone_deposit
                pheromones[j][i] += pheromone_deposit  # Symmetric

def run_optimisation(config_data, params):
    global parcels_global  # Global reference for pheromone update function
    
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract parameters
    num_ants = params.get("num_ants", 20)
    iterations = params.get("iterations", 50)
    alpha = params.get("alpha", 1.0)
    beta = params.get("beta", 2.0)
    evaporation_rate = params.get("evaporation_rate", 0.1)
    q0 = params.get("q0", 0.8)
    return_to_warehouse = params.get("return_to_warehouse", True)
    
    # Handle empty data
    if not parcels or not delivery_agents:
        return {
            "status": "warning",
            "message": "No parcels or delivery agents found in configuration.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels],
            "unassigned_parcels_details": parcels
        }
    
    # Create deep copies
    parcels_copy = copy.deepcopy(parcels)
    delivery_agents_copy = copy.deepcopy(delivery_agents)
    parcels_global = parcels_copy  # For pheromone update function
    
    # Initialize ACO components
    pheromones = _initialize_pheromones(len(parcels_copy))
    distances = _calculate_distances_matrix(warehouse_coords, parcels_copy)
    
    best_solution = None
    best_distance = float('inf')
    
    # Main ACO loop
    for iteration in range(iterations):
        iteration_solutions = []
        
        # Generate solutions with ants
        for ant in range(num_ants):
            solution = _construct_solution(parcels_copy, delivery_agents_copy, pheromones, distances, 
                                        alpha, beta, q0, warehouse_coords, return_to_warehouse)
            iteration_solutions.append(solution)
            
            # Calculate total distance for this solution
            total_distance = sum(_calculate_route_distance(route, warehouse_coords, return_to_warehouse) 
                               for route in solution)
            
            # Update best solution
            if total_distance < best_distance:
                best_distance = total_distance
                best_solution = copy.deepcopy(solution)
        
        # Update pheromones
        _update_pheromones(pheromones, iteration_solutions, evaporation_rate, warehouse_coords, return_to_warehouse)
    
    # Prepare results
    if best_solution is None:
        # Fallback: create empty routes
        best_solution = [[] for _ in delivery_agents_copy]
    
    optimised_routes = []
    assigned_parcel_ids = set()
    
    for agent_idx, route in enumerate(best_solution):
        if not route:
            continue
        
        agent = delivery_agents_copy[agent_idx]
        route_stop_ids = ["Warehouse"]
        
        for parcel in route:
            route_stop_ids.append(parcel["id"])
            assigned_parcel_ids.add(parcel["id"])
        
        if return_to_warehouse:
            route_stop_ids.append("Warehouse")
        
        route_distance = _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
        
        optimised_routes.append({
            "agent_id": agent["id"],
            "parcels_assigned_ids": [p["id"] for p in route],
            "parcels_assigned_details": route,
            "route_stop_ids": route_stop_ids,
            "route_stop_coordinates": [warehouse_coords] + [p["coordinates_x_y"] for p in route] + ([warehouse_coords] if return_to_warehouse else []),
            "total_weight": sum(p["weight"] for p in route),
            "capacity_weight": agent["capacity_weight"],
            "total_distance": round(route_distance, 2),
        })
    
    # Identify unassigned parcels
    unassigned_parcels = [p for p in parcels if p["id"] not in assigned_parcel_ids]
    
    status = "success" if not unassigned_parcels else "warning"
    message = "Ant Colony Optimization completed."
    if unassigned_parcels:
        message += f" {len(unassigned_parcels)} parcel(s) could not be assigned due to capacity constraints."
    
    return {
        "status": status,
        "message": message,
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned_parcels],
        "unassigned_parcels_details": unassigned_parcels
    }
