import math
import random
import copy

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "num_iterations",
                "label": "Number of Iterations",
                "type": "integer",
                "default": 100,
                "min": 10,
                "max": 1000,
                "help": "Number of iterations for the PSO algorithm."
            },
            {
                "name": "num_particles",
                "label": "Number of Particles",
                "type": "integer",
                "default": 30,
                "min": 5,
                "max": 100,
                "help": "Number of particles in the swarm."
            },
            {
                "name": "inertia_weight_w",
                "label": "Inertia Weight (w)",
                "type": "float",
                "default": 0.7,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "help": "Inertia weight, balances global and local search."
            },
            {
                "name": "cognitive_c1",
                "label": "Cognitive Coefficient (c1)",
                "type": "float",
                "default": 1.5,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "help": "Influence of particle's personal best."
            },
            {
                "name": "social_c2",
                "label": "Social Coefficient (c2)",
                "type": "float",
                "default": 1.5,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "help": "Influence of swarm's global best."
            },
            {
                "name": "max_velocity_factor",
                "label": "Max Velocity Factor (for keys in [0,1])",
                "type": "float",
                "default": 0.2,
                "min": 0.05,
                "max": 0.5,
                "step": 0.01,
                "help": "Max velocity as a factor of position range (e.g., 0.2 * 1.0 if keys are 0-1)."
            },
            {
                "name": "time_per_distance_unit",
                "label": "Time per distance unit (minutes)",
                "type": "float",
                "default": 2.0,
                "min": 0.1,
                "step": 0.1,
                "help": "Minutes taken to travel one unit of distance."
            },
            {
                "name": "default_service_time",
                "label": "Default service time at stop (minutes)",
                "type": "integer",
                "default": 10,
                "min": 0,
                "help": "Default time spent at each parcel stop if not specified."
            },
            {
                "name": "generic_vehicle_capacity",
                "label": "Generic Vehicle Capacity (for PSO route building)",
                "type": "integer",
                "default": 100,
                "min": 1,
                "help": "Capacity constraint used during PSO's internal route formation."
            },
            {
                "name": "generic_max_route_duration",
                "label": "Generic Max Route Duration (for PSO, minutes)",
                "type": "integer",
                "default": 720, # 12 hours, made more accommodating
                "min": 30,
                "help": "Maximum duration for a route (warehouse-to-warehouse) during PSO's internal route building."
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_schedule_and_feasibility(ordered_parcel_objects, # List of parcel objects
                                              agent_or_generic_constraints,
                                              warehouse_coords, params, parcel_map_for_lookup):
    """
    Calculates schedule for a sequence of parcels against specific agent or generic constraints.
    Returns: (is_feasible, schedule_details_dict)
    """
    time_per_dist_unit = params.get("time_per_distance_unit", 2.0)
    default_service_time = params.get("default_service_time", 10)

    is_specific_agent = "operating_hours_start" in agent_or_generic_constraints
    if is_specific_agent:
        vehicle_capacity = agent_or_generic_constraints["capacity_weight"]
        route_start_time = agent_or_generic_constraints["operating_hours_start"]
        vehicle_op_end_time = agent_or_generic_constraints["operating_hours_end"]
    else:
        vehicle_capacity = agent_or_generic_constraints["generic_vehicle_capacity"]
        route_start_time = 0
        vehicle_op_end_time = agent_or_generic_constraints["generic_max_route_duration"]

    route_stop_ids = ["Warehouse"]
    route_stop_coordinates = [list(warehouse_coords)]
    arrival_times = [round(route_start_time)]
    departure_times = [round(route_start_time)]

    current_time_on_route = route_start_time
    current_location = list(warehouse_coords)
    current_load = 0
    total_distance = 0.0

    for p_obj_original in ordered_parcel_objects:
        p_obj = parcel_map_for_lookup.get(p_obj_original["id"], p_obj_original)
        p_id = p_obj["id"]
        p_coords = p_obj["coordinates_x_y"]
        p_weight = p_obj["weight"]
        p_service_time = p_obj.get("service_time", default_service_time)
        p_tw_open = p_obj.get("time_window_open", 0)
        p_tw_close = p_obj.get("time_window_close", 1439)

        current_load += p_weight
        if current_load > vehicle_capacity: return False, {}

        dist_to_parcel = _calculate_distance(current_location, p_coords)
        total_distance += dist_to_parcel
        travel_time = dist_to_parcel * time_per_dist_unit
        physical_arrival_at_parcel = current_time_on_route + travel_time
        actual_service_start_time = max(physical_arrival_at_parcel, p_tw_open)

        if actual_service_start_time > p_tw_close: return False, {}
        actual_service_end_time = actual_service_start_time + p_service_time
        if actual_service_end_time > p_tw_close: return False, {}
        if is_specific_agent and actual_service_end_time > vehicle_op_end_time: return False, {}

        route_stop_ids.append(p_id)
        route_stop_coordinates.append(list(p_coords))
        arrival_times.append(round(physical_arrival_at_parcel))
        departure_times.append(round(actual_service_end_time))
        current_time_on_route = actual_service_end_time
        current_location = list(p_coords)

    dist_to_warehouse = _calculate_distance(current_location, warehouse_coords)
    total_distance += dist_to_warehouse
    travel_time_to_wh = dist_to_warehouse * time_per_dist_unit
    physical_arrival_at_warehouse_final = current_time_on_route + travel_time_to_wh

    if is_specific_agent and physical_arrival_at_warehouse_final > vehicle_op_end_time: return False, {}
    route_duration_from_wh_to_wh = physical_arrival_at_warehouse_final - route_start_time
    if not is_specific_agent and route_duration_from_wh_to_wh > vehicle_op_end_time: return False, {}

    route_stop_ids.append("Warehouse")
    route_stop_coordinates.append(list(warehouse_coords))
    arrival_times.append(round(physical_arrival_at_warehouse_final))
    departure_times.append(round(physical_arrival_at_warehouse_final))

    return True, {
        "route_stop_ids": route_stop_ids, "route_stop_coordinates": route_stop_coordinates,
        "arrival_times": arrival_times, "departure_times": departure_times,
        "total_distance": round(total_distance, 2), "total_load": current_load,
        "route_duration_actual": round(route_duration_from_wh_to_wh)
    }

def _decode_particle_to_routes_and_evaluate(particle_position_keys, # List of random keys
                                            all_parcel_objects_original_order, # To map sorted keys back to parcels
                                            warehouse_coords, params, parcel_map_for_lookup,
                                            effective_generic_constraints_for_decode): # New argument
    """
    Decodes a particle's random key position into a set of routes using generic constraints.
    Returns: (fitness_tuple, list_of_routes_of_parcel_objects, list_of_unassigned_parcel_objects)
    Fitness tuple: (number_of_unassigned_parcels, total_distance_of_assigned_routes)
    """
    # Create pairs of (key, parcel_object) then sort by key to get permutation
    keyed_parcels = sorted(zip(particle_position_keys, all_parcel_objects_original_order), key=lambda x: x[0])
    parcel_permutation = [p_obj for key, p_obj in keyed_parcels]


    routes_formed_parcels = [] # List of lists of parcel objects
    parcels_assigned_in_solution = set()
    total_distance_for_solution = 0.0
    
    parcels_to_assign_in_permutation = list(parcel_permutation) # Make a mutable copy

    while parcels_to_assign_in_permutation:
        current_route_parcels = []
        # Try to build one route using generic constraints
        
        # Greedily add parcels from the *remaining* permutation
        temp_unassigned_this_route = []
        for i in range(len(parcels_to_assign_in_permutation)):
            p_obj_to_try = parcels_to_assign_in_permutation[i]
            
            # Check if adding this parcel is feasible for the current_route_parcels
            temp_candidate_route = current_route_parcels + [p_obj_to_try]
            is_feasible_addition, _ = _calculate_route_schedule_and_feasibility(
                temp_candidate_route, effective_generic_constraints_for_decode, warehouse_coords, params, parcel_map_for_lookup
            )
            if is_feasible_addition:
                current_route_parcels.append(p_obj_to_try)
            else:
                temp_unassigned_this_route.append(p_obj_to_try)
        
        # Update parcels_to_assign_in_permutation for the next route attempt
        parcels_to_assign_in_permutation = temp_unassigned_this_route

        if current_route_parcels: # A valid route was formed
            # Final calculation for this route's details
            _, route_details = _calculate_route_schedule_and_feasibility(
                current_route_parcels, effective_generic_constraints_for_decode, warehouse_coords, params, parcel_map_for_lookup
            )
            routes_formed_parcels.append(current_route_parcels) # Store list of parcel objects
            total_distance_for_solution += route_details["total_distance"]
            for p_obj in current_route_parcels:
                parcels_assigned_in_solution.add(p_obj["id"])
        else: # No parcel could be added to start/continue this route
            break # Stop forming routes if the remaining parcels cannot start a new one

    unassigned_parcel_objects = [p for p in all_parcel_objects_original_order if p["id"] not in parcels_assigned_in_solution]
    fitness = (len(unassigned_parcel_objects), total_distance_for_solution)
    
    return fitness, routes_formed_parcels, unassigned_parcel_objects


class Particle:
    def __init__(self, num_dimensions, pos_min=0.0, pos_max=1.0, max_velocity_factor=0.2):
        self.position = [random.uniform(pos_min, pos_max) for _ in range(num_dimensions)]
        self.velocity = [random.uniform(-max_velocity_factor, max_velocity_factor) for _ in range(num_dimensions)] # Vmax based on range of 1.0
        self.pbest_position = list(self.position)
        self.pbest_fitness = (float('inf'), float('inf')) # (unassigned_count, total_distance)
        self.current_fitness = (float('inf'), float('inf'))
        self.current_routes_parcels = [] # List of lists of parcel objects
        self.pos_min = pos_min
        self.pos_max = pos_max
        self.max_velocity = max_velocity_factor * (pos_max - pos_min)

    def update_velocity(self, gbest_position, w, c1, c2):
        for i in range(len(self.position)):
            r1, r2 = random.random(), random.random()
            cognitive_comp = c1 * r1 * (self.pbest_position[i] - self.position[i])
            social_comp = c2 * r2 * (gbest_position[i] - self.position[i])
            self.velocity[i] = w * self.velocity[i] + cognitive_comp + social_comp
            # Clamp velocity
            self.velocity[i] = max(-self.max_velocity, min(self.max_velocity, self.velocity[i]))

    def update_position(self):
        for i in range(len(self.position)):
            self.position[i] += self.velocity[i]
            # Clamp position to [pos_min, pos_max]
            self.position[i] = max(self.pos_min, min(self.pos_max, self.position[i]))


def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    all_parcels_list_orig = [copy.deepcopy(p) for p in config_data.get("parcels", [])] # Keep original
    delivery_agents = config_data.get("delivery_agents", [])

    if not all_parcels_list_orig:
        return {"status": "success", "message": "No parcels to deliver.", "optimised_routes": [], "unassigned_parcels": [], "unassigned_parcels_details": []}
    if not delivery_agents:
        return {"status": "success", "message": "No delivery agents available.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_list_orig], "unassigned_parcels_details": all_parcels_list_orig}

    num_dimensions = len(all_parcels_list_orig) # Each dimension corresponds to a parcel's random key
    parcel_map = {p["id"]: p for p in all_parcels_list_orig}

    # PSO Parameters
    num_iterations = params.get("num_iterations", 100)
    num_particles = params.get("num_particles", 30)
    w_inertia = params.get("inertia_weight_w", 0.7)
    c1_cognitive = params.get("cognitive_c1", 1.5)
    c2_social = params.get("social_c2", 1.5)
    max_velocity_factor = params.get("max_velocity_factor", 0.2) # Factor for keys in [0,1]

    pos_min_val, pos_max_val = 0.0, 1.0 # Range for random keys

    # --- Determine effective generic constraints for PSO decoding ---
    user_set_generic_duration_pso = params.get("generic_max_route_duration", 720) # Default from updated PSO schema

    adaptive_min_duration_needed = 0
    if all_parcels_list_orig:
        latest_tw_close = 0
        for p_obj in all_parcels_list_orig:
            latest_tw_close = max(latest_tw_close, p_obj.get("time_window_close", 0))
        adaptive_min_duration_needed = latest_tw_close + 120 # Add a 2-hour buffer for service/travel
    else:
        adaptive_min_duration_needed = user_set_generic_duration_pso

    effective_generic_max_route_duration_pso = max(user_set_generic_duration_pso, adaptive_min_duration_needed)

    user_set_generic_capacity_pso = params.get("generic_vehicle_capacity", 100)
    actual_max_agent_capacity_pso = 1
    if delivery_agents:
        agent_caps = [da.get("capacity_weight", 1) for da in delivery_agents if isinstance(da, dict)]
        if agent_caps:
            actual_max_agent_capacity_pso = max(agent_caps) if agent_caps else 1
    
    effective_generic_capacity_pso = min(user_set_generic_capacity_pso, actual_max_agent_capacity_pso)
    if effective_generic_capacity_pso <= 0: effective_generic_capacity_pso = 1

    effective_generic_constraints = {
        "generic_vehicle_capacity": effective_generic_capacity_pso,
        "generic_max_route_duration": effective_generic_max_route_duration_pso
    }

    # Initialize swarm
    swarm = [Particle(num_dimensions, pos_min_val, pos_max_val, max_velocity_factor) for _ in range(num_particles)]
    
    gbest_position = None
    gbest_fitness = (float('inf'), float('inf')) # (unassigned_count, total_distance)
    gbest_routes_parcels = [] # List of lists of parcel objects for the global best solution

    for iteration in range(num_iterations):
        for particle in swarm:
            # Decode particle's position (random keys) into routes and evaluate fitness
            fitness, routes_p_objs, _ = _decode_particle_to_routes_and_evaluate(
                particle.position, all_parcels_list_orig, warehouse_coords, params, parcel_map,
                effective_generic_constraints
            )
            particle.current_fitness = fitness
            particle.current_routes_parcels = routes_p_objs

            # Update pbest
            if (particle.current_fitness[0] < particle.pbest_fitness[0]) or \
               (particle.current_fitness[0] == particle.pbest_fitness[0] and particle.current_fitness[1] < particle.pbest_fitness[1]):
                particle.pbest_fitness = particle.current_fitness
                particle.pbest_position = list(particle.position)
            
            # Update gbest
            if (particle.pbest_fitness[0] < gbest_fitness[0]) or \
               (particle.pbest_fitness[0] == gbest_fitness[0] and particle.pbest_fitness[1] < gbest_fitness[1]):
                gbest_fitness = particle.pbest_fitness
                gbest_position = list(particle.pbest_position)
                # Store the routes corresponding to this gbest
                # Need to re-decode pbest_position because current_routes_parcels is from current_position
                _, gbest_routes_parcels, _ = _decode_particle_to_routes_and_evaluate(
                    gbest_position, all_parcels_list_orig, warehouse_coords, params, parcel_map,
                    effective_generic_constraints
                )

        if gbest_position is None: # Should only happen if all particles failed to assign any parcel on first iter
            # This is unlikely if there's at least one parcel and generic constraints are reasonable.
            # If it does, pick a random particle's pbest as gbest to start.
            if swarm and swarm[0].pbest_position:
                 gbest_position = list(swarm[0].pbest_position)
                 # And re-evaluate to get its routes for gbest_routes_parcels
                 _, gbest_routes_parcels, _ = _decode_particle_to_routes_and_evaluate(
                    gbest_position, all_parcels_list_orig, warehouse_coords, params, parcel_map
                )
            else: # No parcels or catastrophic failure.
                 break


        # Update velocities and positions for next iteration
        for particle in swarm:
            particle.update_velocity(gbest_position, w_inertia, c1_cognitive, c2_social)
            particle.update_position()

    # --- Final assignment of gbest_routes_parcels to specific delivery agents ---
    optimised_routes_output = []
    assigned_parcels_globally_ids = set()
    
    if not gbest_routes_parcels: # No routes were formed by PSO
        final_unassigned_parcel_ids = [p["id"] for p in all_parcels_list_orig]
        final_unassigned_parcels_details = all_parcels_list_orig
        message = "PSO completed, but no feasible routes could be formed by the best particle."
    else:
        # Sort gbest_routes (list of lists of parcel objects) e.g., by number of parcels
        # Make copies for sorting
        sorted_gbest_routes_obj_lists = [list(r_list) for r_list in gbest_routes_parcels]
        sorted_gbest_routes_obj_lists.sort(key=len, reverse=True)
        
        used_agent_ids = set()

        for route_parcel_obj_list in sorted_gbest_routes_obj_lists:
            if not route_parcel_obj_list: continue

            best_agent_for_this_route = None
            best_schedule_details_for_agent = None

            for agent_config in delivery_agents:
                if agent_config["id"] in used_agent_ids:
                    continue

                is_feasible_for_agent, schedule_details = _calculate_route_schedule_and_feasibility(
                    route_parcel_obj_list, agent_config, warehouse_coords, params, parcel_map
                )
                if is_feasible_for_agent:
                    best_agent_for_this_route = agent_config
                    best_schedule_details_for_agent = schedule_details
                    break 
            
            if best_agent_for_this_route and best_schedule_details_for_agent:
                assigned_agent_id = best_agent_for_this_route["id"]
                used_agent_ids.add(assigned_agent_id)
                
                current_route_parcel_ids = [p_obj["id"] for p_obj in route_parcel_obj_list]
                current_route_parcels_details = [copy.deepcopy(p_obj) for p_obj in route_parcel_obj_list]
                for p_id in current_route_parcel_ids:
                    assigned_parcels_globally_ids.add(p_id)

                optimised_routes_output.append({
                    "agent_id": assigned_agent_id,
                    "parcels_assigned_ids": current_route_parcel_ids,
                    "parcels_assigned_details": current_route_parcels_details,
                    "route_stop_ids": best_schedule_details_for_agent["route_stop_ids"],
                    "route_stop_coordinates": best_schedule_details_for_agent["route_stop_coordinates"],
                    "total_weight": best_schedule_details_for_agent["total_load"],
                    "capacity_weight": best_agent_for_this_route["capacity_weight"],
                    "total_distance": best_schedule_details_for_agent["total_distance"],
                    "arrival_times": best_schedule_details_for_agent["arrival_times"],
                    "departure_times": best_schedule_details_for_agent["departure_times"]
                })
        
        final_unassigned_parcel_ids = [p["id"] for p in all_parcels_list_orig if p["id"] not in assigned_parcels_globally_ids]
        final_unassigned_parcels_details = [copy.deepcopy(parcel_map[p_id]) for p_id in final_unassigned_parcel_ids]
        message = (f"PSO completed. Iterations: {iteration+1}/{num_iterations}. "
                   f"Best solution: {gbest_fitness[0]} unassigned, {gbest_fitness[1]:.2f} distance. "
                   f"Final unassigned after agent assignment: {len(final_unassigned_parcel_ids)}")


    return {
        "status": "success",
        "message": message,
        "optimised_routes": optimised_routes_output,
        "unassigned_parcels": final_unassigned_parcel_ids,
        "unassigned_parcels_details": final_unassigned_parcels_details
    }
