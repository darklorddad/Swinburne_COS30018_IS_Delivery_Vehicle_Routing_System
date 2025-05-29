# DVRS Optimisation Script: OpenRouter LLM Optimizer
import math
import copy
import json
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
def _build_llm_prompt(warehouse_coords, parcels, delivery_agents, return_to_warehouse_flag):
    """Constructs the prompt for the LLM."""
    prompt_lines = [
        "You are a vehicle routing problem (VRP) solver. Your task is to assign parcels to delivery agents to form optimal delivery routes.",
        "Constraints:",
        "- Each agent has a maximum weight capacity.",
        "- The total weight of parcels assigned to an agent must not exceed its capacity.",
        "- Each parcel should be delivered by at most one agent.",
        f"- All routes start at the warehouse located at {warehouse_coords}.",
    ]
    if return_to_warehouse_flag:
        prompt_lines.append("- All routes must end back at the warehouse after the last delivery.")
    else:
        prompt_lines.append("- Routes end at the last delivered parcel's location.")
    
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

    # Build the prompt
    prompt_content = _build_llm_prompt(warehouse_coords, all_parcels_list, delivery_agents_list, return_to_warehouse)

    print(prompt_content)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
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

    optimised_routes = []
    llm_assigned_parcels_ids = set()
    
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
        
        # Try to parse the LLM string output as JSON
        try:
            # The LLM might sometimes wrap the JSON in backticks or add other text
            if llm_output_str.startswith("```json"):
                llm_output_str = llm_output_str[len("```json"):].strip()
            if llm_output_str.endswith("```"):
                llm_output_str = llm_output_str[:-len("```")].strip()
            
            llm_solution = json.loads(llm_output_str)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM JSON response: {e}. Raw response: '{llm_output_str}'"
            return {
                "status": "error", "message": error_msg, "optimised_routes": [],
                "unassigned_parcels": [p["id"] for p in all_parcels_list],
                "unassigned_parcels_details": all_parcels_list
            }

        llm_assignments = llm_solution.get("assignments", [])
        
        for assignment in llm_assignments:
            agent_id = assignment.get("agent_id")
            parcel_ids_in_order = assignment.get("parcels_in_route_order", [])

            if not agent_id or agent_id not in agents_map:
                # LLM provided an invalid agent_id, skip this assignment
                continue 
            
            agent_config = agents_map[agent_id]
            current_route_parcels_details = []
            current_route_total_weight = 0
            valid_assignment = True

            for parcel_id in parcel_ids_in_order:
                if parcel_id not in parcels_map:
                    # LLM provided an invalid parcel_id, this part of route is problematic
                    # For simplicity, we might skip the whole agent assignment or just this parcel
                    valid_assignment = False; break 
                
                parcel_obj = parcels_map[parcel_id]
                if parcel_id in llm_assigned_parcels_ids: # Parcel already assigned by LLM to another route
                    valid_assignment = False; break

                current_route_parcels_details.append(copy.deepcopy(parcel_obj))
                current_route_total_weight += parcel_obj["weight"]
            
            if not valid_assignment: continue # Skip this agent if any parcel was invalid/re-assigned

            # Check capacity constraint (LLM might make mistakes)
            if current_route_total_weight > agent_config["capacity_weight"]:
                # LLM violated capacity. These parcels become unassigned.
                # (Alternative: try to partially assign, but simpler to mark all as unassigned from this LLM route)
                continue # Skip this agent's assignment

            # If valid and within capacity
            for p_detail in current_route_parcels_details:
                 llm_assigned_parcels_ids.add(p_detail["id"])

            route_stop_ids = ["Warehouse"] + [p["id"] for p in current_route_parcels_details]
            route_stop_coordinates = [list(warehouse_coords)] + [list(p["coordinates_x_y"]) for p in current_route_parcels_details]

            if return_to_warehouse and current_route_parcels_details: # only add if parcels exist
                route_stop_ids.append("Warehouse")
                route_stop_coordinates.append(list(warehouse_coords))
            elif not current_route_parcels_details and return_to_warehouse: # Empty route, but returns
                route_stop_ids.append("Warehouse")
                route_stop_coordinates.append(list(warehouse_coords))


            total_dist = _calculate_route_distance(current_route_parcels_details, warehouse_coords, return_to_warehouse)

            optimised_routes.append({
                "agent_id": agent_id,
                "parcels_assigned_ids": [p["id"] for p in current_route_parcels_details],
                "parcels_assigned_details": current_route_parcels_details,
                "route_stop_ids": route_stop_ids,
                "route_stop_coordinates": route_stop_coordinates,
                "total_weight": current_route_total_weight,
                "capacity_weight": agent_config["capacity_weight"],
                "total_distance": round(total_dist, 2),
            })
        
        # Identify unassigned parcels based on LLM's explicit list and our validation
        final_unassigned_parcels_ids = set(p["id"] for p in all_parcels_list) - llm_assigned_parcels_ids
        # Also add parcels LLM explicitly said were unassigned, if not already caught
        if "unassigned_parcel_ids" in llm_solution:
            for pid in llm_solution["unassigned_parcel_ids"]:
                if pid in parcels_map: # ensure it's a valid parcel id
                     final_unassigned_parcels_ids.add(pid)


        final_unassigned_parcels_details = [parcels_map[pid] for pid in final_unassigned_parcels_ids if pid in parcels_map]
        
        return {
            "status": "success" if not final_unassigned_parcels_ids else "warning",
            "message": f"OpenRouter LLM optimisation completed using {llm_model}. " + (f"{len(final_unassigned_parcels_ids)} parcel(s) unassigned." if final_unassigned_parcels_ids else "All parcels assigned."),
            "optimised_routes": optimised_routes,
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