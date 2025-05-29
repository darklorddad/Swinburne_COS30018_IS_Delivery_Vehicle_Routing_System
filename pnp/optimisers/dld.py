# DVRS Optimisation Script: OpenRouter LLM Optimizer
import math
import copy
import json
import random
import re
import requests # Ensure 'requests' library is installed (pip install requests)

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "openrouter_api_key",
                "label": "OpenRouter API Key",
                "type": "string", # In a real UI, this should be treated as a sensitive/password field
                "default": "",
                "help": "Your OpenRouter API Key (e.g., sk-or-...). Required."
            },
            {
                "name": "llm_model",
                "label": "LLM Model",
                "type": "selectbox",
                "default": "deepseek/deepseek-chat-v3-0324:free",
                "options": [
                    "deepseek/deepseek-chat-v3-0324:free",
                    "openai/gpt-3.5-turbo",
                    "openai/gpt-4o-mini",
                    "google/gemini-flash-1.5",
                    "mistralai/mistral-7b-instruct:free",
                    "anthropic/claude-3-haiku",
                    "deepseek/deepseek-r1-0528:free",
                    # Add other models you might want to use
                ],
                "help": "Select the LLM model to use from OpenRouter."
            },
            {
                "name": "max_tokens",
                "label": "Max Tokens for Response",
                "type": "integer",
                "default": 3000,
                "min": 200,
                "max": 8192, # Model dependent, but a general upper bound
                "step": 100,
                "help": "Maximum number of tokens for the LLM response. Adjust based on problem size."
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "float",
                "default": 0.2, # Lower for more deterministic routing
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "help": "Controls randomness. Lower values (e.g., 0.2) make output more deterministic and focused."
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse after deliveries."
            },
            {
                "name": "http_referer",
                "label": "HTTP Referer (Optional)",
                "type": "string",
                "default": "<YOUR_SITE_URL>", # Replace with your actual site URL or a placeholder
                "help": "Optional. Your site URL for rankings on openrouter.ai."
            },
            {
                "name": "x_title",
                "label": "X-Title (Optional)",
                "type": "string",
                "default": "<YOUR_PROJECT_NAME>", # Replace with your actual project name or a placeholder
                "help": "Optional. Your site name for rankings on openrouter.ai."
            }
        ]
    }

# --- Helper Functions (copied from other optimisers for consistency) ---
def _calculate_distance(coord1, coord2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_distance(route_parcels, warehouse_coords, return_to_warehouse):
    """Calculate total distance for a list of parcel objects in a route."""
    if not route_parcels:
        return 0.0
    
    # Distance from warehouse to first parcel
    total_distance = _calculate_distance(warehouse_coords, route_parcels[0]["coordinates_x_y"])
    
    # Distance between consecutive parcels
    for i in range(len(route_parcels) - 1):
        total_distance += _calculate_distance(route_parcels[i]["coordinates_x_y"], route_parcels[i+1]["coordinates_x_y"])
    
    # Distance from last parcel back to warehouse
    if return_to_warehouse and route_parcels:
        total_distance += _calculate_distance(route_parcels[-1]["coordinates_x_y"], warehouse_coords)
    
    return total_distance

def _calculate_route_weight(route_parcels):
    """Calculate total weight for a list of parcel objects in a route."""
    return sum(parcel["weight"] for parcel in route_parcels)

# --- LLM Specific Helper Functions ---
def _build_llm_prompt(warehouse_coords, parcels, delivery_agents, return_to_warehouse_flag, additional_notes=None):
    """Constructs the prompt for the LLM, including any pre-computation notes."""
    prompt_lines = [
        "You are an expert vehicle routing problem (VRP) solver. Your task is to assign parcels to delivery agents to form optimal delivery routes, ensuring all constraints are met.",
        "Key Objective: Assign AS MANY PARCELS AS POSSIBLE while adhering to all constraints. If a parcel cannot be assigned, it should be explicitly listed as unassigned.",
        "",
        "Constraints:",
        "- Each agent has a maximum weight capacity. The total weight of parcels assigned to an agent MUST NOT exceed this capacity.",
        "- Each parcel should be delivered by at most one agent.",
        f"- All routes start at the warehouse located at {warehouse_coords}.",
    ]
    if return_to_warehouse_flag:
        prompt_lines.append("- All routes must end back at the warehouse after the last delivery.")
    else:
        prompt_lines.append("- Routes end at the last delivered parcel's location.")
    
    if additional_notes:
        prompt_lines.append("\nImportant Notes Based on Pre-analysis:")
        for note in additional_notes:
            prompt_lines.append(f"- {note}")
        prompt_lines.append("")

    prompt_lines.extend([
        "Input Data:", 
        f"Warehouse Coordinates: {warehouse_coords}",
        "Parcels (ID, Coordinates [x,y], Weight):"
    ])
    for p in parcels:
        prompt_lines.append(f"- {p['id']}: {p['coordinates_x_y']}, Weight: {p['weight']}")
    
    prompt_lines.append("Delivery Agents (ID, Capacity_Weight):")
    for da in delivery_agents:
        prompt_lines.append(f"- {da['id']}: Capacity: {da['capacity_weight']}")
        
    prompt_lines.extend([
        "",
        "Task: Assign parcels to agents and determine the order of delivery for each agent.",
        "Objective: Minimize total travel distance across all routes while respecting all constraints. Ensure all possible parcels are assigned if capacity allows.",
        "",
        "Output Format: Provide your solution as a single JSON object. The JSON object should have two top-level keys: 'assignments' and 'unassigned_parcel_ids'.",
        "'assignments' should be a list of objects, where each object represents an agent's route and has:",
        "  - 'agent_id': The ID of the delivery agent (string).",
        "  - 'parcels_in_route_order': A list of parcel IDs (strings) in the order they should be delivered.",
        "'unassigned_parcel_ids' should be a list of parcel IDs (strings) that could not be assigned to any agent due to capacity or other constraints.",
        "",
        "Example of desired JSON output format:",
        '''
        {
          "assignments": [
            {
              "agent_id": "DA01",
              "parcels_in_route_order": ["P001", "P003"]
            },
            {
              "agent_id": "DA02",
              "parcels_in_route_order": ["P002"]
            }
          ],
          "unassigned_parcel_ids": ["P004", "P005"]
        }
        ''',
        "Please provide only the JSON object as your response, without any preceding or succeeding text."
    ])
    return "\n".join(prompt_lines)

def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    all_parcels_list = config_data.get("parcels", [])
    delivery_agents_list = config_data.get("delivery_agents", [])

    # Extract parameters
    api_key = params.get("openrouter_api_key")
    llm_model = params.get("llm_model", "deepseek/deepseek-chat-v3-0324:free")
    max_tokens = params.get("max_tokens", 3000)
    temperature = params.get("temperature", 0.2)
    return_to_warehouse = params.get("return_to_warehouse", True)
    http_referer = params.get("http_referer", "")
    x_title = params.get("x_title", "")

    if not api_key:
        return {
            "status": "error",
            "message": "OpenRouter API Key is missing. Please provide it in the parameters.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in all_parcels_list],
            "unassigned_parcels_details": all_parcels_list
        }

    if not all_parcels_list:
        return {
            "status": "success",
            "message": "No parcels to deliver.",
            "optimised_routes": [],
            "unassigned_parcels": [],
            "unassigned_parcels_details": []
        }
    
    if not delivery_agents_list:
        return {
            "status": "error",
            "message": "No delivery agents available to deliver parcels.",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in all_parcels_list],
            "unassigned_parcels_details": all_parcels_list
        }

    # Create maps for easy lookup
    parcels_map = {p["id"]: p for p in all_parcels_list}
    agents_map = {a["id"]: a for a in delivery_agents_list}

    # --- Pre-LLM checks and prompt notes ---
    prompt_notes = []
    total_parcel_weight = sum(p['weight'] for p in all_parcels_list)
    total_agent_capacity = sum(a['capacity_weight'] for a in delivery_agents_list)

    if total_parcel_weight > total_agent_capacity:
        prompt_notes.append(f"Warning: Total parcel weight ({total_parcel_weight}) exceeds total available agent capacity ({total_agent_capacity}). It will be impossible to assign all parcels.")
    
    max_single_agent_capacity = max(a['capacity_weight'] for a in delivery_agents_list) if delivery_agents_list else 0
    for p_check in all_parcels_list:
        if p_check['weight'] > max_single_agent_capacity:
            prompt_notes.append(f"Warning: Parcel {p_check['id']} (weight {p_check['weight']}) is heavier than any single agent's maximum capacity ({max_single_agent_capacity}) and cannot be assigned by any single agent.")

    prompt_content = _build_llm_prompt(warehouse_coords, all_parcels_list, delivery_agents_list, return_to_warehouse, prompt_notes)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if x_title:
        headers["X-Title"] = x_title
        
    payload = {
        "model": llm_model,
        "messages": [{"role": "user", "content": prompt_content}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False # Ensure we get the full response at once
    }

    # Initialize tracking structures
    final_routes_map = {agent_id: [] for agent_id in agents_map.keys()}
    final_routes_weights = {agent_id: 0 for agent_id in agents_map.keys()}
    script_confirmed_assigned_parcel_ids = set()
    optimised_routes_output = []
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=120 # Increased timeout for potentially long LLM responses
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        response_data = response.json()
        
        if not response_data.get("choices") or not response_data["choices"][0].get("message") or not response_data["choices"][0]["message"].get("content"):
            raise ValueError("LLM response is not in the expected format or is empty.")

        llm_output_str = response_data["choices"][0]["message"]["content"]
        
        json_str_to_parse = ""
        # Try to extract JSON robustly
        json_match_multiline = re.search(r"```json\s*(\{.*?\})\s*```", llm_output_str, re.DOTALL)
        json_match_inline = re.search(r"```json\s*(\{.*\})\s*```", llm_output_str) # for single line JSON within backticks
        
        if json_match_multiline:
            json_str_to_parse = json_match_multiline.group(1)
        elif json_match_inline:
            json_str_to_parse = json_match_inline.group(1)
        else:
            first_brace = llm_output_str.find('{')
            last_brace = llm_output_str.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_str_to_parse = llm_output_str[first_brace : last_brace+1]
            else:
                raise ValueError(f"Could not isolate a JSON block from LLM response. Raw: '{llm_output_str}'")
        
        try:
            llm_solution = json.loads(json_str_to_parse)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM JSON response: {e}. Raw response: '{llm_output_str}'"
            return {
                "status": "error", "message": error_msg, "optimised_routes": [],
                "unassigned_parcels": [p["id"] for p in all_parcels_list],
                "unassigned_parcels_details": all_parcels_list
            }

        # --- Pass 1: Process and Validate LLM's assignments ---
        llm_proposed_assignments = llm_solution.get("assignments", [])
        llm_temp_assigned_ids_this_pass = set() # Track PIDs assigned by LLM in this pass to detect LLM self-duplication

        for assignment in llm_proposed_assignments:
            agent_id = assignment.get("agent_id")
            parcel_ids_llm_order = assignment.get("parcels_in_route_order", [])

            if not agent_id or agent_id not in agents_map: continue # Invalid agent_id

            current_agent_route_parcels_temp = []
            current_agent_route_weight_temp = 0
            is_current_llm_route_valid = True

            for p_id_llm in parcel_ids_llm_order:
                if p_id_llm not in parcels_map: is_current_llm_route_valid = False; break # Invalid parcel_id
                if p_id_llm in llm_temp_assigned_ids_this_pass: is_current_llm_route_valid = False; break # LLM assigned same parcel twice

                parcel_obj = parcels_map[p_id_llm]
                current_agent_route_parcels_temp.append(parcel_obj)
                current_agent_route_weight_temp += parcel_obj["weight"]
                llm_temp_assigned_ids_this_pass.add(p_id_llm)
            
            if not is_current_llm_route_valid: # Problem with this route, revert any temp PIDs
                for p_obj_revert in current_agent_route_parcels_temp:
                    llm_temp_assigned_ids_this_pass.discard(p_obj_revert["id"])
                continue

            if current_agent_route_weight_temp > agents_map[agent_id]["capacity_weight"]: # LLM violated capacity
                for p_obj_revert in current_agent_route_parcels_temp:
                     llm_temp_assigned_ids_this_pass.discard(p_obj_revert["id"])
                continue
            
            # LLM's route for this agent is valid: commit it
            final_routes_map[agent_id] = [copy.deepcopy(p) for p in current_agent_route_parcels_temp]
            final_routes_weights[agent_id] = current_agent_route_weight_temp
            for p_obj_commit in current_agent_route_parcels_temp:
                script_confirmed_assigned_parcel_ids.add(p_obj_commit["id"])
        
        # --- Pass 2: Greedy Repair for remaining unassigned parcels ---
        parcels_needing_repair = [p for p in all_parcels_list if p["id"] not in script_confirmed_assigned_parcel_ids]
        parcels_needing_repair.sort(key=lambda p: p["weight"], reverse=True) # Try to fit heavier ones first

        for parcel_to_repair in parcels_needing_repair:
            agent_ids_for_repair = list(agents_map.keys())
            random.shuffle(agent_ids_for_repair) # Try agents in random order for this parcel

            for agent_id_repair in agent_ids_for_repair:
                agent_cap = agents_map[agent_id_repair]["capacity_weight"]
                if final_routes_weights[agent_id_repair] + parcel_to_repair["weight"] <= agent_cap:
                    final_routes_map[agent_id_repair].append(copy.deepcopy(parcel_to_repair))
                    final_routes_weights[agent_id_repair] += parcel_to_repair["weight"]
                    script_confirmed_assigned_parcel_ids.add(parcel_to_repair["id"])
                    break # Parcel assigned in repair

        # --- Construct final output ---
        optimised_routes_output = []
        for agent_id_out, route_parcels_list_out in final_routes_map.items():
            agent_detail_out = agents_map[agent_id_out]
            parcels_assigned_ids_out = [p["id"] for p in route_parcels_list_out]
            
            route_stop_ids_out = ["Warehouse"]
            route_stop_coords_out = [list(warehouse_coords)]

            if route_parcels_list_out: # If agent has parcels
                route_stop_ids_out.extend(parcels_assigned_ids_out)
                route_stop_coords_out.extend([list(p["coordinates_x_y"]) for p in route_parcels_list_out])
            
            if return_to_warehouse: # Always add warehouse at end if true, even for empty routes
                route_stop_ids_out.append("Warehouse")
                route_stop_coords_out.append(list(warehouse_coords))
            elif not route_parcels_list_out and not return_to_warehouse: # Empty, no return -> just warehouse
                pass # Already ["Warehouse"]

            total_dist_out = _calculate_route_distance(route_parcels_list_out, warehouse_coords, return_to_warehouse)

            optimised_routes_output.append({
                "agent_id": agent_id_out,
                "parcels_assigned_ids": parcels_assigned_ids_out,
                "parcels_assigned_details": route_parcels_list_out,
                "route_stop_ids": route_stop_ids_out,
                "route_stop_coordinates": route_stop_coords_out,
                "total_weight": final_routes_weights[agent_id_out],
                "capacity_weight": agent_detail_out["capacity_weight"],
                "total_distance": round(total_dist_out, 2),
            })
        
        final_unassigned_parcels_ids_set = set(p["id"] for p in all_parcels_list) - script_confirmed_assigned_parcel_ids
        
        final_unassigned_parcels_details_list = [parcels_map[pid] for pid in final_unassigned_parcels_ids_set if pid in parcels_map]
        
        return {
            "status": "success" if not final_unassigned_parcels_ids else "warning",
            "message": f"OpenRouter LLM optimisation completed using {llm_model}. " + (f"{len(final_unassigned_parcels_ids)} parcel(s) unassigned." if final_unassigned_parcels_ids else "All parcels assigned."),
            "optimised_routes": optimised_routes_output,
            "unassigned_parcels": list(final_unassigned_parcels_ids),
            "unassigned_parcels_details": final_unassigned_parcels_details
        }

    except requests.exceptions.RequestException as e:
        message = f"API request failed: {e}"
    except ValueError as e: # Catch our own ValueErrors from response parsing
        message = f"LLM response processing error: {e}"
    except Exception as e:
        message = f"An unexpected error occurred: {type(e).__name__} - {e}"

    # Fallback for any error
    return {
        "status": "error",
        "message": message,
        "optimised_routes": [],
        "unassigned_parcels": [p["id"] for p in all_parcels_list],
        "unassigned_parcels_details": all_parcels_list
    }
