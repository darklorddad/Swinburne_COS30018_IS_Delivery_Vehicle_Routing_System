# DVRS Optimisation Script: Greedy Nearest Neighbor
import math

def get_params_schema():
    # Defines the parameters accepted by this script.
    # This basic greedy optimiser does not require any configurable parameters.
    # The schema can be expanded if parameters are needed in the future.
    return {
        "parameters": [] # No parameters for this version
    }

def _calculate_distance(coord1, coord2):
    # Calculates Euclidean distance between two points.
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def run_optimisation(config_data, params):
    # Main optimisation function.
    # Implements a greedy nearest-neighbour approach to assign parcels to delivery agents
    # based on proximity and capacity.
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    # Create a mutable list of parcels, including their original data
    unassigned_parcels = [dict(p) for p in config_data.get("parcels", [])]
    delivery_agents = config_data.get("delivery_agents", [])

    optimised_routes = []
    parcels_assigned_globally = set()

    for agent in delivery_agents:
        current_capacity = agent["capacity_weight"]
        current_location = list(warehouse_coords) # Use a mutable copy
        agent_route_parcels = [] # List of parcel objects for this agent
        agent_route_stops_coords = [list(warehouse_coords)] # List of coordinates for distance calculation
        agent_route_stop_ids = ["Warehouse"] # List of IDs for display

        while True:
            best_parcel_candidate = None
            best_parcel_idx = -1
            min_dist_candidate = float('inf')

            # Find the nearest, eligible, unassigned parcel
            for i, parcel_data in enumerate(unassigned_parcels):
                if parcel_data["weight"] <= current_capacity:
                    dist = _calculate_distance(current_location, parcel_data["coordinates_x_y"])
                    if dist < min_dist_candidate:
                        min_dist_candidate = dist
                        best_parcel_candidate = parcel_data
                        best_parcel_idx = i
            
            if best_parcel_candidate:
                # Assign the best found parcel
                assigned_parcel = unassigned_parcels.pop(best_parcel_idx) # Remove from unassigned
                parcels_assigned_globally.add(assigned_parcel["id"])

                agent_route_parcels.append(assigned_parcel)
                agent_route_stops_coords.append(list(assigned_parcel["coordinates_x_y"]))
                agent_route_stop_ids.append(assigned_parcel["id"])
                
                current_capacity -= assigned_parcel["weight"]
                current_location = list(assigned_parcel["coordinates_x_y"])
            else:
                # No more parcels can be assigned to this agent
                break
        
        # Return to warehouse
        agent_route_stops_coords.append(list(warehouse_coords))
        agent_route_stop_ids.append("Warehouse")

        # Calculate total distance for the agent's route
        total_distance = 0
        for i in range(len(agent_route_stops_coords) - 1):
            total_distance += _calculate_distance(agent_route_stops_coords[i], agent_route_stops_coords[i+1])

        if agent_route_parcels: # Only add route if parcels were assigned
            optimised_routes.append({
                "agent_id": agent["id"],
                "parcels_assigned_ids": [p["id"] for p in agent_route_parcels],
                "parcels_assigned_details": agent_route_parcels, # Full details
                "route_stop_ids": agent_route_stop_ids,
                "total_weight": sum(p["weight"] for p in agent_route_parcels),
                "capacity_weight": agent["capacity_weight"],
                "total_distance": round(total_distance, 2),
            })

    # Remaining unassigned parcels (those not in parcels_assigned_globally)
    final_unassigned_parcels = [p for p in config_data.get("parcels", []) if p["id"] not in parcels_assigned_globally]

    return {
        "status": "success",
        "message": "Greedy optimisation completed.",
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in final_unassigned_parcels],
        "unassigned_parcels_details": final_unassigned_parcels
    }
