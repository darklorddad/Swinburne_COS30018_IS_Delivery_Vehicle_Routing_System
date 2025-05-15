# DVRS Optimisation Script: Configurable Greedy Algorithm
import math
import random

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "distance_weight",
                "label": "Distance Weight", 
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "help": "Weight given to distance in parcel selection"
            },
            {
                "name": "capacity_weight",
                "label": "Capacity Weight",
                "type": "float", 
                "default": 0.3,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "help": "Weight given to remaining capacity in selection"
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after delivery"
            },
            {
                "name": "sort_parcels",
                "label": "Sort Parcels By",
                "type": "selectbox",
                "default": "none",
                "options": ["none", "weight_asc", "weight_desc"],
                "help": "Initial sorting of parcels before assignment"
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def run_optimisation(config_data, params):
    """Greedy algorithm with weighted distance/capacity considerations"""
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels = [dict(p) for p in config_data.get("parcels", [])]
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Apply initial sorting if specified
    if params["sort_parcels"] == "weight_asc":
        parcels.sort(key=lambda x: x["weight"])
    elif params["sort_parcels"] == "weight_desc":
        parcels.sort(key=lambda x: x["weight"], reverse=True)

    optimised_routes = []
    unassigned = []
    
    for agent in delivery_agents:
        current_cap = agent["capacity_weight"]
        current_loc = warehouse_coords.copy()
        route = {
            "agent_id": agent["id"],
            "parcels": [],
            "stops": [{"id": "Warehouse", "coords": warehouse_coords}],
            "total_weight": 0,
            "total_distance": 0
        }
        
        while True:
            best_score = -float('inf')
            best_parcel = None
            best_idx = -1
            
            for idx, p in enumerate(parcels):
                if p["weight"] > current_cap:
                    continue
                    
                # Calculate weighted score
                dist = _calculate_distance(current_loc, p["coordinates_x_y"])
                cap_score = current_cap - p["weight"]
                combined = (params["distance_weight"] * (1/dist) if dist > 0 else 0) + \
                          (params["capacity_weight"] * cap_score)
                
                if combined > best_score:
                    best_score = combined
                    best_parcel = p
                    best_idx = idx
            
            if best_parcel:
                # Update route
                current_cap -= best_parcel["weight"]
                route["parcels"].append(best_parcel)
                route["total_weight"] += best_parcel["weight"]
                route["stops"].append({
                    "id": best_parcel["id"],
                    "coords": best_parcel["coordinates_x_y"]
                })
                route["route_stop_ids"] = [stop["id"] for stop in route["stops"]]
                # Update location and remove parcel
                current_loc = best_parcel["coordinates_x_y"].copy()
                del parcels[best_idx]
            else:
                break  # No more parcels can be assigned
        
        # Add return to warehouse if enabled
        if params["return_to_warehouse"] and route["stops"]:
            route["stops"].append({"id": "Warehouse", "coords": warehouse_coords})
        
        # Update route stop IDs list
        route["route_stop_ids"] = [stop["id"] for stop in route["stops"]]
        
        # Calculate total distance
        total_dist = 0
        for i in range(len(route["stops"])-1):
            total_dist += _calculate_distance(
                route["stops"][i]["coords"], 
                route["stops"][i+1]["coords"]
            )
        route["total_distance"] = round(total_dist, 2)
        
        if route["parcels"]:
            optimised_routes.append(route)
    
    unassigned = parcels  # Remaining parcels
    
    return {
        "status": "success",
        "message": "Configurable greedy optimisation completed",
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned],
        "unassigned_parcels_details": unassigned
    }
