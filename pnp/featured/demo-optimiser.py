# DVRS Optimisation Script: Greedy Nearest Neighbour
import math
import datetime

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
                "name": "distance_weight",
                "label": "Distance weight",
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "help": "Weight given to distance vs capacity utilization"
            },
            {
                "name": "service_time_per_stop_minutes",
                "label": "Service Time (mins)",
                "type": "integer",
                "default": 10,
                "min": 0,
                "help": "Fixed time spent at each delivery location"
            },
            {
                "name": "time_per_distance_unit_minutes",
                "label": "Time per Distance Unit (mins)",
                "type": "float",
                "default": 5.0,
                "min": 0.1,
                "help": "Time taken to travel one unit of distance"
            }
        ]
    }

def time_str_to_datetime(time_str, date_obj=None):
    """Converts HH:MM string to a datetime.datetime object."""
    if not time_str: return None
    if not date_obj:
        date_obj = datetime.date.today()
    try:
        t = datetime.datetime.strptime(time_str, "%H:%M").time()
        return datetime.datetime.combine(date_obj, t)
    except (ValueError, TypeError):
        return None

def datetime_to_time_str(dt_obj):
    """Converts datetime.datetime or datetime.time object to HH:MM string."""
    return dt_obj.strftime("%H:%M") if dt_obj else "N/A"

def _calculate_distance(coord1, coord2):
    # Calculates Euclidean distance between two points.
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    unassigned_parcels = [dict(p) for p in config_data.get("parcels", [])]
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Get time parameters
    service_time_minutes = params.get("service_time_per_stop_minutes", 10)
    time_per_dist_unit_minutes = params.get("time_per_distance_unit_minutes", 5.0)
    
    # Apply sorting if specified in parameters
    if params.get("sort_parcels", "none") != "none":
        reverse_sort = params["sort_parcels"] == "weight_desc"
        unassigned_parcels.sort(key=lambda x: x["weight"], reverse=reverse_sort)

    optimised_routes = []
    parcels_assigned_globally = set()
    distance_weight = params.get("distance_weight", 1.0)

    for agent in delivery_agents:
        current_capacity = agent["capacity_weight"]
        current_location = list(warehouse_coords)
        
        # Initialize agent's start time
        agent_shift_start_str = agent.get("shift_start", "00:00")
        current_agent_time = time_str_to_datetime(agent_shift_start_str)
        if not current_agent_time:
            current_agent_time = time_str_to_datetime("00:00")
        
        # Create parcel lookup map
        all_parcels_map = {p["id"]: p for p in config_data.get("parcels", [])}
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
                    # Calculate weighted distance score
                    raw_dist = _calculate_distance(current_location, parcel_data["coordinates_x_y"])
                    dist_score = raw_dist * distance_weight
                    
                    # Add inverse capacity utilization to prefer vehicles with more remaining capacity
                    capacity_utilization = (agent["capacity_weight"] - current_capacity) / agent["capacity_weight"]
                    score = dist_score * (1 + capacity_utilization)
                    
                    if score < min_dist_candidate:
                        min_dist_candidate = score
                        best_parcel_candidate = parcel_data
                        best_parcel_idx = i
            
            if best_parcel_candidate:
                # Assign the best found parcel
                assigned_parcel = unassigned_parcels.pop(best_parcel_idx) # Remove from unassigned
                parcels_assigned_globally.add(assigned_parcel["id"])

                # Calculate travel time and handle delivery time windows
                travel_distance = _calculate_distance(current_location, assigned_parcel["coordinates_x_y"])
                travel_duration = travel_distance * time_per_dist_unit_minutes
                current_agent_time += datetime.timedelta(minutes=travel_duration)
                
                # Check earliest delivery time constraint
                parcel_data = all_parcels_map.get(assigned_parcel["id"], {})
                earliest_delivery = time_str_to_datetime(parcel_data.get("earliest_delivery"))
                if earliest_delivery and current_agent_time < earliest_delivery:
                    current_agent_time = earliest_delivery
                
                # Set arrival and departure times
                assigned_parcel["arrival_time"] = datetime_to_time_str(current_agent_time)
                current_agent_time += datetime.timedelta(minutes=service_time_minutes)
                assigned_parcel["departure_time"] = datetime_to_time_str(current_agent_time)

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
