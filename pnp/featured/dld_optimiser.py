import json
import math
import copy
import requests # For synchronous HTTP requests
import time # For retry delay

def get_params_schema():
    return {
        "parameters": [
            {
                "name": "llm_model_name", 
                "label": "LLM Model Name",
                "type": "string",
                "default": "default-model",
                "help": "The LLM model to use for routing optimization."
            },
            {
                "name": "llm_api_key",
                "label": "LLM API Key",
                "type": "string",
                "default": "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",
                "help": "API key for LLM service access."
            },
            {
                "name": "llm_temperature",
                "label": "LLM Temperature",
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "help": "Controls randomness. Lower is more deterministic."
            },
            {
                "name": "llm_max_tokens", 
                "label": "LLM Max Tokens",
                "type": "integer",
                "default": 2048,
                "min": 256, 
                "max": 4096,
                "help": "Maximum tokens in LLM response."
            },
            {
                "name": "time_per_distance_unit",
                "label": "Time per distance unit",
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "help": "Minutes per distance unit for scheduling."
            },
            {
                "name": "default_service_time",
                "label": "Default service time",
                "type": "integer",
                "default": 10,
                "min": 1,
                "help": "Default minutes per delivery stop."
            },
            {
                "name": "return_to_warehouse",
                "label": "Return to warehouse",
                "type": "boolean",
                "default": True,
                "help": "Whether vehicles must return to warehouse."
            }
        ]
    }

def _calculate_distance(coord1, coord2):
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def _build_llm_prompt(warehouse_coords, parcels, delivery_agents):
    prompt = "You are an expert logistics planner. Your task is to solve a Vehicle Routing Problem (VRP).\n"
    prompt += "You need to assign parcels to delivery agents and suggest an order for deliveries for each agent.\n"
    prompt += "Adhere to agent capacity constraints and try to respect parcel time windows and agent operating hours, though final scheduling will be done by another system.\n\n"

    prompt += "VRP Instance Data:\n"
    prompt += f"1. Warehouse Coordinates: {warehouse_coords}\n\n"

    prompt += "2. Parcels:\n"
    if not parcels:
        prompt += "  - No parcels to deliver.\n"
    for p in parcels:
        prompt += f"  - ID: {p['id']}, Coords: {p['coordinates_x_y']}, Weight: {p['weight']}, "
        prompt += f"TimeWindow: [{p.get('time_window_open', 'N/A')}-{p.get('time_window_close', 'N/A')}], "
        prompt += f"ServiceTime: {p.get('service_time', 'N/A')} min\n"
    prompt += "\n"

    prompt += "3. Delivery Agents:\n"
    if not delivery_agents:
        prompt += "  - No delivery agents available.\n"
    for da in delivery_agents:
        prompt += f"  - ID: {da['id']}, Capacity (weight): {da['capacity_weight']}, "
        prompt += f"OperatingHours: [{da.get('operating_hours_start', 'N/A')}-{da.get('operating_hours_end', 'N/A')}] min from midnight\n"
    prompt += "\n"

    prompt += "Output Instructions:\n"
    prompt += "Please provide your solution in JSON format. The JSON should have two top-level keys: 'optimised_routes' and 'unassigned_parcels_ids'.\n"
    prompt += "'optimised_routes' should be a list of route objects. Each route object must have:\n"
    prompt += "  - 'agent_id': The ID of the delivery agent.\n"
    prompt += "  - 'parcels_assigned_ids': A list of parcel IDs assigned to this agent, in the suggested delivery order.\n"
    prompt += "'unassigned_parcels_ids' should be a list of IDs of parcels that could not be assigned.\n\n"
    prompt += "Example JSON Output Format:\n"
    prompt += "```json\n"
    prompt += "{\n"
    prompt += '  "optimised_routes": [\n'
    prompt += "    {\n"
    prompt += '      "agent_id": "DA01",\n'
    prompt += '      "parcels_assigned_ids": ["P001", "P003"]\n'
    prompt += "    },\n"
    prompt += "    {\n"
    prompt += '      "agent_id": "DA02",\n'
    prompt += '      "parcels_assigned_ids": ["P002", "P004"]\n'
    prompt += "    }\n"
    prompt += "  ],\n"
    prompt += '  "unassigned_parcels_ids": ["P005"]\n'
    prompt += "}\n"
    prompt += "```\n\n"
    prompt += "Based on the provided data, generate the VRP solution in the specified JSON format.\n"
    prompt += "Focus on assigning all parcels if possible, respecting agent capacities. The order of parcels within each agent's route should be logical (e.g., somewhat geographically clustered or forming a reasonable path).\n"
    return prompt

def _invoke_llm_sync(api_token, model_name, prompt_content, temperature=0.5, max_tokens=2048):
    if not api_token:
        return {"error": "LLM API key is missing. Please configure it in parameters."}

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "HTTP-Referer": "",
        "X-Title": ""
    }
    body = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_content}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",  # Generic endpoint
            headers=headers,
            json=body,
            timeout=180
        )
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("choices") and \
           len(response_data["choices"]) > 0 and \
           response_data["choices"][0].get("message") and \
           response_data["choices"][0]["message"].get("content"):
            
            llm_content_str = response_data["choices"][0]["message"]["content"]
            
            # Try to extract JSON from markdown code block if present
            if "```json" in llm_content_str:
                try:
                    json_block = llm_content_str.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_block)
                except (IndexError, json.JSONDecodeError) as e_json_block:
                    print(f"LLM: Failed to extract/parse JSON from markdown block: {e_json_block}. Content: {llm_content_str[:300]}")
                    # Fallback to trying to parse the whole string if block extraction fails
            
            # Try to parse the whole content as JSON (if no markdown or block extraction failed)
            try:
                return json.loads(llm_content_str)
            except json.JSONDecodeError as e_json_full:
                print(f"LLM: Response content was not valid JSON: {e_json_full}. Content: {llm_content_str[:300]}")
                return {"error": "LLM response content not valid JSON", "raw_content": llm_content_str}
        else:
            print(f"LLM: Response format unexpected: {response_data}")
            return {"error": "LLM response format unexpected", "raw_response": response_data}

    except requests.exceptions.Timeout:
        print("LLM: API request timed out.")
        return {"error": "API request timed out."}
    except requests.exceptions.RequestException as e:
        print(f"LLM: API request failed: {e}")
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e: # Catch-all for other unexpected errors
        print(f"LLM: Unexpected error during API call: {e}")
        return {"error": f"Unexpected error during LLM API call: {str(e)}"}


def _calculate_route_schedule_and_feasibility(ordered_parcel_objects, agent_config, warehouse_coords, params, parcel_map_for_lookup):
    """
    (Copied and adapted from other optimisers - ensures consistency)
    Calculates detailed schedule for a given sequence of parcels for a specific agent.
    Checks feasibility against agent's capacity, operating hours, and parcel time windows.
    """
    should_return_to_warehouse = params.get("return_to_warehouse", True)
    time_per_dist_unit = params.get("time_per_distance_unit", 1.0)
    default_service_time = params.get("default_service_time", 10)

    agent_capacity = agent_config["capacity_weight"]
    agent_op_start = agent_config.get("operating_hours_start", 0) # Default if missing
    agent_op_end = agent_config.get("operating_hours_end", 1439) # Default if missing

    route_stop_ids = ["Warehouse"]
    route_stop_coordinates = [list(warehouse_coords)]
    arrival_times = [round(agent_op_start)]
    departure_times = [round(agent_op_start)]

    current_time = agent_op_start
    current_location = list(warehouse_coords)
    current_load = 0
    total_distance = 0.0

    if not ordered_parcel_objects:
        if should_return_to_warehouse:
             pass # Already initialized
        else:
            return True, {
                "route_stop_ids": [], "route_stop_coordinates": [],
                "arrival_times": [], "departure_times": [],
                "total_distance": 0.0, "total_load": 0.0
            }

    for p_obj_id in ordered_parcel_objects: # Expecting list of parcel IDs here from LLM
        p_obj = parcel_map_for_lookup.get(p_obj_id)
        if not p_obj:
            print(f"Warning: Parcel ID '{p_obj_id}' from LLM not found in config_data. Skipping.")
            continue # Skip if parcel ID is invalid

        p_coords = p_obj["coordinates_x_y"]
        p_weight = p_obj["weight"]
        p_service_time = p_obj.get("service_time", 10)  # Fixed service time (10 min default)
        p_tw_open = p_obj.get("time_window_open", 0)
        p_tw_close = p_obj.get("time_window_close", 1439)

        current_load += p_weight
        if current_load > agent_capacity: return False, {"reason": f"Exceeded capacity for agent {agent_config['id']}"}

        dist_to_parcel = _calculate_distance(current_location, p_coords)
        total_distance += dist_to_parcel
        travel_time = dist_to_parcel * time_per_dist_unit
        
        arrival_at_parcel = current_time + travel_time
        service_start_time = max(arrival_at_parcel, p_tw_open)

        if service_start_time > p_tw_close: return False, {"reason": f"Service start for {p_obj['id']} after TW close"}
        
        service_end_time = service_start_time + p_service_time
        if service_end_time > p_tw_close: return False, {"reason": f"Service end for {p_obj['id']} after TW close"}
        if service_end_time > agent_op_end: return False, {"reason": f"Service end for {p_obj['id']} after agent op end"}

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

        if arrival_at_warehouse_final > agent_op_end: return False, {"reason": "Return to WH after agent op end"}

        route_stop_ids.append("Warehouse")
        route_stop_coordinates.append(list(warehouse_coords))
        arrival_times.append(round(arrival_at_warehouse_final))
        departure_times.append(round(arrival_at_warehouse_final))
    
    return True, {
        "route_stop_ids": route_stop_ids, "route_stop_coordinates": route_stop_coordinates,
        "arrival_times": arrival_times, "departure_times": departure_times,
        "total_distance": round(total_distance, 2), "total_load": current_load
    }


def run_optimisation(config_data, params):
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    parcels_cfg = config_data.get("parcels", [])
    agents_cfg = config_data.get("delivery_agents", [])

    api_token = "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"
    llm_model = params.get("llm_model_name", "default-model")

    if not parcels_cfg:
        return {
            "status": "success", "message": "No parcels to deliver.",
            "optimised_routes": [], "unassigned_parcels": [], "unassigned_parcels_details": []
        }
    if not agents_cfg:
        return {
            "status": "warning", "message": "No delivery agents available to assign parcels.",
            "optimised_routes": [], "unassigned_parcels": [p["id"] for p in parcels_cfg],
            "unassigned_parcels_details": copy.deepcopy(parcels_cfg)
        }

    prompt = _build_llm_prompt(warehouse_coords, parcels_cfg, agents_cfg)
    
    print("Optimiser: Sending prompt to routing assistant...")
    # print(f"LLM Prompt:\n{prompt[:500]}...\n...\n{prompt[-500:]}") # Log snippet of prompt

    max_retries = 3
    retry_delay = 5  # seconds
    llm_response_data = None
    
    for attempt in range(max_retries):
        try:
            llm_temperature = params.get("llm_temperature", 0.5)
            llm_max_tokens = params.get("llm_max_tokens", 2048)
            llm_response_data = _invoke_llm_sync(api_token, llm_model, prompt, llm_temperature, llm_max_tokens)
            break  # Exit loop if successful
        except Exception as e:
            print(f"LLM API attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                llm_response_data = {"error": f"All {max_retries} attempts failed"}

    if not llm_response_data or "error" in llm_response_data:
        error_msg = llm_response_data["error"]
        raw_content_msg = ""
        if "raw_content" in llm_response_data: # If LLM gave non-JSON text
            raw_content_msg = f" LLM's raw output (partial): '{llm_response_data['raw_content'][:200]}...'"
        elif "raw_response" in llm_response_data: # If API gave completely unexpected structure
             raw_content_msg = f" LLM's raw API response: '{str(llm_response_data['raw_response'])[:200]}...'"
        return {
            "status": "error",
            "message": f"LLM API call failed or returned unusable data: {error_msg}.{raw_content_msg}",
            "optimised_routes": [], "unassigned_parcels": [p["id"] for p in parcels_cfg],
            "unassigned_parcels_details": copy.deepcopy(parcels_cfg)
        }

    # --- Post-process LLM Output ---
    # Extract and validate routes from LLM response
    llm_proposed_routes = llm_response_data.get("optimised_routes", [])
    llm_unassigned_ids = llm_response_data.get("unassigned_parcels_ids", [])
    
    # If LLM response is empty or invalid structure
    if not llm_response_data or not isinstance(llm_response_data, dict):
        return {
            "status": "error",
            "message": "LLM returned empty or invalid response format",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels_cfg],
            "unassigned_parcels_details": copy.deepcopy(parcels_cfg)
        }

    # If routes are missing or not in expected format
    if not isinstance(llm_proposed_routes, list) or not all(isinstance(r, dict) for r in llm_proposed_routes):
        return {
            "status": "error",
            "message": "LLM output 'optimised_routes' was missing or not a list of route objects",
            "optimised_routes": [],
            "unassigned_parcels": [p["id"] for p in parcels_cfg],
            "unassigned_parcels_details": copy.deepcopy(parcels_cfg)
        }


    final_optimised_routes = []
    actually_assigned_parcel_ids = set()
    parcel_map = {p["id"]: p for p in parcels_cfg} # For quick lookup
    agent_map = {a["id"]: a for a in agents_cfg}   # For quick lookup

    for llm_route_proposal in llm_proposed_routes:
        agent_id = llm_route_proposal.get("agent_id")
        proposed_parcel_ids_for_agent = llm_route_proposal.get("parcels_assigned_ids", [])

        if not agent_id or not isinstance(proposed_parcel_ids_for_agent, list):
            print(f"LLM Optimiser: Skipping invalid route proposal from LLM: {llm_route_proposal}")
            continue
        
        agent_config = agent_map.get(agent_id)
        if not agent_config:
            print(f"LLM Optimiser: Agent ID '{agent_id}' from LLM not found in config. Skipping route.")
            llm_unassigned_ids.extend(p_id for p_id in proposed_parcel_ids_for_agent if p_id not in llm_unassigned_ids)
            continue

        # The LLM provides parcel_ids. We need to ensure they are valid and then schedule them.
        # The order from LLM is taken as the sequence.
        
        # Filter out invalid parcel IDs just in case
        valid_parcel_ids_for_route = [pid for pid in proposed_parcel_ids_for_agent if pid in parcel_map]
        parcels_to_schedule_for_agent = [parcel_map[pid] for pid in valid_parcel_ids_for_route]


        is_feasible, route_details = _calculate_route_schedule_and_feasibility(
            valid_parcel_ids_for_route, # Pass IDs, scheduler will look up full objects
            agent_config,
            warehouse_coords,
            params,
            parcel_map # Pass the map for the scheduler to use
        )

        if is_feasible and route_details.get("route_stop_ids") and len(route_details["route_stop_ids"]) > (1 if params.get("return_to_warehouse") else 0) : # Has at least one parcel if not returning, or WH start/end
            # Ensure that route_details parcels (excluding Warehouse) are added to actually_assigned_parcel_ids
            # route_details["route_stop_ids"] includes 'Warehouse'
            scheduled_parcel_ids_in_route = [stop_id for stop_id in route_details["route_stop_ids"] if stop_id != "Warehouse"]
            
            final_optimised_routes.append({
                "agent_id": agent_id,
                "parcels_assigned_ids": scheduled_parcel_ids_in_route,
                "parcels_assigned_details": [copy.deepcopy(parcel_map[pid]) for pid in scheduled_parcel_ids_in_route],
                "route_stop_ids": route_details["route_stop_ids"],
                "route_stop_coordinates": route_details["route_stop_coordinates"],
                "total_weight": route_details["total_load"],
                "capacity_weight": agent_config["capacity_weight"],
                "total_distance": route_details["total_distance"],
                "arrival_times": route_details["arrival_times"],
                "departure_times": route_details["departure_times"]
            })
            for pid in scheduled_parcel_ids_in_route:
                actually_assigned_parcel_ids.add(pid)
        else:
            # If route proposed by LLM for this agent is not feasible after Python scheduling,
            # add its parcels to the unassigned list.
            print(f"LLM Optimiser: Route for agent {agent_id} proposed by LLM was infeasible after scheduling. Reason: {route_details.get('reason', 'Unknown')}. Parcels {valid_parcel_ids_for_route} will be unassigned.")
            for p_id in valid_parcel_ids_for_route:
                if p_id not in llm_unassigned_ids: # Avoid duplicates if LLM already marked them
                    llm_unassigned_ids.append(p_id)


    # Consolidate unassigned parcels: those LLM didn't assign + those whose routes became infeasible
    final_unassigned_ids_set = set(llm_unassigned_ids)
    for p_cfg in parcels_cfg:
        if p_cfg["id"] not in actually_assigned_parcel_ids:
            final_unassigned_ids_set.add(p_cfg["id"])
    
    final_unassigned_ids_list = sorted(list(final_unassigned_ids_set))
    final_unassigned_details = [copy.deepcopy(parcel_map[pid]) for pid in final_unassigned_ids_list if pid in parcel_map]
    
    # Build final output message with more detailed status
    if not final_optimised_routes:
        message = "LLM optimisation failed - no valid routes could be constructed"
        status = "error"
    else:
        message = f"LLM-based optimisation completed successfully with {len(final_optimised_routes)} routes"
        if final_unassigned_ids_list:
            message += f" ({len(final_unassigned_ids_list)} parcels unassigned)"
            status = "warning" 
        else:
            status = "success"
    
    return {
        "status": status,
        "message": message,
        "optimised_routes": final_optimised_routes,
        "unassigned_parcels": final_unassigned_ids_list,
        "unassigned_parcels_details": final_unassigned_details
    }
