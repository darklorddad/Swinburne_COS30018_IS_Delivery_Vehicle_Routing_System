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
        response = gateway.entry_point.forwardOptimisationResultsToMRA(mra_name, results_json)
        
        if "error" in response.lower() or "fail" in response.lower():
            return False, f"JADE reported error: {response}"
        return True, response
    except Py4JNetworkError as e:
        return False, f"Network error sending results: {str(e)}"
    except Exception as e:
        return False, f"Error sending results: {str(e)}"

def get_compiled_optimization_data_from_mra(gateway, mra_name):
    """
    Calls the Py4jGatewayAgent on the Java side to get compiled data from the MRA.
    Returns the data as a JSON string, and an error message if any.
    """
    if not gateway:
        return None, "Py4J Gateway not available"
    try:
        data_json_str = gateway.entry_point.getCompiledOptimizationDataFromMRA(mra_name)
        return data_json_str, None 
    except Py4JNetworkError as e:
        return None, f"Network error getting compiled data from MRA: {str(e)}"
    except Exception as e:
        return None, f"Error getting compiled data from MRA (Exception: {type(e).__name__} - {str(e)})"

def get_compiled_optimization_data_from_mra(gateway, mra_name):
    """
    Calls the Py4jGatewayAgent on the Java side to get compiled data from the MRA.
    Returns the data as a JSON string, and an error message if any.
    """
    if not gateway:
        return None, "Py4J Gateway not available"
    try:
        # This calls the getCompiledOptimizationDataFromMRA method in Py4jGatewayAgent.java
        data_json_str = gateway.entry_point.getCompiledOptimizationDataFromMRA(mra_name)
        # The Java method should return a JSON string. If it contains an error structure,
        # the Python side might want to parse it and handle it. For now, just return.
        return data_json_str, None 
    except Py4JNetworkError as e:
        return None, f"Network error getting compiled data from MRA: {str(e)}"
    except Exception as e:
        return None, f"Error getting compiled data from MRA (Exception: {type(e).__name__} - {str(e)})"
