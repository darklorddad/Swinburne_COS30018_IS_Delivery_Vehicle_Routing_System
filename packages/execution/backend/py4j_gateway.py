from py4j.java_gateway import JavaGateway, GatewayParameters, Py4JNetworkError
import json

def connect_to_gateway(py4j_address="127.0.0.1", py4j_port=25333):
    try:
        return JavaGateway(gateway_parameters=GatewayParameters(
            address=py4j_address, 
            port=py4j_port, 
            auto_convert=True
        )), None
    except Py4JNetworkError as e:
        return None, f"Py4J connection failed: {str(e)}. Check JADE GatewayServer"
    except Exception as e:
        return None, f"Error connecting to Py4J gateway: {str(e)}"

def create_agent(gateway, agent_name, agent_class, agent_args):
    if not gateway:
        return False, "Py4J Gateway not available"

    try:
        java_args_array = gateway.new_array(gateway.jvm.java.lang.String, len(agent_args))
        for i, arg_str in enumerate(agent_args):
            java_args_array[i] = arg_str
            
        result_message = gateway.entry_point.createAgentByController(agent_name, agent_class, java_args_array)
        
        if "error" in result_message.lower() or "fail" in result_message.lower():
            return False, f"JADE reported error: {result_message}"
        return True, result_message
    except Py4JNetworkError as e:
        return False, f"Network error creating agent: {str(e)}"
    except Exception as e:
        return False, f"Error creating agent: {str(e)}"

def create_mra_agent(gateway, agent_name, agent_class, config_data):
    try:
        agent_args = [json.dumps(config_data)]
        return create_agent(gateway, agent_name, agent_class, agent_args)
    except Exception as e:
        return False, f"Error serializing config data: {str(e)}"

def create_da_agent(gateway, agent_name, agent_class, agent_config):
    try:
        agent_args = [json.dumps(agent_config)]
        return create_agent(gateway, agent_name, agent_class, agent_args)
    except Exception as e:
        return False, f"Error serializing agent config: {str(e)}"

def send_optimisation_results(gateway, mra_name, results):
    if not gateway:
        return False, "Py4J Gateway not available"

    try:
        results_json = json.dumps(results)
        response_from_java = gateway.entry_point.forwardOptimisationResultsToMRA(mra_name, results_json)
        
        response_lower = response_from_java.lower()
        if "mra successfully processed" in response_lower:
            return True, response_from_java
        elif "mra failed" in response_lower or \
             "error: timeout" in response_lower or \
             "error forwarding" in response_lower or \
             "unexpected performative" in response_lower:
            return False, f"JADE/MRA reported issue: {response_from_java}"
        else:
            return False, f"Unexpected response from JADE/MRA: {response_from_java}"
    except Py4JNetworkError as e:
        return False, f"Network error sending results: {str(e)}"
    except Exception as e:
        return False, f"Error sending results: {str(e)}"

def get_compiled_optimization_data_from_mra(gateway, mra_name):
    """
    Gets current delivery agent statuses from MRA via Py4jGatewayAgent.
    Returns JSON string with 'delivery_agent_statuses' array, or error.
    """
    if not gateway:
        return None, "Py4J Gateway not available"
    try:
        data_json_str = gateway.entry_point.getCompiledOptimizationDataFromMRA(mra_name)
        return data_json_str, None 
    except Py4JNetworkError as e:
        return None, f"Network error getting DA statuses from MRA: {str(e)}"
    except Exception as e:
        return None, f"Error getting DA statuses from MRA: {str(e)}"

def trigger_mra_optimisation_cycle(gateway, mra_name):
    """
    Triggers MRA to compile warehouse, parcels and DA statuses for optimisation.
    Returns JSON string with all data needed for optimisation script.
    """
    if not gateway:
        return None, "Py4J Gateway not available"
    try:
        data_json_str = gateway.entry_point.triggerMRAOptimisationCycleAndGetData(mra_name)
        return data_json_str, None
    except Py4JNetworkError as e:
        return None, f"Network error triggering MRA optimisation cycle: {str(e)}"
    except Exception as e:
        return None, f"Error triggering MRA optimisation cycle: {str(e)}"

def send_warehouse_parcel_data_to_mra(gateway, mra_name, warehouse_parcel_json):
    """
    Sends warehouse and parcel data from Python to the MRA.
    MRA will discover DAs via DF rather than receiving IDs from Python.
    """
    if not gateway:
        return False, "Py4J Gateway not available for sending warehouse/parcel data."
    try:
        response_message = gateway.entry_point.receiveWarehouseParcelDataAndForwardToMRA(mra_name, warehouse_parcel_json)
        if "success" in response_message.lower():
            return True, response_message
        else:
            return False, f"MRA/Gateway reported issue receiving warehouse/parcel data: {response_message}"
    except Py4JNetworkError as e_net:
        return False, f"Network error sending warehouse/parcel data to MRA: {str(e_net)}"
    except Exception as e_exc:
        return False, f"Exception sending warehouse/parcel data to MRA: {str(e_exc)}"

def get_jade_simulated_routes_data(gateway):
    if not gateway:
        return None, "Py4J Gateway not available"
    try:
        # This method in Java returns a JSON string representing an array of route objects
        json_array_string = gateway.entry_point.getJadeSimulatedRoutes()
        # Attempt to parse it here to catch errors early and return Python objects
        # If Java returns null or an empty string that is not valid JSON, json.loads will fail.
        if json_array_string is None: # Handle case where Java might return null
             return [], "JADE returned no data for simulated routes (null)."
        
        # Handle empty string which is not valid JSON
        if not json_array_string.strip():
            return [], "JADE returned empty string for simulated routes."

        parsed_data = json.loads(json_array_string)
        return parsed_data, None # Return parsed data and no error
    except Py4JNetworkError as e:
        return None, f"Network error getting JADE simulated routes: {str(e)}"
    except json.JSONDecodeError as e:
        # This will catch if json_array_string is not valid JSON
        return None, f"Error decoding JSON from JADE for simulated routes: {str(e)}. Received: '{json_array_string[:200]}...'"
    except Exception as e:
        # Catch other potential Py4J errors or issues with the gateway call itself
        return None, f"Error getting JADE simulated routes: {str(e)}"
