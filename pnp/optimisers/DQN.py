import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import torch.nn.functional as F

class DQN(nn.Module):
    """Deep Q-Network for delivery route optimization"""
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, output_size)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return self.fc4(x)

class ReplayBuffer:
    """Experience replay buffer for DQN"""
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "episodes",
                "label": "Training Episodes",
                "type": "integer",
                "default": 500,
                "min": 100,
                "max": 5000,
                "step": 100,
                "help": "Number of training episodes"
            },
            {
                "name": "epsilon_start",
                "label": "Initial Epsilon",
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "help": "Initial exploration rate"
            },
            {
                "name": "epsilon_end",
                "label": "Final Epsilon",
                "type": "float",
                "default": 0.01,
                "min": 0.01,
                "max": 0.2,
                "step": 0.01,
                "help": "Final exploration rate"
            },
            {
                "name": "epsilon_decay",
                "label": "Epsilon Decay",
                "type": "float",
                "default": 0.995,
                "min": 0.9,
                "max": 0.999,
                "step": 0.001,
                "help": "Epsilon decay rate per episode"
            },
            {
                "name": "learning_rate",
                "label": "Learning Rate",
                "type": "float",
                "default": 0.001,
                "min": 0.0001,
                "max": 0.01,
                "step": 0.0001,
                "help": "Neural network learning rate"
            },
            {
                "name": "batch_size",
                "label": "Batch Size",
                "type": "integer",
                "default": 64,
                "min": 16,
                "max": 256,
                "step": 16,
                "help": "Training batch size"
            },
            {
                "name": "gamma",
                "label": "Discount Factor (γ)",
                "type": "float",
                "default": 0.99,
                "min": 0.9,
                "max": 0.999,
                "step": 0.001,
                "help": "Reward discount factor"
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

def _state_to_vector(state, max_capacity, max_weight, max_coord):
    """Convert state to normalized feature vector"""
    state_vector = []
    
    # Vehicle states (remaining capacity)
    for vehicle in state["vehicles"]:
        state_vector.append(vehicle["remaining_capacity"] / max_capacity)
    
    # Parcel states (weight, coordinates, assigned status)
    for parcel in state["parcels"]:
        state_vector.append(parcel["weight"] / max_weight)
        state_vector.append(parcel["coordinates_x_y"][0] / max_coord)
        state_vector.append(parcel["coordinates_x_y"][1] / max_coord)
        state_vector.append(1.0 if parcel["assigned"] else 0.0)
    
    return np.array(state_vector, dtype=np.float32)

def _select_action(state_vector, policy_net, epsilon, n_actions, valid_actions_mask):
    """Select action using epsilon-greedy policy"""
    if random.random() < epsilon:
        # Exploration: choose random valid action
        return random.choice([i for i in range(n_actions) if valid_actions_mask[i]])
    
    # Exploitation: choose best valid action
    with torch.no_grad():
        state_tensor = torch.tensor(state_vector, dtype=torch.float32).unsqueeze(0)
        q_values = policy_net(state_tensor).squeeze(0).numpy()
        
        # Mask invalid actions
        masked_q = q_values.copy()
        masked_q[~valid_actions_mask] = -np.inf
        
        return np.argmax(masked_q)

def _apply_action(state, action, parcels, delivery_agents):
    """Apply action to state and return next state"""
    next_state = copy.deepcopy(state)
    n_agents = len(delivery_agents)
    
    # Decode action: (parcel_idx, agent_idx)
    parcel_idx = action // n_agents
    agent_idx = action % n_agents
    
    parcel = parcels[parcel_idx]
    agent = delivery_agents[agent_idx]
    
    # Apply assignment if valid
    if (not next_state["parcels"][parcel_idx]["assigned"] and 
        next_state["vehicles"][agent_idx]["remaining_capacity"] >= parcel["weight"]):
        
        next_state["parcels"][parcel_idx]["assigned"] = True
        next_state["vehicles"][agent_idx]["remaining_capacity"] -= parcel["weight"]
    
    return next_state

def _calculate_reward(state, next_state, warehouse_coords, return_to_warehouse, parcels, delivery_agents):
    """Calculate reward for state transition"""
    reward = 0
    
    # Assignment reward
    assigned_count = sum(p["assigned"] for p in next_state["parcels"]) - sum(p["assigned"] for p in state["parcels"])
    reward += assigned_count * 10  # Reward for assigning parcels
    
    # Distance penalty (estimated)
    for agent_idx in range(len(delivery_agents)):
        # Simplified distance estimation
        if state["vehicles"][agent_idx]["remaining_capacity"] != next_state["vehicles"][agent_idx]["remaining_capacity"]:
            # Penalize based on distance from current location to parcel
            # (In actual implementation, this would be more sophisticated)
            reward -= 1
    
    # End-of-episode bonus/penalty
    if all(p["assigned"] for p in next_state["parcels"]):
        # Calculate actual total distance
        total_distance = 0
        for agent_idx, agent in enumerate(delivery_agents):
            route = [p for p in parcels if p["assigned_to"] == agent["id"]]
            total_distance += _calculate_route_distance(route, warehouse_coords, return_to_warehouse)
        reward -= total_distance * 0.1  # Penalize total distance
    
    return reward

def _build_solution(state, parcels, delivery_agents):
    """Build solution from final state"""
    routes = [[] for _ in delivery_agents]
    
    # Assign parcels to agents based on assignment in state
    for parcel_idx, parcel_state in enumerate(state["parcels"]):
        if parcel_state["assigned"]:
            agent_idx = parcel_state["assigned_to"]
            routes[agent_idx].append(parcels[parcel_idx])
    
    return routes

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    
    # Extract parameters
    episodes = params.get("episodes", 500)
    epsilon_start = params.get("epsilon_start", 1.0)
    epsilon_end = params.get("epsilon_end", 0.01)
    epsilon_decay = params.get("epsilon_decay", 0.995)
    learning_rate = params.get("learning_rate", 0.001)
    batch_size = params.get("batch_size", 64)
    gamma = params.get("gamma", 0.99)
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
    
    # Calculate normalization constants
    max_capacity = max(agent["capacity_weight"] for agent in delivery_agents_copy) or 1
    max_weight = max(parcel["weight"] for parcel in parcels_copy) or 1
    all_coords = [warehouse_coords] + [p["coordinates_x_y"] for p in parcels_copy]
    max_coord = max(max(abs(x), abs(y)) for x, y in all_coords) or 1
    
    # Initialize DQN components
    n_parcels = len(parcels_copy)
    n_agents = len(delivery_agents_copy)
    n_actions = n_parcels * n_agents
    state_size = n_agents + n_parcels * 4  # Vehicles + parcels features
    
    policy_net = DQN(state_size, n_actions)
    target_net = DQN(state_size, n_actions)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()
    
    optimizer = optim.Adam(policy_net.parameters(), lr=learning_rate)
    replay_buffer = ReplayBuffer(10000)
    
    epsilon = epsilon_start
    best_solution = None
    best_distance = float('inf')
    
    # Training loop
    for episode in range(episodes):
        # Initialize state
        state = {
            "vehicles": [{"remaining_capacity": agent["capacity_weight"]} for agent in delivery_agents_copy],
            "parcels": [{"weight": p["weight"], 
                         "coordinates_x_y": p["coordinates_x_y"],
                         "assigned": False,
                         "assigned_to": None} for p in parcels_copy]
        }
        
        total_reward = 0
        done = False
        
        while not done:
            # Convert state to vector
            state_vector = _state_to_vector(state, max_capacity, max_weight, max_coord)
            
            # Create valid actions mask
            valid_actions_mask = np.zeros(n_actions, dtype=bool)
            for parcel_idx in range(n_parcels):
                if state["parcels"][parcel_idx]["assigned"]:
                    continue
                
                for agent_idx in range(n_agents):
                    if state["vehicles"][agent_idx]["remaining_capacity"] >= parcels_copy[parcel_idx]["weight"]:
                        action_idx = parcel_idx * n_agents + agent_idx
                        valid_actions_mask[action_idx] = True
            
            # Select action
            action = _select_action(state_vector, policy_net, epsilon, n_actions, valid_actions_mask)
            
            # Apply action
            next_state = _apply_action(state, action, parcels_copy, delivery_agents_copy)
            
            # Calculate reward
            reward = _calculate_reward(state, next_state, warehouse_coords, 
                                      return_to_warehouse, parcels_copy, delivery_agents_copy)
            total_reward += reward
            
            # Check termination
            done = all(p["assigned"] for p in next_state["parcels"]) or not any(valid_actions_mask)
            
            # Store transition
            next_state_vector = _state_to_vector(next_state, max_capacity, max_weight, max_coord)
            replay_buffer.push(state_vector, action, reward, next_state_vector, done)
            
            state = next_state
            
            # Train network
            if len(replay_buffer) >= batch_size:
                transitions = replay_buffer.sample(batch_size)
                batch_state, batch_action, batch_reward, batch_next_state, batch_done = zip(*transitions)
                
                batch_state = torch.tensor(batch_state, dtype=torch.float32)
                batch_action = torch.tensor(batch_action, dtype=torch.int64)
                batch_reward = torch.tensor(batch_reward, dtype=torch.float32)
                batch_next_state = torch.tensor(batch_next_state, dtype=torch.float32)
                batch_done = torch.tensor(batch_done, dtype=torch.float32)
                
                # Compute Q values
                current_q = policy_net(batch_state).gather(1, batch_action.unsqueeze(1))
                
                # Compute next Q values
                next_q = target_net(batch_next_state).max(1)[0].detach()
                expected_q = batch_reward + gamma * next_q * (1 - batch_done)
                
                # Compute loss
                loss = F.mse_loss(current_q.squeeze(), expected_q)
                
                # Optimize model
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        
        # Update target network
        if episode % 10 == 0:
            target_net.load_state_dict(policy_net.state_dict())
        
        # Decay epsilon
        epsilon = max(epsilon_end, epsilon * epsilon_decay)
        
        # Track best solution
        if done:
            routes = _build_solution(state, parcels_copy, delivery_agents_copy)
            total_distance = sum(_calculate_route_distance(route, warehouse_coords, return_to_warehouse) 
                             for route in routes)
            
            if total_distance < best_distance:
                best_distance = total_distance
                best_solution = routes
    
    # Prepare results
    if best_solution is None:
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
            "total_weight": sum(p["weight"] for p in route),
            "capacity_weight": agent["capacity_weight"],
            "total_distance": round(route_distance, 2),
        })
    
    # Identify unassigned parcels
    unassigned_parcels = [p for p in parcels if p["id"] not in assigned_parcel_ids]
    
    status = "success" if not unassigned_parcels else "warning"
    message = "Deep Q-Network optimization completed."
    if unassigned_parcels:
        message += f" {len(unassigned_parcels)} parcel(s) could not be assigned due to capacity constraints."
    
    return {
        "status": status,
        "message": message,
        "optimised_routes": optimised_routes,
        "unassigned_parcels": [p["id"] for p in unassigned_parcels],
        "unassigned_parcels_details": unassigned_parcels
    }