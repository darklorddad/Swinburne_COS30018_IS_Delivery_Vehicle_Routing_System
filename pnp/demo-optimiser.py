# DVRS Optimisation Script: Greedy Nearest Neighbour
import math

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "sort_parcels",
                "label": "Sort parcels by",
                "type": "selectbox",
                "default": "none",
                "options": ["none", "weight_asc", "weight_desc"],
                "help": "Initial sorting of parcels before assignment"
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries"
            },
            {
                "name": "time_per_distance_unit",
                "label": "Time per distance unit (minutes)",
                "type": "float",
                "default": 2.0,
                "min": 0.1,
                "max": 10.0,
                "step": 0.1,
                "help": "Minutes taken to travel one unit of distance"
            },
            {
                "name": "default_service_time",
                "label": "Default service time at stop (minutes)", 
                "type": "integer",
                "default": 10,
                "min": 0,
                "step": 1,
                "help": "Default time spent at each parcel stop for service"
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    # Calculates Euclidean distance between two points.
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    unassigned_parcels = [dict(p) for p in config_data.get("parcels", [])]
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Apply sorting if specified in parameters
    if params.get("sort_parcels", "none") != "none":
        reverse_sort = params["sort_parcels"] == "weight_desc"
        unassigned_parcels.sort(key=lambda x: x["weight"], reverse=reverse_sort)

    optimised_routes = []
    parcels_assigned_globally = set()
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)
    return_to_warehouse_flag = params.get("return_to_warehouse", True)
    sort_parcels_option = params.get("sort_parcels", "none")

    for agent in delivery_agents:
        current_capacity = agent["capacity_weight"]
        current_location = list(warehouse_coords)
        agent_route_parcels = []
        agent_route_stops_coords = [list(warehouse_coords)]
        agent_route_stop_ids = ["Warehouse"]
        agent_op_start_time = agent.get("operating_hours_start", 0)
        agent_op_end_time = agent.get("operating_hours_end", 1439)
        current_time = agent_op_start_time
        agent_arrival_times = [current_time]
        agent_departure_times = [current_time]

        while True:
            best_parcel_candidate = None
            best_parcel_idx = -1
            min_dist_candidate = float('inf')

            # Find the nearest, eligible, unassigned parcel
            for i, parcel_data in enumerate(unassigned_parcels):
                if parcel_data["weight"] <= current_capacity:
                    parcel_coords = parcel_data["coordinates_x_y"]
                    dist_to_parcel = _calculate_distance(current_location, parcel_coords)
                    travel_time = dist_to_parcel * time_per_dist_unit

                    arrival_at_parcel = current_time + travel_time
                    parcel_tw_open = parcel_data.get("time_window_open", 0)
                    parcel_tw_close = parcel_data.get("time_window_close", 1439)
                    parcel_service_time = parcel_data.get("service_time", default_service_time)

                    service_start_time = max(arrival_at_parcel, parcel_tw_open)
                    service_end_time = service_start_time + parcel_service_time

                    feasible = True
                    if service_end_time > parcel_tw_close:
                        feasible = False
                    if service_end_time > agent_op_end_time:
                        feasible = False
                    
                    if return_to_warehouse_flag:
                        dist_from_parcel_to_wh = _calculate_distance(parcel_coords, warehouse_coords)
                        travel_time_to_wh = dist_from_parcel_to_wh * time_per_dist_unit
                        arrival_at_wh_after_parcel = service_end_time + travel_time_to_wh
                        if arrival_at_wh_after_parcel > agent_op_end_time:
                            feasible = False

                    if feasible and dist_to_parcel < min_dist_candidate:
                        min_dist_candidate = dist_to_parcel
                        best_parcel_candidate = parcel_data
                        best_parcel_idx = i
                        candidate_arrival_time = service_start_time
                        candidate_departure_time = service_end_time
            
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
        
        # Return to warehouse if enabled
        if params.get("return_to_warehouse", True):
            agent_route_stops_coords.append(list(warehouse_coords))
            agent_route_stop_ids.append("Warehouse")
            dist_to_wh = _calculate_distance(current_location, warehouse_coords)
            travel_time_to_wh = dist_to_wh * time_per_dist_unit
            arrival_at_wh = current_time + travel_time_to_wh
            agent_arrival_times.append(round(arrival_at_wh))
            agent_departure_times.append(round(arrival_at_wh)) # Arrival and departure are same for final WH

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
                "route_stop_coordinates": agent_route_stops_coords,
                "total_weight": sum(p["weight"] for p in agent_route_parcels),
                "capacity_weight": agent["capacity_weight"],
                "total_distance": round(total_distance, 2),
                "arrival_times": agent_arrival_times,
                "departure_times": agent_departure_times
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
