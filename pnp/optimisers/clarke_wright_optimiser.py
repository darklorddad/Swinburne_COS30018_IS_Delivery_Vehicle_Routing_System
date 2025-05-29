# DVRS Optimisation Script: Clarke-Wright Savings Algorithm
import math
from operator import itemgetter

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "route_strategy",
                "label": "Route Building Strategy",
                "type": "selectbox",
                "default": "parallel",
                "options": ["parallel", "sequential"],
                "help": "Parallel builds all routes simultaneously, Sequential builds one route at a time"
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries"
            },
            {
                "name": "savings_lambda",
                "label": "Route Shape Parameter",
                "type": "float",
                "default": 1.0,
                "min": 0.5,
                "max": 2.0,
                "step": 0.1,
                "help": "Controls route shape: lower values favor more radial routes, higher values favor routes that extend outward"
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_savings(i, j, distances, warehouse_idx, lambda_param=1.0):
    """Calculate savings for merging routes between points i and j.
    
    The savings formula represents how much distance is saved by visiting i and j 
    consecutively in one route, rather than in separate routes:
    savings = d(i,depot) + d(depot,j) - lambda * d(i,j)
    
    Lambda is a shape parameter that can be tuned:
    - lambda = 1.0 is the classic Clarke-Wright algorithm
    - lambda < 1.0 favors merging nodes that are close to each other (more radial routes)
    - lambda > 1.0 favors merging nodes that are far from the depot (more elongated routes)
    """
    return (distances[i][warehouse_idx] + distances[warehouse_idx][j] 
            - lambda_param * distances[i][j])

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Strategy and parameters
    route_strategy = params.get("route_strategy", "parallel")
    return_to_warehouse = params.get("return_to_warehouse", True)
    lambda_param = params.get("savings_lambda", 1.0)
    
    # Handle empty data gracefully
    if not parcels or not delivery_agents:
        return {
            "status": "warning",
            "message": "No parcels or delivery agents found in configuration.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels],
            "unassigned_parcels_details": parcels
        }
    
    # Create a list of all stops (warehouse + all parcels)
    all_stops = [warehouse_coords] + [p["coordinates_x_y"] for p in parcels]
    warehouse_idx = 0  # Index of warehouse in all_stops
    
    # Calculate distance matrix
    n_stops = len(all_stops)
    distances = [[0 for _ in range(n_stops)] for _ in range(n_stops)]
    for i in range(n_stops):
        for j in range(i, n_stops):
            if i == j:
                distances[i][j] = 0
            else:
                dist = _calculate_distance(all_stops[i], all_stops[j])
                distances[i][j] = dist
                distances[j][i] = dist  # Distance matrix is symmetric
    
    # Calculate savings for all pairs of parcels
    savings_list = []
    for i in range(1, n_stops):  # Start from 1 to skip warehouse
        for j in range(i+1, n_stops):
            saving = _calculate_savings(i, j, distances, warehouse_idx, lambda_param)
            savings_list.append((i, j, saving))
    
    # Sort savings in descending order
    savings_list.sort(key=itemgetter(2), reverse=True)
    
    # Create initial routes: each parcel in its own route
    # Routes are represented as lists of indices into all_stops
    # We include warehouse at the start (and end if return_to_warehouse is True)
    routes = []
    for i in range(1, n_stops):
        route = [warehouse_idx, i]
        if return_to_warehouse:
            route.append(warehouse_idx)
        routes.append(route)
    
    # Track which route each stop belongs to
    stop_to_route = {}
    for route_idx, route in enumerate(routes):
        for stop_idx in route:
            if stop_idx != warehouse_idx:  # Don't track warehouse
                stop_to_route[stop_idx] = route_idx
    
    # For each agent, we'll track remaining capacity
    agent_capacities = [agent["capacity_weight"] for agent in delivery_agents]
    route_to_agent = {}  # Maps route_idx to agent_idx
    
    if route_strategy == "parallel":
        # Parallel route building - merge routes based on savings
        for i, j, saving in savings_list:
            if i not in stop_to_route or j not in stop_to_route:
                continue  # Skip if already merged into another route
                
            route_i = stop_to_route[i]
            route_j = stop_to_route[j]
            
            if route_i == route_j:
                continue  # Already in the same route
            
            # Check if routes can be merged
            # Two routes can be merged if:
            # 1. i is at the end of its route (just before warehouse if return_to_warehouse)
            # 2. j is at the start of its route (just after warehouse)
            # 3. The resulting route can be assigned to an agent with sufficient capacity
            
            # Find positions of i and j in their routes
            route_i_list = routes[route_i]
            route_j_list = routes[route_j]
            
            # Check positions - we need i at the end and j at the beginning of their routes
            if return_to_warehouse:
                pos_i = route_i_list[-2]  # Second-to-last position (before warehouse)
                pos_j = route_j_list[1]   # Second position (after warehouse)
            else:
                pos_i = route_i_list[-1]  # Last position
                pos_j = route_j_list[1]   # Second position (after warehouse)
            
            if pos_i != i or pos_j != j:
                continue  # Not in the correct positions for merging
            
            # Check capacity constraints
            # Calculate total weight of combined route
            route_i_weight = sum(parcels[idx-1]["weight"] for idx in route_i_list if idx != warehouse_idx)
            route_j_weight = sum(parcels[idx-1]["weight"] for idx in route_j_list if idx != warehouse_idx)
            total_weight = route_i_weight + route_j_weight
            
            # Find an agent that can handle this weight
            agent_idx = -1
            for idx, capacity in enumerate(agent_capacities):
                if capacity >= total_weight and idx not in route_to_agent.values():
                    agent_idx = idx
                    break
            
            if agent_idx == -1:
                continue  # No agent can handle this route
            
            # Merge routes
            if return_to_warehouse:
                merged_route = route_i_list[:-1] + route_j_list[1:]
            else:
                merged_route = route_i_list + route_j_list[1:]
            
            # Update routes
            routes[route_i] = merged_route
            routes[route_j] = []  # Empty route (will be removed later)
            
            # Update stop_to_route mapping
            for stop_idx in merged_route:
                if stop_idx != warehouse_idx:
                    stop_to_route[stop_idx] = route_i
            
            # Assign route to agent
            route_to_agent[route_i] = agent_idx
            agent_capacities[agent_idx] -= total_weight
    
    else:  # Sequential route building
        # Start with empty routes for each agent
        active_routes = [[] for _ in range(len(delivery_agents))]
        route_weights = [0 for _ in range(len(delivery_agents))]
        
        # Process each parcel in order of savings
        for i, j, saving in savings_list:
            # Skip if either parcel is already assigned
            if i not in stop_to_route or j not in stop_to_route:
                continue
                
            # Try to find an agent that can handle both parcels
            for agent_idx, capacity in enumerate(agent_capacities):
                if capacity >= parcels[i-1]["weight"] + parcels[j-1]["weight"]:
                    # Create or extend route for this agent
                    if not active_routes[agent_idx]:
                        # Start new route
                        active_routes[agent_idx] = [warehouse_idx, i, j]
                        if return_to_warehouse:
                            active_routes[agent_idx].append(warehouse_idx)
                        route_weights[agent_idx] += parcels[i-1]["weight"] + parcels[j-1]["weight"]
                    else:
                        # Try to extend existing route
                        current_route = active_routes[agent_idx]
                        if current_route[-1 if not return_to_warehouse else -2] == i:
                            # i is at the end, append j
                            if return_to_warehouse:
                                current_route.insert(-1, j)
                            else:
                                current_route.append(j)
                            route_weights[agent_idx] += parcels[j-1]["weight"]
                        elif current_route[1] == j:
                            # j is at the start, prepend i
                            current_route.insert(1, i)
                            route_weights[agent_idx] += parcels[i-1]["weight"]
                    
                    # Update assignments
                    stop_to_route.pop(i, None)
                    stop_to_route.pop(j, None)
                    agent_capacities[agent_idx] -= parcels[i-1]["weight"] + parcels[j-1]["weight"]
                    break
        
        # Replace routes with active_routes
        routes = active_routes
    
    # Clean up empty routes
    routes = [route for route in routes if route]
    
    # Convert routes from indices to actual data
    optimised_routes = []
    assigned_parcel_ids = set()
    
    for route_idx, route in enumerate(routes):
        if not route:
            continue  # Skip empty routes
            
        # Find an agent for this route if not already assigned
        agent_idx = route_to_agent.get(route_idx)
        if agent_idx is None:
            # Try to find an agent with enough capacity
            route_weight = sum(parcels[idx-1]["weight"] for idx in route if idx != warehouse_idx)
            for idx, capacity in enumerate(agent_capacities):
                if capacity >= route_weight and idx not in route_to_agent.values():
                    agent_idx = idx
                    agent_capacities[idx] -= route_weight
                    break
            
            if agent_idx is None:
                continue  # No agent can handle this route
        
        # Extract parcel details for this route
        route_parcels = []
        for idx in route:
            if idx != warehouse_idx:
                parcel = parcels[idx-1]
                route_parcels.append(parcel)
                assigned_parcel_ids.add(parcel["id"])
        
        # Calculate total distance
        total_distance = 0
        for i in range(len(route) - 1):
            total_distance += distances[route[i]][route[i+1]]
        
        # Create route stop IDs
        route_stop_ids = []
        for idx in route:
            if idx == warehouse_idx:
                route_stop_ids.append("Warehouse")
            else:
                route_stop_ids.append(parcels[idx-1]["id"])
        
        # Add route to results
        optimised_routes.append({
            "agent_id": delivery_agents[agent_idx]["id"],
            "parcels_assigned_ids": [p["id"] for p in route_parcels],
            "parcels_assigned_details": route_parcels,
            "route_stop_ids": route_stop_ids,
            "route_stop_coordinates": [warehouse_coords] + [p["coordinates_x_y"] for p in route_parcels] + ([warehouse_coords] if return_to_warehouse else []),
            "total_weight": sum(p["weight"] for p in route_parcels),
            "capacity_weight": delivery_agents[agent_idx]["capacity_weight"],
            "total_distance": round(total_distance, 2),
        })
    
    # Identify unassigned parcels
    unassigned_parcels = [p for p in parcels if p["id"] not in assigned_parcel_ids]
    
    return {
        "status": "success",
        "message": "Clarke-Wright savings algorithm completed.",
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned_parcels],
        "unassigned_parcels_details": unassigned_parcels
    }
