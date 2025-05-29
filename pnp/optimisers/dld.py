# pnp/optimisers/openrouter_optimiser.py
import requests
import json
import math
import copy # For deepcopying

# Constants for OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# It's good practice to include these, even if optional, for better tracking on OpenRouter
HTTP_REFERER = "http://localhost/pnp-optimizer" # Placeholder, customize if needed
X_TITLE = "PNP Route Optimiser (OpenRouter)"    # Placeholder, customize if needed

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "openrouter_api_key",
                "label": "OpenRouter API Key",
                "type": "text", # Ideally "password" or "secret" if UI supports
                "default": "",
                "help": "Your OpenRouter API key. Get one from openrouter.ai. Keep this secret."
            },
            {
                "name": "openrouter_model",
                "label": "OpenRouter Model",
                "type": "selectbox",
                "default": "deepseek/deepseek-chat-v3-0324:free", 
                "options": [
                    "deepseek/deepseek-chat-v3-0324:free",
                    "mistralai/mistral-7b-instruct:free",
                    "google/gemma-7b-it:free",
                    "openai/gpt-3.5-turbo",
                    "anthropic/claude-3-haiku",
                    "anthropic/claude-3-sonnet",
                    # Add more models as desired from openrouter.ai/models
                ],
                "help": "Select the LLM model to use from OpenRouter."
            },
            {
                "name": "max_tokens",
                "label": "Max Tokens",
                "type": "integer",
                "default": 2048,
                "min": 256,
                "max": 8192, 
                "step": 256,
                "help": "Maximum number of tokens for the LLM's response. Adjust based on model and problem complexity."
            },
            {
                "name": "temperature",
                "label": "Temperature",
                "type": "float",
                "default": 0.2, # Lower for more deterministic VRP-like tasks
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "help": "Controls randomness. Lower values (e.g., 0.0-0.3) are more deterministic and recommended for this task."
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to Warehouse",
                "type": "boolean",
                "default": True,
                "help": "Instruct the LLM that vehicles must return to the warehouse after their last delivery."
            },
            {
                "name": "custom_system_prompt",
                "label": "Custom System Prompt (Advanced)",
                "type": "textarea",
                "default": "",
                "help": "Override the default system prompt. Use the placeholder {output_format_instructions} to include JSON formatting guidance, or provide your own."
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    """Calculates Euclidean distance between two points."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _calculate_route_distance(route_parcels, warehouse_coords, return_to_warehouse_flag):
    """Calculate total distance for a list of parcel objects in a route."""
    if not route_parcels:
        return 0.0
    
    current_pos = warehouse_coords
    total_distance = 0.0
    
    # Distance from warehouse to first parcel (or first point in route)
    total_distance += _calculate_distance(current_pos, route_parcels[0]["coordinates_x_y"])
    current_pos = route_parcels[0]["coordinates_x_y"]
    
    # Distances between parcels in the route
    for i in range(len(route_parcels) - 1):
        total_distance += _calculate_distance(current_pos, route_parcels[i+1]["coordinates_x_y"])
        current_pos = route_parcels[i+1]["coordinates_x_y"]
    
    # Distance from last parcel back to warehouse (if applicable)
    if return_to_warehouse_flag and route_parcels: # route_parcels check ensures current_pos is last parcel
        total_distance += _calculate_distance(current_pos, warehouse_coords)
    
    return total_distance

def _calculate_route_weight(route_parcels):
    """Calculate total weight for a list of parcel objects in a route."""
    return sum(p["weight"] for p in route_parcels)

def _construct_prompt_messages(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels = config_data.get("parcels", [])
    delivery_agents = config_data.get("delivery_agents", [])
    return_to_warehouse_flag = params.get("return_to_warehouse", True)

    output_format_instructions = """
Please provide your solution in a VALID JSON format. The JSON object should have two top-level keys: "routes" and "unassigned_parcels".
- "routes" must be a list of route objects. Each route object represents a single delivery agent's assignments and must contain:
  - "agent_id": (string) The ID of the delivery agent (must match one of the provided agent IDs).
  - "parcel_ids": (list of strings) A list of parcel IDs assigned to this agent, in the order they should be visited. An empty list `[]` indicates no parcels are assigned to this agent.
- "unassigned_parcels" must be a list of strings, where each string is the ID of a parcel that could not be assigned to any agent. If all parcels are assigned, this should be an empty list `[]`.

Example of the expected JSON output structure:
```json
{
  "routes": [
    {
      "agent_id": "DA01",
      "parcel_ids": ["P001", "P003"]
    },
    {
      "agent_id": "DA02",
      "parcel_ids": ["P002"]
    }
  ],
  "unassigned_parcels": ["P004", "P005"]
}


IMPORTANT CONSTRAINTS AND GUIDELINES:

Agent Capacity: The sum of weights of parcels in parcel_ids for an agent MUST NOT exceed that agent's capacity_weight.

Parcel Uniqueness: Each parcel ID can appear at most once across all parcel_ids lists and the unassigned_parcels list. A parcel cannot be both assigned and unassigned, nor can it be assigned to multiple agents.

Existing IDs: All agent_id and parcel_id values in your response MUST correspond to IDs provided in the problem description. Do not invent new IDs.

Completeness: Account for ALL parcels provided in the problem. Either assign them to an agent or list them in unassigned_parcels.

Empty Routes: If an agent is not used, include them in the "routes" list with an empty parcel_ids list (e.g., {"agent_id": "DA03", "parcel_ids": []}).
"""

warehouse_return_instruction_text = "All routes must also end at the warehouse after the last delivery." if return_to_warehouse_flag else "Routes DO NOT need to return to the warehouse after the last delivery."

default_system_prompt_template = f"""
You are an expert Vehicle Routing Problem (VRP) solver. Your task is to assign a list of parcels to a list of delivery agents and determine the sequence of deliveries for each agent.
You must strictly adhere to the following constraints:

Capacity Constraint: The total weight of parcels assigned to any single agent cannot exceed their stated capacity_weight.

Parcel Delivery: Attempt to deliver all parcels. If some parcels cannot be delivered due to capacity or other constraints, they must be listed in the unassigned_parcels section of your response.

Warehouse Operations: All delivery routes start at the warehouse. {warehouse_return_instruction_text}

Objective: Your primary goal is to assign all parcels while respecting agent capacities. A secondary goal is to minimize the total travel distance implicitly through efficient routing.

Output Format:
{{output_format_instructions}}
"""

custom_prompt_text = params.get("custom_system_prompt", "").strip()
if custom_prompt_text:
    system_prompt = custom_prompt_text.replace("{output_format_instructions}", output_format_instructions)
else:
    system_prompt = default_system_prompt_template.replace("{output_format_instructions}", output_format_instructions)
    
user_prompt_content = "Please solve the following Vehicle Routing Problem based on the rules and output format specified in the system prompt.\n\n"
user_prompt_content += f"Problem Data:\n"
user_prompt_content += f"Warehouse Location (coordinates_x_y): {warehouse_coords}\n\n"

user_prompt_content += "Parcels to be Delivered (id, coordinates_x_y, weight):\n"
if not parcels:
    user_prompt_content += "  No parcels to deliver.\n"
for p in parcels:
    user_prompt_content += f"  - ID: {p['id']}, Coords: {p['coordinates_x_y']}, Weight: {p['weight']}\n"
user_prompt_content += "\n"

user_prompt_content += "Available Delivery Agents (id, capacity_weight):\n"
if not delivery_agents:
    user_prompt_content += "  No delivery agents available.\n"
for da in delivery_agents:
    user_prompt_content += f"  - ID: {da['id']}, Capacity: {da['capacity_weight']}\n"
user_prompt_content += "\n"

user_prompt_content += "Remember to provide your complete solution in the specified JSON format."

return [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt_content}
]

def run_optimisation(config_data, params):
api_key = params.get("openrouter_api_key")
if not api_key:
return {
"status": "error", "message": "OpenRouter API Key is missing. Please provide it in the parameters.",
"optimised_routes": [],
"unassigned_parcels": [p["id"] for p in config_data.get("parcels", [])],
"unassigned_parcels_details": config_data.get("parcels", [])
}

# Prepare data maps
all_parcels_input = config_data.get("parcels", [])
all_agents_input = config_data.get("delivery_agents", [])
warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
return_to_warehouse_flag = params.get("return_to_warehouse", True)

all_parcels_map = {p["id"]: p for p in all_parcels_input}
all_agents_map = {da["id"]: da for da in all_agents_input}

# Handle edge cases: no agents or no parcels
if not all_agents_input:
    return {
        "status": "error", "message": "No delivery agents available. Cannot assign parcels.",
        "optimised_routes": [], 
        "unassigned_parcels": [p["id"] for p in all_parcels_input],
        "unassigned_parcels_details": all_parcels_input
    }

if not all_parcels_input:
    empty_routes = []
    for agent_id, agent_data in all_agents_map.items():
        route_stops = [warehouse_coords]
        if return_to_warehouse_flag: route_stops.append(warehouse_coords)
        empty_routes.append({
            "agent_id": agent_id, "parcels_assigned_ids": [], "parcels_assigned_details": [],
            "route_stop_ids": ["Warehouse", "Warehouse"] if return_to_warehouse_flag else ["Warehouse"],
            "route_stop_coordinates": route_stops,
            "total_weight": 0, "capacity_weight": agent_data["capacity_weight"], "total_distance": 0.0,
        })
    return {
        "status": "success", "message": "No parcels to deliver. All agents have empty routes.",
        "optimised_routes": empty_routes, "unassigned_parcels": [], "unassigned_parcels_details": []
    }

messages = _construct_prompt_messages(config_data, params)

api_payload = {
    "model": params.get("openrouter_model", "deepseek/deepseek-chat-v3-0324:free"),
    "messages": messages,
    "max_tokens": params.get("max_tokens", 2048),
    "temperature": params.get("temperature", 0.2),
    "stream": False 
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": HTTP_REFERER, 
    "X-Title": X_TITLE
}

raw_llm_content = ""
try:
    response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(api_payload), timeout=180) # 180s timeout
    response.raise_for_status()
    
    llm_response_json = response.json()
    if not llm_response_json.get("choices") or not llm_response_json["choices"][0].get("message") or \
       not llm_response_json["choices"][0]["message"].get("content"):
        raise ValueError("LLM response structure is invalid or content is missing.")

    raw_llm_content = llm_response_json["choices"][0]["message"]["content"]
    
    # Attempt to clean and parse JSON (LLMs sometimes wrap in markdown)
    cleaned_content = raw_llm_content.strip()
    if cleaned_content.startswith("```json"):
        cleaned_content = cleaned_content[7:]
    if cleaned_content.startswith("```"): # Handles cases like ```\njson...
        cleaned_content = cleaned_content[3:]
    if cleaned_content.endswith("```"):
        cleaned_content = cleaned_content[:-3]
    
    parsed_solution_from_llm = json.loads(cleaned_content.strip())

except requests.exceptions.Timeout:
    return {"status": "error", "message": "API request timed out.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
except requests.exceptions.RequestException as e:
    return {"status": "error", "message": f"API Request Error: {e}", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
except json.JSONDecodeError:
    return {"status": "error", "message": f"Failed to parse LLM JSON response. Raw content: '{raw_llm_content}'", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
except ValueError as e: # Custom validation errors
    return {"status": "error", "message": str(e), "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
except Exception as e: 
    return {"status": "error", "message": f"An unexpected error occurred: {e}. Raw content: '{raw_llm_content}'", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

# --- Process and Validate LLM's Solution ---
optimised_routes_output = []
parcels_assigned_by_llm_ids = set()

if not isinstance(parsed_solution_from_llm.get("routes"), list):
    return {"status": "error", "message": "LLM response 'routes' field is missing or not a list.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

processed_agent_ids_from_llm = set()

for llm_route_data in parsed_solution_from_llm["routes"]:
    if not isinstance(llm_route_data, dict):
        return {"status": "error", "message": f"Invalid route item (not a dict): {llm_route_data}", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

    agent_id = llm_route_data.get("agent_id")
    if not agent_id or agent_id not in all_agents_map:
        return {"status": "error", "message": f"LLM response contains invalid or unknown agent_id: '{agent_id}'.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
    if agent_id in processed_agent_ids_from_llm:
         return {"status": "error", "message": f"LLM response contains duplicate agent_id: '{agent_id}'.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
    processed_agent_ids_from_llm.add(agent_id)
    
    agent_config = all_agents_map[agent_id]
    current_route_parcels_details = []
    
    llm_parcel_ids_for_route = llm_route_data.get("parcel_ids", [])
    if not isinstance(llm_parcel_ids_for_route, list):
        return {"status": "error", "message": f"Parcel IDs for agent {agent_id} is not a list: {llm_parcel_ids_for_route}", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

    for parcel_id in llm_parcel_ids_for_route:
        if parcel_id not in all_parcels_map:
            return {"status": "error", "message": f"LLM assigned unknown parcel_id '{parcel_id}' to agent '{agent_id}'.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
        if parcel_id in parcels_assigned_by_llm_ids:
             return {"status": "error", "message": f"LLM assigned parcel_id '{parcel_id}' to multiple routes/agents.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
        
        current_route_parcels_details.append(all_parcels_map[parcel_id])
        parcels_assigned_by_llm_ids.add(parcel_id)

    # Validate capacity and calculate actuals based on our data
    current_route_total_weight = _calculate_route_weight(current_route_parcels_details)
    if current_route_total_weight > agent_config["capacity_weight"]:
        return {"status": "error", "message": f"LLM solution for agent '{agent_id}' exceeds capacity. Assigned: {current_route_total_weight} kg, Capacity: {agent_config['capacity_weight']} kg.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

    route_dist = _calculate_route_distance(current_route_parcels_details, warehouse_coords, return_to_warehouse_flag)
    
    route_stop_ids = ["Warehouse"] + [p["id"] for p in current_route_parcels_details]
    route_stop_coordinates = [warehouse_coords] + [p["coordinates_x_y"] for p in current_route_parcels_details]
    
    if return_to_warehouse_flag:
        route_stop_ids.append("Warehouse")
        route_stop_coordinates.append(warehouse_coords)
    
    optimised_routes_output.append({
        "agent_id": agent_id,
        "parcels_assigned_ids": [p["id"] for p in current_route_parcels_details],
        "parcels_assigned_details": current_route_parcels_details,
        "route_stop_ids": route_stop_ids,
        "route_stop_coordinates": route_stop_coordinates,
        "total_weight": current_route_total_weight,
        "capacity_weight": agent_config["capacity_weight"],
        "total_distance": round(route_dist, 2),
    })

# Add empty routes for any agents in config but not mentioned by LLM
for agent_id_cfg, agent_data_cfg in all_agents_map.items():
    if agent_id_cfg not in processed_agent_ids_from_llm:
        route_stops_coords_empty = [warehouse_coords]
        if return_to_warehouse_flag: route_stops_coords_empty.append(warehouse_coords)
        optimised_routes_output.append({
            "agent_id": agent_id_cfg, "parcels_assigned_ids": [], "parcels_assigned_details": [],
            "route_stop_ids": ["Warehouse", "Warehouse"] if return_to_warehouse_flag else ["Warehouse"],
            "route_stop_coordinates": route_stops_coords_empty,
            "total_weight": 0, "capacity_weight": agent_data_cfg["capacity_weight"], "total_distance": 0.0,
        })

# Determine final unassigned parcels based on what LLM actually assigned
final_unassigned_parcel_ids = set(all_parcels_map.keys()) - parcels_assigned_by_llm_ids

# Validate LLM's list of unassigned_parcels against our derived list
llm_declared_unassigned_ids = set(parsed_solution_from_llm.get("unassigned_parcels", []))
if not isinstance(parsed_solution_from_llm.get("unassigned_parcels"), list):
     return {"status": "error", "message": "LLM response 'unassigned_parcels' field is not a list.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

for pid in llm_declared_unassigned_ids:
    if pid not in all_parcels_map:
        return {"status": "error", "message": f"LLM listed unknown parcel_id '{pid}' as unassigned.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}
    if pid in parcels_assigned_by_llm_ids: # Should have been caught, but good check
        return {"status": "error", "message": f"LLM listed parcel_id '{pid}' as unassigned but also assigned it.", "optimised_routes": [], "unassigned_parcels": [p["id"] for p in all_parcels_input], "unassigned_parcels_details": all_parcels_input}

# Reconcile: if LLM said a parcel was unassigned, but it wasn't in our final_unassigned_parcel_ids (meaning we thought it was assigned),
# this indicates an inconsistency. Trust our derived final_unassigned_parcel_ids.
# Also, if LLM missed declaring an unassigned parcel, our list will catch it.

unassigned_details_final = [all_parcels_map[pid] for pid in final_unassigned_parcel_ids]

status_message = "OpenRouter LLM optimisation processed."
result_status = "success"
if final_unassigned_parcel_ids:
    status_message += f" {len(final_unassigned_parcel_ids)} parcel(s) are unassigned."
    result_status = "warning"

# Final check: Ensure all original parcels are either in an agent's route or in the final unassigned list
all_original_parcel_ids = set(all_parcels_map.keys())
accounted_for_parcels = parcels_assigned_by_llm_ids.union(final_unassigned_parcel_ids)
if all_original_parcel_ids != accounted_for_parcels:
    missing_from_accounting = all_original_parcel_ids - accounted_for_parcels
    over_accounted = accounted_for_parcels - all_original_parcel_ids # Should be empty due to earlier checks
    return {"status": "error", 
            "message": f"Internal accounting error: Mismatch in parcel tracking. Missing: {missing_from_accounting}, Over-accounted: {over_accounted}", 
            "optimised_routes": optimised_routes_output, # Return what we have
            "unassigned_parcels": sorted(list(final_unassigned_parcel_ids)), 
            "unassigned_parcels_details": unassigned_details_final}


return {
    "status": result_status,
    "message": status_message,
    "optimised_routes": optimised_routes_output,
    "unassigned_parcels": sorted(list(final_unassigned_parcel_ids)),
    "unassigned_parcels_details": unassigned_details_final
}
