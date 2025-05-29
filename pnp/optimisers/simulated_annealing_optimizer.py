# DVRS Optimisation Script: Simulated Annealing
import math
import random
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "initial_temperature",
                "label": "Initial Temperature",
                "type": "float",
                "default": 1000.0,
                "min": 100.0,
                "max": 10000.0,
                "step": 100.0,
                "help": "Starting temperature for annealing process"
            },
            {
                "name": "cooling_rate",
                "label": "Cooling Rate",
                "type": "float",
                "default": 0.95,
                "min": 0.7,
                "max": 0.99,
                "step": 0.01,
                "help": "Rate at which temperature decreases"
            },
            {
                "name": "iterations_per_temp",
                "label": "Iterations Per Temperature",
                "type": "integer",
                "default": 100,
                "min": 10,
                "max": 1000,
                "step": 10,
                "help": "Number of iterations at each temperature"
            },
            {
                "name": "min_temperature",
                "label": "Minimum Temperature",
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "max": 100.0,
                "step": 0.1,
                "help": "Temperature at which annealing stops"
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

def _calculate_total_solution_distance(solution, warehouse_coords, return_to_warehouse):
    """Calculate total distance for all routes in the solution."""
    total_distance = 0.0
    for route in solution:
        total_distance += _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
    return total_distance

def _calculate_route_weight(route):
    """Calculate total weight for a route."""
    return sum(parcel["weight"] for parcel in route)

def _is_valid_solution(solution, capacity_limits):
    """Check if solution is valid (all routes within capacity limits)."""
    if len(solution) != len(capacity_limits):
        return False
    
    for i, route in enumerate(solution):
        if _calculate_route_weight(route) > capacity_limits[i]:
            return False
    
    return True

def _generate_initial_solution(parcels, delivery_agents):
    """Generate a simple initial solution by randomly assigning parcels to agents."""
    solution = [[] for _ in delivery_agents]
    capacity_limits = [agent["capacity_weight"] for agent in delivery_agents]
    remaining_capacity = capacity_limits.copy()
    
    # Shuffle parcels for randomized initial assignment
    shuffled_parcels = parcels.copy()
    random.shuffle(shuffled_parcels)
    
    # Assign parcels to agents while respecting capacity constraints
    for parcel in shuffled_parcels:
        # Find agent with enough capacity
        assigned = False
        for i, capacity in enumerate(remaining_capacity):
            if parcel["weight"] <= capacity:
                solution[i].append(parcel)
                remaining_capacity[i] -= parcel["weight"]
                assigned = False
                break
    
    return solution

def _generate_neighbor(current_solution, delivery_agents):
    """Generate a neighboring solution by applying a random move."""
    neighbor = copy.deepcopy(current_solution)
    
    # Choose a random move type
    move_type = random.choice(["swap", "relocate", "reverse"])
    
    if move_type == "swap" and len(neighbor) >= 2:
        # Swap two parcels between different routes
        route1_idx = random.randint(0, len(neighbor) - 1)
        route2_idx = random.randint(0, len(neighbor) - 1)
        while route2_idx == route1_idx:
            route2_idx = random.randint(0, len(neighbor) - 1)
        
        if neighbor[route1_idx] and neighbor[route2_idx]:
            parcel1_idx = random.randint(0, len(neighbor[route1_idx]) - 1)
            parcel2_idx = random.randint(0, len(neighbor[route2_idx]) - 1)
            
            # Check if swap would violate capacity constraints
            if (delivery_agents[route1_idx]["capacity_weight"] - _calculate_route_weight(neighbor[route1_idx]) + 
                neighbor[route2_idx][parcel2_idx]["weight"] - neighbor[route1_idx][parcel1_idx]["weight"] >= 0 and
                delivery_agents[route2_idx]["capacity_weight"] - _calculate_route_weight(neighbor[route2_idx]) +
                neighbor[route1_idx][parcel1_idx]["weight"] - neighbor[route2_idx][parcel2_idx]["weight"] >= 0):
                
                neighbor[route1_idx][parcel1_idx], neighbor[route2_idx][parcel2_idx] = (
                    neighbor[route2_idx][parcel2_idx], neighbor[route1_idx][parcel1_idx]
                )
    
    elif move_type == "relocate":
        # Move a parcel from one route to another
        if len(neighbor) >= 2:
            route1_idx = random.randint(0, len(neighbor) - 1)
            route2_idx = random.randint(0, len(neighbor) - 1)
            while route2_idx == route1_idx:
                route2_idx = random.randint(0, len(neighbor) - 1)
            
            if neighbor[route1_idx]:
                parcel_idx = random.randint(0, len(neighbor[route1_idx]) - 1)
                parcel = neighbor[route1_idx][parcel_idx]
                
                # Check if relocation would violate capacity constraint
                if delivery_agents[route2_idx]["capacity_weight"] - _calculate_route_weight(neighbor[route2_idx]) >= parcel["weight"]:
                    neighbor[route1_idx].pop(parcel_idx)
                    if not neighbor[route2_idx]:
                        neighbor[route2_idx] = [parcel]
                    else:
                        insert_pos = random.randint(0, len(neighbor[route2_idx]))
                        neighbor[route2_idx].insert(insert_pos, parcel)
    
    elif move_type == "reverse" and neighbor:
        # Reverse a segment of a route
        route_idx = random.randint(0, len(neighbor) - 1)
        if len(neighbor[route_idx]) > 2:
            start_idx = random.randint(0, len(neighbor[route_idx]) - 2)
            end_idx = random.randint(start_idx + 1, len(neighbor[route_idx]) - 1)
            neighbor[route_idx][start_idx:end_idx+1] = reversed(neighbor[route_idx][start_idx:end_idx+1])
    
    return neighbor

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract simulated annealing parameters
    initial_temperature = params.get("initial_temperature", 1000.0)
    cooling_rate = params.get("cooling_rate", 0.95)
    iterations_per_temp = params.get("iterations_per_temp", 100)
    min_temperature = params.get("min_temperature", 1.0)
    return_to_warehouse = params.get("return_to_warehouse", True)
    
    # Create deep copies to avoid modifying original data
    parcels_copy = copy.deepcopy(parcels)
    delivery_agents_copy = copy.deepcopy(delivery_agents)
    
    # Generate initial solution
    current_solution = _generate_initial_solution(parcels_copy, delivery_agents_copy)
    current_distance = _calculate_total_solution_distance(current_solution, warehouse_coords, return_to_warehouse)
    
    best_solution = copy.deepcopy(current_solution)
    best_distance = current_distance
    
    # Simulated annealing process
    temperature = initial_temperature
    while temperature > min_temperature:
        for _ in range(iterations_per_temp):
            # Generate neighbor solution
            neighbor_solution = _generate_neighbor(current_solution, delivery_agents_copy)
            
            # Calculate distance of neighbor
            neighbor_distance = _calculate_total_solution_distance(neighbor_solution, warehouse_coords, return_to_warehouse)
            
            # Decide whether to accept the neighbor
            if neighbor_distance < current_distance:
                # Always accept better solutions
                current_solution = neighbor_solution
                current_distance = neighbor_distance
                
                # Update best solution if needed
                if current_distance < best_distance:
                    best_solution = copy.deepcopy(current_solution)
                    best_distance = current_distance
            else:
                # Accept worse solutions with a probability based on temperature
                delta = neighbor_distance - current_distance
                acceptance_probability = math.exp(-delta / temperature)
                
                if random.random() < acceptance_probability:
                    current_solution = neighbor_solution
                    current_distance = neighbor_distance
        
        # Cool down
        temperature *= cooling_rate
    
    # Prepare results
    optimised_routes = []
    unassigned_parcels_ids = set(p["id"] for p in parcels)
    
    for agent_idx, route in enumerate(best_solution):
        agent = delivery_agents[agent_idx]
        route_stop_ids = ["Warehouse"]
        
        for parcel in route:
            route_stop_ids.append(parcel["id"])
            unassigned_parcels_ids.discard(parcel["id"])
        
        if return_to_warehouse:
            route_stop_ids.append("Warehouse")
        
        if route:  # Only include routes with assigned parcels
            route_distance = _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
            optimised_routes.append({
                "agent_id": agent["id"],
                "parcels_assigned_ids": [p["id"] for p in route],
                "parcels_assigned_details": route,
                "route_stop_ids": route_stop_ids,
                "route_stop_coordinates": [warehouse_coords] + [p["coordinates_x_y"] for p in route] + ([warehouse_coords] if return_to_warehouse else []),
                "total_weight": _calculate_route_weight(route),
                "capacity_weight": agent["capacity_weight"],
                "total_distance": round(route_distance, 2),
            })
    
    # Get unassigned parcels details
    unassigned_parcels_details = [p for p in parcels if p["id"] in unassigned_parcels_ids]
    
    return {
        "status": "success",
        "message": "Simulated Annealing optimisation completed.",
        "optimised_routes": optimised_routes,
        "unassigned_parcels": list(unassigned_parcels_ids),
        "unassigned_parcels_details": unassigned_parcels_details
    }
