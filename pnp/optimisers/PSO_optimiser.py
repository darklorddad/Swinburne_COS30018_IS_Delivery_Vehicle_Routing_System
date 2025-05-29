import math
import random
import copy
import numpy as np

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "num_particles",
                "label": "Number of Particles",
                "type": "integer",
                "default": 30,
                "min": 10,
                "max": 100,
                "step": 5,
                "help": "Number of particles in the swarm"
            },
            {
                "name": "iterations",
                "label": "Number of Iterations",
                "type": "integer",
                "default": 100,
                "min": 20,
                "max": 500,
                "step": 10,
                "help": "Number of iterations to run the algorithm"
            },
            {
                "name": "inertia_weight",
                "label": "Inertia Weight (ω)",
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.2,
                "step": 0.05,
                "help": "Controls momentum of particles"
            },
            {
                "name": "cognitive_weight",
                "label": "Cognitive Weight (c1)",
                "type": "float",
                "default": 1.5,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "help": "Attraction to particle's best position"
            },
            {
                "name": "social_weight",
                "label": "Social Weight (c2)",
                "type": "float",
                "default": 1.5,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "help": "Attraction to swarm's best position"
            },
            {
                "name": "velocity_clamp",
                "label": "Velocity Clamp",
                "type": "float",
                "default": 0.5,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "help": "Maximum velocity change per iteration"
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

def _initialize_particles(num_particles, num_parcels, num_agents):
    """Initialize particle positions and velocities."""
    particles = []
    for _ in range(num_particles):
        # Position: [agent assignment, parcel sequence]
        position = np.zeros((num_parcels, 2))
        position[:, 0] = np.random.uniform(0, num_agents, num_parcels)  # Agent assignment
        position[:, 1] = np.random.uniform(0, 1, num_parcels)           # Sequence priority
        
        # Velocity: initialize with random values
        velocity = np.random.uniform(-0.1, 0.1, (num_parcels, 2))
        
        particles.append({
            "position": position,
            "velocity": velocity,
            "best_position": position.copy(),
            "best_fitness": float('inf')
        })
    return particles

def _decode_particle_position(position, parcels, delivery_agents, warehouse_coords, return_to_warehouse):
    """Convert continuous particle position to discrete routes."""
    num_parcels = len(parcels)
    num_agents = len(delivery_agents)
    
    # Extract agent assignments and sequence priorities
    agent_assignments = np.floor(position[:, 0]).astype(int)
    sequence_priorities = position[:, 1]
    
    # Initialize routes and loads
    routes = [[] for _ in range(num_agents)]
    current_loads = [0.0] * num_agents
    agent_capacities = [agent["capacity_weight"] for agent in delivery_agents]
    
    # Sort parcels by sequence priority
    sorted_indices = np.argsort(sequence_priorities)
    
    # Assign parcels to agents in priority order
    for idx in sorted_indices:
        parcel = parcels[idx]
        assigned_agent = agent_assignments[idx] % num_agents
        
        # Check capacity constraint
        if current_loads[assigned_agent] + parcel["weight"] <= agent_capacities[assigned_agent]:
            routes[assigned_agent].append(parcel)
            current_loads[assigned_agent] += parcel["weight"]
    
    # Sort parcels within each route by proximity to warehouse
    for agent_idx in range(num_agents):
        if not routes[agent_idx]:
            continue
        
        # Calculate distance from warehouse to each parcel
        parcel_distances = [
            _calculate_distance(warehouse_coords, p["coordinates_x_y"])
            for p in routes[agent_idx]
        ]
        
        # Sort parcels by distance from warehouse (nearest first)
        sorted_parcels = [p for _, p in sorted(zip(parcel_distances, routes[agent_idx]))]
        routes[agent_idx] = sorted_parcels
    
    return routes

def _calculate_fitness(routes, warehouse_coords, return_to_warehouse, parcels):
    """Calculate solution fitness (lower is better)."""
    total_distance = 0
    unassigned_penalty = 0
    
    # Calculate route distances
    for route in routes:
        total_distance += _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
    
    # Calculate unassigned parcels penalty
    assigned_parcels = set()
    for route in routes:
        for parcel in route:
            assigned_parcels.add(parcel["id"])
    
    unassigned_count = len(parcels) - len(assigned_parcels)
    if unassigned_count > 0:
        # Calculate average distance from warehouse to parcels
        avg_distance = sum(
            _calculate_distance(warehouse_coords, p["coordinates_x_y"])
            for p in parcels
        ) / len(parcels)
        unassigned_penalty = avg_distance * unassigned_count * 100  # Large penalty factor
    
    return total_distance + unassigned_penalty

def _update_velocity(particle, global_best_position, params):
    """Update particle velocity using PSO equations."""
    w = params["inertia_weight"]
    c1 = params["cognitive_weight"]
    c2 = params["social_weight"]
    v_clamp = params["velocity_clamp"]
    
    r1 = random.random()
    r2 = random.random()
    
    # Calculate cognitive and social components
    cognitive = c1 * r1 * (particle["best_position"] - particle["position"])
    social = c2 * r2 * (global_best_position - particle["position"])
    
    # Update velocity
    new_velocity = w * particle["velocity"] + cognitive + social
    
    # Apply velocity clamping
    new_velocity = np.clip(new_velocity, -v_clamp, v_clamp)
    
    return new_velocity

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract parameters
    num_particles = params.get("num_particles", 30)
    iterations = params.get("iterations", 100)
    inertia_weight = params.get("inertia_weight", 0.8)
    cognitive_weight = params.get("cognitive_weight", 1.5)
    social_weight = params.get("social_weight", 1.5)
    velocity_clamp = params.get("velocity_clamp", 0.5)
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
    num_parcels = len(parcels_copy)
    num_agents = len(delivery_agents_copy)
    
    # Initialize particles and global best
    particles = _initialize_particles(num_particles, num_parcels, num_agents)
    global_best_position = None
    global_best_fitness = float('inf')
    global_best_routes = None
    
    # Main PSO loop
    for iteration in range(iterations):
        for particle in particles:
            # Decode particle position to routes
            routes = _decode_particle_position(
                particle["position"],
                parcels_copy,
                delivery_agents_copy,
                warehouse_coords,
                return_to_warehouse
            )
            
            # Calculate fitness
            fitness = _calculate_fitness(
                routes,
                warehouse_coords,
                return_to_warehouse,
                parcels_copy
            )
            
            # Update personal best
            if fitness < particle["best_fitness"]:
                particle["best_fitness"] = fitness
                particle["best_position"] = particle["position"].copy()
            
            # Update global best
            if fitness < global_best_fitness:
                global_best_fitness = fitness
                global_best_position = particle["position"].copy()
                global_best_routes = copy.deepcopy(routes)
        
        # Update velocities and positions
        for particle in particles:
            if global_best_position is not None:
                particle["velocity"] = _update_velocity(
                    particle,
                    global_best_position,
                    {
                        "inertia_weight": inertia_weight,
                        "cognitive_weight": cognitive_weight,
                        "social_weight": social_weight,
                        "velocity_clamp": velocity_clamp
                    }
                )
                particle["position"] += particle["velocity"]
    
    # Prepare results
    if global_best_routes is None:
        # Fallback: create empty routes
        global_best_routes = [[] for _ in delivery_agents_copy]
    
    optimised_routes = []
    assigned_parcel_ids = set()
    
    for agent_idx, route in enumerate(global_best_routes):
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
            "total_weight": sum(p["weight"] for p in route),
            "capacity_weight": agent["capacity_weight"],
            "total_distance": round(route_distance, 2),
        })
    
    # Identify unassigned parcels
    unassigned_parcels = [p for p in parcels if p["id"] not in assigned_parcel_ids]
    
    status = "success" if not unassigned_parcels else "warning"
    message = "Particle Swarm Optimization completed."
    if unassigned_parcels:
        message += f" {len(unassigned_parcels)} parcel(s) could not be assigned due to capacity constraints."
    
    return {
        "status": status,
        "message": message,
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned_parcels],
        "unassigned_parcels_details": unassigned_parcels
    }