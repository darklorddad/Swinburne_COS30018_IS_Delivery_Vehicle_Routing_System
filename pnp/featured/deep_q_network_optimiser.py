import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import torch.nn.functional as F

# --- DQN Model and Replay Buffer ---
class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 256) # Increased layer size
        self.fc3 = nn.Linear(256, 128) # Increased layer size
        self.fc4 = nn.Linear(128, output_size)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return self.fc4(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

# --- Optimisation Script Interface ---
def get_params_schema():
    return {
        "parameters": [
            {
                "name": "episodes", "label": "Training Episodes", "type": "integer",
                "default": 200, "min": 50, "max": 2000, "step": 50, # Reduced default for faster demo
                "help": "Number of training episodes for the DQN agent."
            },
            {
                "name": "epsilon_start", "label": "Initial Epsilon (Exploration)", "type": "float",
                "default": 1.0, "min": 0.1, "max": 1.0, "step": 0.05,
                "help": "Starting value for epsilon in epsilon-greedy exploration."
            },
            {
                "name": "epsilon_end", "label": "Final Epsilon", "type": "float",
                "default": 0.05, "min": 0.01, "max": 0.2, "step": 0.01, # Increased min slightly
                "help": "Minimum value for epsilon."
            },
            {
                "name": "epsilon_decay_rate", "label": "Epsilon Decay Rate", "type": "float",
                "default": 0.99, "min": 0.9, "max": 0.999, "step": 0.001, # Renamed from epsilon_decay
                "help": "Multiplicative factor for decaying epsilon."
            },
            {
                "name": "learning_rate", "label": "Learning Rate (Adam)", "type": "float",
                "default": 0.0005, "min": 0.00001, "max": 0.01, "step": 0.00005, # Adjusted step
                "help": "Learning rate for the Adam optimizer."
            },
            {
                "name": "batch_size", "label": "Batch Size for Training", "type": "integer",
                "default": 32, "min": 16, "max": 128, "step": 16, # Reduced default
                "help": "Number of experiences to sample from replay buffer for training."
            },
            {
                "name": "gamma_discount_factor", "label": "Discount Factor (γ)", "type": "float",
                "default": 0.95, "min": 0.8, "max": 0.999, "step": 0.005, # Renamed from gamma
                "help": "Discount factor for future rewards."
            },
            {
                "name": "target_update_frequency", "label": "Target Network Update Frequency", "type": "integer",
                "default": 10, "min": 1, "max": 100, "step": 1,
                "help": "Update target network every N episodes."
            },
            {
                "name": "replay_buffer_capacity", "label": "Replay Buffer Capacity", "type": "integer",
                "default": 5000, "min": 1000, "max": 50000, "step": 1000, # Reduced default
                "help": "Maximum size of the experience replay buffer."
            },
            {
                "name": "time_per_distance_unit", "label": "Time per distance unit (min)", "type": "float",
                "default": 1.0, "min": 0.1, "step": 0.1,
                "help": "Minutes taken to travel one unit of distance (for scheduling)."
            },
            {
                "name": "default_service_time", "label": "Default service time (min)", "type": "integer",
                "default": 10, "min": 0, "help": "Default time spent at each parcel stop (for scheduling)."
            },
             { # Added from other optimisers for consistency in scheduling
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries (for scheduling)."
            }
        ]
    }

# --- Helper Functions ---
def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_schedule_and_feasibility(ordered_parcel_objects, agent_config, warehouse_coords, params):
    """
    Calculates detailed schedule for a given sequence of parcels for a specific agent.
    Checks feasibility against agent's capacity, operating hours, and parcel time windows.
    """
    time_per_dist_unit = params.get("time_per_distance_unit", 1.0)
    default_service_time = params.get("default_service_time", 10)
    should_return_to_warehouse = params.get("return_to_warehouse", True)

    agent_capacity = agent_config["capacity_weight"]
    agent_op_start = agent_config["operating_hours_start"]
    agent_op_end = agent_config["operating_hours_end"]

    route_stop_ids = ["Warehouse"]
    route_stop_coordinates = [list(warehouse_coords)]
    arrival_times = [round(agent_op_start)]
    departure_times = [round(agent_op_start)]

    current_time = agent_op_start
    current_location = list(warehouse_coords)
    current_load = 0
    total_distance = 0.0

    if not ordered_parcel_objects: # Agent has no parcels
        if should_return_to_warehouse: # Empty route still needs WH start/end if returning
             pass # Already initialized with WH start/end for times
        else: # No return, no parcels - effectively no route
            return True, { # Feasible empty route
                "route_stop_ids": [], "route_stop_coordinates": [],
                "arrival_times": [], "departure_times": [],
                "total_distance": 0.0, "total_load": 0.0
            }


    for p_obj in ordered_parcel_objects:
        p_coords = p_obj["coordinates_x_y"]
        p_weight = p_obj["weight"]
        p_service_time = p_obj.get("service_time", default_service_time)
        p_tw_open = p_obj.get("time_window_open", 0)
        p_tw_close = p_obj.get("time_window_close", 1439) # Default to full day

        current_load += p_weight
        if current_load > agent_capacity: return False, {} # Exceeds capacity

        dist_to_parcel = _calculate_distance(current_location, p_coords)
        total_distance += dist_to_parcel
        travel_time = dist_to_parcel * time_per_dist_unit
        
        arrival_at_parcel = current_time + travel_time
        service_start_time = max(arrival_at_parcel, p_tw_open)

        if service_start_time > p_tw_close: return False, {} # Arrived too late or TW too restrictive
        
        service_end_time = service_start_time + p_service_time
        if service_end_time > p_tw_close: return False, {} # Service ends too late for parcel TW
        if service_end_time > agent_op_end: return False, {} # Service ends too late for agent

        route_stop_ids.append(p_obj["id"])
        route_stop_coordinates.append(list(p_coords))
        arrival_times.append(round(arrival_at_parcel))
        departure_times.append(round(service_end_time))
        
        current_time = service_end_time
        current_location = list(p_coords)

    if should_return_to_warehouse:
        dist_to_warehouse = _calculate_distance(current_location, warehouse_coords)
        total_distance += dist_to_warehouse
        travel_time_to_wh = dist_to_warehouse * time_per_dist_unit
        arrival_at_warehouse_final = current_time + travel_time_to_wh

        if arrival_at_warehouse_final > agent_op_end: return False, {} # Return to WH too late

        route_stop_ids.append("Warehouse")
        route_stop_coordinates.append(list(warehouse_coords))
        arrival_times.append(round(arrival_at_warehouse_final))
        departure_times.append(round(arrival_at_warehouse_final))
    
    # If not returning to warehouse, the last departure time is from the last parcel
    # and the stops/coords don't include final WH. total_distance is also up to last parcel.

    return True, {
        "route_stop_ids": route_stop_ids, "route_stop_coordinates": route_stop_coordinates,
        "arrival_times": arrival_times, "departure_times": departure_times,
        "total_distance": round(total_distance, 2), "total_load": current_load
    }


def _get_initial_state(parcels_cfg, agents_cfg):
    state = {
        "parcels_status": [ # 0: unassigned, 1: assigned
            0 for _ in parcels_cfg
        ],
        "parcels_assigned_to_agent_idx": [ # -1 if unassigned
            -1 for _ in parcels_cfg
        ],
        "agents_remaining_capacity": [
            agent["capacity_weight"] for agent in agents_cfg
        ],
        # Potentially add current agent locations if routing was part of DQN state
        # For now, DQN focuses on assignment.
    }
    return state

def _state_to_vector(state, num_parcels, num_agents, max_cap_overall, max_weight_overall, max_coord_overall, parcels_config_info):
    """Normalized state vector for DQN input."""
    # Features:
    # 1. For each parcel: assigned_status (0/1), assigned_agent_idx_norm (-1 to 1 after norm), weight_norm, x_norm, y_norm
    # 2. For each agent: remaining_capacity_norm
    
    # Parcel features
    parcel_features = []
    for i in range(num_parcels):
        parcel_features.append(state["parcels_status"][i]) # 0 or 1
        
        # Normalize assigned_agent_idx: map [-1, num_agents-1] to roughly [-1, 1]
        # -1 (unassigned) -> -1. Others (0 to N-1) -> map to [0,1] then scale to avoid -1 overlap if needed
        # Simpler: if assigned, agent_idx / (num_agents-1) if num_agents > 1 else 0.5. If unassigned, -1.
        # For NN, better to use one-hot encoding for assigned agent, or separate flags.
        # Here, let's use a simple normalized version of agent_idx, and status flag.
        assigned_agent_norm = -1.0 
        if state["parcels_assigned_to_agent_idx"][i] != -1:
            if num_agents > 1:
                assigned_agent_norm = state["parcels_assigned_to_agent_idx"][i] / (num_agents - 1.0)
            elif num_agents == 1: # Only one agent
                assigned_agent_norm = 0.0 # or 1.0, to distinguish from -1

        parcel_features.append(assigned_agent_norm)
        parcel_features.append(parcels_config_info[i]["weight"] / max_weight_overall if max_weight_overall > 0 else 0)
        parcel_features.append(parcels_config_info[i]["coordinates_x_y"][0] / max_coord_overall if max_coord_overall > 0 else 0)
        parcel_features.append(parcels_config_info[i]["coordinates_x_y"][1] / max_coord_overall if max_coord_overall > 0 else 0)

    # Agent features
    agent_features = [cap / max_cap_overall if max_cap_overall > 0 else 0 for cap in state["agents_remaining_capacity"]]
    
    # Combine and flatten
    flat_vector = np.array(parcel_features + agent_features, dtype=np.float32)
    return flat_vector


def _select_action(state_vector, policy_net, epsilon, n_total_actions, valid_actions_mask):
    if random.random() < epsilon:
        # Exploration: choose random valid action
        valid_indices = [i for i, valid in enumerate(valid_actions_mask) if valid]
        return random.choice(valid_indices) if valid_indices else -1 # -1 if no valid action
    
    # Exploitation
    with torch.no_grad():
        state_tensor = torch.from_numpy(state_vector).unsqueeze(0)
        q_values = policy_net(state_tensor).squeeze(0).numpy()
        
        masked_q = q_values.copy()
        masked_q[~valid_actions_mask] = -np.inf # Mask out invalid actions
        
        if np.all(np.isinf(masked_q)): # All actions are invalid or lead to -inf
            return -1 # No valid action
        return np.argmax(masked_q)


def _apply_action_and_get_reward(current_state, action_idx, parcels_cfg, agents_cfg, params):
    """
    Applies action, calculates reward for this step.
    Action: assign parcel_idx_in_list to agent_idx_in_list.
    Returns (next_state, reward, done)
    """
    num_parcels = len(parcels_cfg)
    num_agents = len(agents_cfg)

    parcel_to_assign_idx = action_idx // num_agents
    agent_to_assign_to_idx = action_idx % num_agents

    next_state = copy.deepcopy(current_state)
    reward = 0
    
    # Check if action is valid in current_state context (should be pre-filtered by mask, but double check)
    if next_state["parcels_status"][parcel_to_assign_idx] == 1: # Already assigned
        reward = -100 # Heavy penalty for trying to reassign (should not happen with mask)
        done = all(s == 1 for s in next_state["parcels_status"])
        return next_state, reward, done

    parcel_obj = parcels_cfg[parcel_to_assign_idx]
    if next_state["agents_remaining_capacity"][agent_to_assign_to_idx] >= parcel_obj["weight"]:
        # Valid assignment
        next_state["parcels_status"][parcel_to_assign_idx] = 1
        next_state["parcels_assigned_to_agent_idx"][parcel_to_assign_idx] = agent_to_assign_to_idx
        next_state["agents_remaining_capacity"][agent_to_assign_to_idx] -= parcel_obj["weight"]
        reward = 20 # Positive reward for successful assignment
    else:
        # Invalid assignment (capacity) - should be caught by mask
        reward = -50 # Penalty for attempting infeasible assignment
    
    done = all(s == 1 for s in next_state["parcels_status"])
    
    # Bonus for completing all assignments
    if done:
        reward += 100
        # Further reward/penalty based on quality of full solution could be added here,
        # but that requires building and evaluating routes, which is costly per step.
        # Current reward is step-based. Final solution quality check is done outside training loop.

    return next_state, reward, done


def _optimize_model(policy_net, target_net, optimizer, replay_buffer, batch_size, gamma_discount):
    if len(replay_buffer) < batch_size:
        return
    
    transitions = replay_buffer.sample(batch_size)
    batch_state_vec, batch_action, batch_reward, batch_next_state_vec, batch_done = zip(*transitions)
    
    batch_state_t = torch.from_numpy(np.array(batch_state_vec))
    batch_action_t = torch.from_numpy(np.array(batch_action)).long().unsqueeze(1) # Ensure it's Long and correct shape
    batch_reward_t = torch.from_numpy(np.array(batch_reward)).float()
    batch_next_state_t = torch.from_numpy(np.array(batch_next_state_vec))
    batch_done_t = torch.from_numpy(np.array(batch_done)).float() # 0.0 for not done, 1.0 for done

    # Q(s_t, a_t)
    current_q_values = policy_net(batch_state_t).gather(1, batch_action_t)
    
    # max_a Q_target(s_{t+1}, a)
    # Use .detach() to prevent gradients from flowing into the target network
    next_q_values_target_net = target_net(batch_next_state_t).max(1)[0].detach()
    
    # Expected Q values: r + gamma * max_a Q_target(s_{t+1}, a) if not done, else r
    expected_q_values = batch_reward_t + (gamma_discount * next_q_values_target_net * (1 - batch_done_t))
    
    loss = F.mse_loss(current_q_values.squeeze(), expected_q_values)
    
    optimizer.zero_grad()
    loss.backward()
    # Gradient clipping can be useful: torch.nn.utils.clip_grad_norm_(policy_net.parameters(), max_norm=1.0)
    optimizer.step()

def _build_final_routes_from_state(final_state, parcels_cfg, agents_cfg, warehouse_coords, params):
    """
    Constructs DVRS-compatible routes from the final assignment state.
    Includes sequencing and scheduling.
    """
    optimised_routes_output = []
    assigned_parcels_globally_ids = set()

    for agent_idx, agent_config in enumerate(agents_cfg):
        agent_assigned_parcels_indices = [
            p_idx for p_idx, assigned_agent_idx in enumerate(final_state["parcels_assigned_to_agent_idx"])
            if assigned_agent_idx == agent_idx
        ]
        
        if not agent_assigned_parcels_indices:
            continue # No parcels for this agent

        agent_parcels_objects = [parcels_cfg[i] for i in agent_assigned_parcels_indices]

        # --- Simple Sequencing: Maintain original relative order or NN ---
        # For now, use a very simple greedy nearest-neighbor from warehouse/last parcel
        # This is a placeholder; a better TSP heuristic should be used for robust sequencing.
        
        current_route_parcels_ordered = []
        if agent_parcels_objects:
            remaining_p_for_agent = list(agent_parcels_objects)
            current_loc_for_nn = warehouse_coords
            
            while remaining_p_for_agent:
                best_p = None
                min_dist = float('inf')
                for p_cand in remaining_p_for_agent:
                    dist = _calculate_distance(current_loc_for_nn, p_cand["coordinates_x_y"])
                    if dist < min_dist:
                        min_dist = dist
                        best_p = p_cand
                
                if best_p:
                    current_route_parcels_ordered.append(best_p)
                    current_loc_for_nn = best_p["coordinates_x_y"]
                    remaining_p_for_agent.remove(best_p)
                else: # Should not happen if remaining_p_for_agent is not empty
                    break
        
        # Calculate schedule and check feasibility for the *specific agent*
        is_feasible, route_details = _calculate_route_schedule_and_feasibility(
            current_route_parcels_ordered, agent_config, warehouse_coords, params
        )

        if is_feasible and current_route_parcels_ordered: # Ensure route is not empty and feasible
            for p_obj in current_route_parcels_ordered:
                assigned_parcels_globally_ids.add(p_obj["id"])
            
            optimised_routes_output.append({
                "agent_id": agent_config["id"],
                "parcels_assigned_ids": [p["id"] for p in current_route_parcels_ordered],
                "parcels_assigned_details": [copy.deepcopy(p) for p in current_route_parcels_ordered],
                "route_stop_ids": route_details["route_stop_ids"],
                "route_stop_coordinates": route_details["route_stop_coordinates"],
                "total_weight": route_details["total_load"],
                "capacity_weight": agent_config["capacity_weight"],
                "total_distance": route_details["total_distance"],
                "arrival_times": route_details["arrival_times"],
                "departure_times": route_details["departure_times"]
            })
    
    unassigned_parcels_details = [
        copy.deepcopy(p) for p_idx, p in enumerate(parcels_cfg)
        if final_state["parcels_status"][p_idx] == 0 or p["id"] not in assigned_parcels_globally_ids
    ]
    unassigned_parcels_ids = [p["id"] for p in unassigned_parcels_details]

    return optimised_routes_output, unassigned_parcels_ids, unassigned_parcels_details


# --- Main Optimisation Function ---
def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels_cfg_orig = config_data.get("parcels", [])
    agents_cfg_orig = config_data.get("delivery_agents", [])

    # Extract DQN parameters
    num_episodes = params.get("episodes", 200)
    epsilon_start = params.get("epsilon_start", 1.0)
    epsilon_end = params.get("epsilon_end", 0.05)
    epsilon_decay_rate = params.get("epsilon_decay_rate", 0.99)
    learning_rate = params.get("learning_rate", 0.0005)
    batch_size = params.get("batch_size", 32)
    gamma_discount = params.get("gamma_discount_factor", 0.95)
    target_update_freq = params.get("target_update_frequency", 10)
    buffer_capacity = params.get("replay_buffer_capacity", 5000)

    if not parcels_cfg_orig or not agents_cfg_orig:
        return {
            "status": "warning", "message": "No parcels or delivery agents for DQN.",
            "optimised_routes": [], 
            "unassigned_parcels": [p["id"] for p in parcels_cfg_orig],
            "unassigned_parcels_details": copy.deepcopy(parcels_cfg_orig)
        }
    
    parcels_cfg = copy.deepcopy(parcels_cfg_orig)
    agents_cfg = copy.deepcopy(agents_cfg_orig)
    num_parcels = len(parcels_cfg)
    num_agents = len(agents_cfg)

    # Normalization constants
    max_cap = max(a["capacity_weight"] for a in agents_cfg) if agents_cfg else 1
    max_weight = max(p["weight"] for p in parcels_cfg) if parcels_cfg else 1
    all_coords_flat = [c for p in parcels_cfg for c in p["coordinates_x_y"]] + list(warehouse_coords)
    max_coord = max(abs(c) for c in all_coords_flat) if all_coords_flat else 1
    
    # DQN setup
    # State vector size: num_parcels * (status + assigned_agent_norm + weight_norm + x_norm + y_norm) + num_agents * (cap_norm)
    # status=1, assigned_agent_norm=1, weight=1, x=1, y=1 -> 5 features per parcel
    state_size = (num_parcels * 5) + num_agents 
    action_size = num_parcels * num_agents # Assign parcel P to agent A

    policy_net = DQN(state_size, action_size)
    target_net = DQN(state_size, action_size)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.Adam(policy_net.parameters(), lr=learning_rate)
    replay_buffer = ReplayBuffer(buffer_capacity)
    epsilon = epsilon_start

    best_final_state_overall = None
    min_unassigned_parcels_overall = num_parcels + 1
    
    episode_rewards = []

    for episode in range(num_episodes):
        current_state = _get_initial_state(parcels_cfg, agents_cfg)
        episode_total_reward = 0
        done = False
        
        # Max steps per episode to prevent infinite loops if goal is hard to reach
        max_steps_per_episode = num_parcels * 2 # Allow some mistakes/re-exploration
        for step in range(max_steps_per_episode):
            state_vector = _state_to_vector(current_state, num_parcels, num_agents, max_cap, max_weight, max_coord, parcels_cfg)
            
            # Valid actions mask: True if parcel unassigned AND agent has capacity
            valid_actions_mask = np.zeros(action_size, dtype=bool)
            can_assign_more = False
            for p_idx in range(num_parcels):
                if current_state["parcels_status"][p_idx] == 0: # If parcel is unassigned
                    for a_idx in range(num_agents):
                        if current_state["agents_remaining_capacity"][a_idx] >= parcels_cfg[p_idx]["weight"]:
                            valid_actions_mask[p_idx * num_agents + a_idx] = True
                            can_assign_more = True
            
            if not can_assign_more: # No valid moves left or all assigned
                done = True
                # Check if all parcels are assigned
                if not all(s == 1 for s in current_state["parcels_status"]):
                     episode_total_reward -= 200 # Penalty if stuck with unassigned parcels

            if done:
                break

            action = _select_action(state_vector, policy_net, epsilon, action_size, valid_actions_mask)
            if action == -1 : # No valid action selected
                done = True
                if not all(s == 1 for s in current_state["parcels_status"]):
                    episode_total_reward -= 150 # Penalty if stuck with unassigned parcels and no valid moves
                break 

            next_state, reward_step, step_done = _apply_action_and_get_reward(current_state, action, parcels_cfg, agents_cfg, params)
            episode_total_reward += reward_step
            done = step_done # Update overall done flag

            next_state_vector = _state_to_vector(next_state, num_parcels, num_agents, max_cap, max_weight, max_coord, parcels_cfg)
            replay_buffer.push(state_vector, action, reward_step, next_state_vector, done)
            
            current_state = next_state
            _optimize_model(policy_net, target_net, optimizer, replay_buffer, batch_size, gamma_discount)

            if done:
                break
        
        episode_rewards.append(episode_total_reward)
        num_unassigned_in_episode_end_state = sum(1 for s in current_state["parcels_status"] if s == 0)

        if num_unassigned_in_episode_end_state < min_unassigned_parcels_overall:
            min_unassigned_parcels_overall = num_unassigned_in_episode_end_state
            best_final_state_overall = copy.deepcopy(current_state)
        elif num_unassigned_in_episode_end_state == min_unassigned_parcels_overall:
            # If same number unassigned, could add a secondary metric (e.g. estimated distance)
            # For now, just update if it's the first time we hit this low number or by chance
            best_final_state_overall = copy.deepcopy(current_state)


        if (episode + 1) % target_update_freq == 0:
            target_net.load_state_dict(policy_net.state_dict())
        
        epsilon = max(epsilon_end, epsilon * epsilon_decay_rate)

        # Optional: Print progress
        # if (episode + 1) % 10 == 0:
        #     print(f"Episode {episode+1}/{num_episodes}, Avg Reward (last 10): {np.mean(episode_rewards[-10:]):.2f}, Epsilon: {epsilon:.3f}, Min Unassigned: {min_unassigned_parcels_overall}")


    if best_final_state_overall is None: # Should not happen if episodes > 0
        best_final_state_overall = _get_initial_state(parcels_cfg, agents_cfg) # Fallback to initial

    # Build final routes using the best assignment state found
    opt_routes, unassigned_ids, unassigned_details = _build_final_routes_from_state(
        best_final_state_overall, parcels_cfg, agents_cfg, warehouse_coords, params
    )
    
    message = f"DQN optimization completed. Episodes: {num_episodes}. Best found solution has {len(unassigned_ids)} unassigned parcels."
    status_type = "success" if not unassigned_ids else "warning"
    if not opt_routes and parcels_cfg:
        message = "DQN optimization completed, but no feasible routes could be constructed from assignments for any agent."
        status_type = "error"


    return {
        "status": status_type,
        "message": message,
        "optimised_routes": opt_routes,
        "unassigned_parcels": unassigned_ids,
        "unassigned_parcels_details": unassigned_details
    }