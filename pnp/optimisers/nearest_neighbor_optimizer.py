# DVRS Optimisation Script: Nearest Neighbor Algorithm
import math
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "start_strategy",
                "label": "Starting Strategy",
                "type": "selectbox",
                "default": "nearest_to_warehouse",
                "options": ["nearest_to_warehouse", "farthest_from_warehouse", "random"],
                "help": "Strategy for selecting the first parcel in each route"
            },
            {
                "name": "use_2opt",
                "label": "Apply 2-opt Improvement",
                "type": "boolean",
                "default": True,
                "help": "Apply 2-opt local search to improve routes"
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries"
            },
            {
                "name": "prioritize_weight",
                "label": "Prioritize Heavy Parcels",
                "type": "boolean",
                "default": False,
                "help": "Consider parcel weight when selecting next destination"
            },
            {
                "name": "weight_factor",
                "label": "Weight Priority Factor",
                "type": "float",
                "default": 0.1,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "help": "How much to prioritize heavy parcels (0=ignore weight, 1=weight only)"
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

def _apply_2opt(route, warehouse_coords, return_to_warehouse):
    """Apply 2-opt improvement to a route."""
    if len(route) < 2:
        return route
    
    improved = True
    best_route = route.copy()
    
    while improved:
        improved = False
        best_distance = _calculate_route_distance(best_route, warehouse_coords, return_to_warehouse)
        
        for i in range(len(best_route)):
            for j in range(i + 2, len(best_route)):
                # Create new route by reversing the segment between i and j
                new_route = best_route.copy()
                new_route[i:j] = reversed(new_route[i:j])
                
                new_distance = _calculate_route_distance(new_route, warehouse_coords, return_to_warehouse)
                
                if new_distance < best_distance:
                    best_route = new_route
                    best_distance = new_distance
                    improved = True
                    break
            
            if improved:
                break
    
    return best_route

def _select_starting_parcel(available_parcels, warehouse_coords, strategy):
    """Select the starting parcel for a route based on strategy."""
    if not available_parcels:
        return None
    
    if strategy == "nearest_to_warehouse":
        return min(available_parcels, 
                  key=lambda p: _calculate_distance(warehouse_coords, p["coordinates_x_y"]))
    elif strategy == "farthest_from_warehouse":
        return max(available_parcels, 
                  key=lambda p: _calculate_distance(warehouse_coords, p["coordinates_x_y"]))
    else:  # random
        import random
        return random.choice(available_parcels)

def _calculate_selection_score(current_pos, candidate_parcel, prioritize_weight, weight_factor):
    """Calculate selection score for next parcel (lower is better)."""
    distance = _calculate_distance(current_pos, candidate_parcel["coordinates_x_y"])
    
    if not prioritize_weight:
        return distance
    
    # Combine distance with weight consideration
    # Heavy parcels get lower scores (higher priority)
    weight_score = 1.0 / (candidate_parcel["weight"] + 0.1)  # Add 0.1 to avoid division by zero
    
    # Weighted combination: lower weight_factor means distance is more important
    return (1 - weight_factor) * distance + weight_factor * weight_score

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract parameters
    start_strategy = params.get("start_strategy", "nearest_to_warehouse")
    use_2opt = params.get("use_2opt", True)
    return_to_warehouse = params.get("return_to_warehouse", True)
    prioritize_weight = params.get("prioritize_weight", False)
    weight_factor = params.get("weight_factor", 0.1)
    
    # Handle empty data
    if not parcels or not delivery_agents:
        return {
            "status": "warning",
            "message": "No parcels or delivery agents found in configuration.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels],
            "unassigned_parcels_details": parcels
        }
    
    # Create deep copies to avoid modifying original data
    parcels_copy = copy.deepcopy(parcels)
    delivery_agents_copy = copy.deepcopy(delivery_agents)
    
    # Initialize solution
    routes = []
    available_parcels = parcels_copy.copy()
    
    # Build routes for each agent
    for agent in delivery_agents_copy:
        if not available_parcels:
            break
        
        current_route = []
        current_weight = 0
        current_position = warehouse_coords
        agent_capacity = agent["capacity_weight"]
        
        # Select starting parcel
        if available_parcels:
            # Filter parcels that can fit in this agent's capacity
            feasible_parcels = [p for p in available_parcels if p["weight"] <= agent_capacity]
            
            if feasible_parcels:
                starting_parcel = _select_starting_parcel(feasible_parcels, warehouse_coords, start_strategy)
                
                if starting_parcel:
                    current_route.append(starting_parcel)
                    current_weight += starting_parcel["weight"]
                    current_position = starting_parcel["coordinates_x_y"]
                    available_parcels.remove(starting_parcel)
        
        # Build route using nearest neighbor
        while available_parcels:
            # Find feasible parcels that fit in remaining capacity
            feasible_parcels = [p for p in available_parcels 
                             if current_weight + p["weight"] <= agent_capacity]
            
            if not feasible_parcels:
                break
            
            # Select next parcel based on selection criteria
            next_parcel = min(feasible_parcels, 
                            key=lambda p: _calculate_selection_score(
                                current_position, p, prioritize_weight, weight_factor))
            
            current_route.append(next_parcel)
            current_weight += next_parcel["weight"]
            current_position = next_parcel["coordinates_x_y"]
            available_parcels.remove(next_parcel)
        
        # Apply 2-opt improvement if requested
        if use_2opt and len(current_route) > 2:
            current_route = _apply_2opt(current_route, warehouse_coords, return_to_warehouse)
        
        routes.append(current_route)
    
    # Prepare results
    optimised_routes = []
    assigned_parcel_ids = set()
    
    for agent_idx, route in enumerate(routes):
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
    message = "Nearest Neighbor algorithm completed."
    if unassigned_parcels:
        message += f" {len(unassigned_parcels)} parcel(s) could not be assigned due to capacity constraints."
    
    return {
        "status": status,
        "message": message,
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned_parcels],
        "unassigned_parcels_details": unassigned_parcels
    }
