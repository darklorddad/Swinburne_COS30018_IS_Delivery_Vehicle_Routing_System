import subprocess
import os
import time # Added for checking JADE startup
import platform # Added for OS-specific stop logic
import json # For serializing arguments to JADE agents
from py4j.java_gateway import JavaGateway, GatewayParameters, Py4JNetworkError # For JADE communication

# Attempt to locate jade.jar. This is a common location.
# Users might need to configure this path if it's different.
JADE_JAR_PATH = os.path.join("dependencies", "java", "JADE-all-4.6.0", "jade", "lib", "jade.jar")
# Path to the Py4J JAR, required for compiling agents that use Py4J (e.g., Py4jGatewayAgent)
# and for JADE runtime to find Py4J classes.
# Corrected path based on user-provided file location and new directory structure.
PY4J_JAR_PATH = os.path.join("dependencies", "java", "py4j-0.10.9.9", "py4j-java", "py4j0.10.9.9.jar")
# Path to the org.json JAR, required for JSON parsing in MasterRoutingAgent
JSON_JAR_PATH = os.path.join("dependencies", "java", "libs", "json-20250107.jar") # Updated path and filename


# Default Py4J connection parameters
PY4J_PORT = 25333
PY4J_ADDRESS = "127.0.0.1"

def start_jade_platform():
    """
    Attempts to start the JADE platform and connect via Py4J.
    Returns: (success_bool, message_str, process_obj_or_None, gateway_obj_or_None)
    """
    print(f"Attempting to start JADE platform. JADE JAR expected at: {JADE_JAR_PATH}")
    if not os.path.exists(JADE_JAR_PATH):
        return False, f"JADE JAR not found at {JADE_JAR_PATH}. Please check the path.", None, None
    
    # Starting JADE with -gui. For Py4J, a GatewayServer would need to be started by a JADE agent.
    # The -host and -port parameters for JADE main container might be relevant.
    # Setting port back to 30018 as requested.
    
    # Define classpath: JADE JAR and the 'classes' directory for our compiled agents
    # On Windows, classpath separator is ';'. On Linux/macOS, it's ':'.
    classpath_separator = ";" if platform.system() == "Windows" else ":"
    # Updated path for compiled classes
    compiled_classes_path = os.path.join("packages", "simulation", "java", "classes")
    
    # Ensure the 'classes' directory exists, or JADE might have issues, though javac creates it.
    # For robustness, one might check os.path.exists(compiled_classes_path) here.

    # Command to start JADE, including our Py4jGatewayAgent
    # The agent is specified as agentName:fully.qualified.ClassName
    # Arguments to the agent can be passed in parentheses, e.g., agentName(arg1 arg2):className
    # We don't need arguments for Py4jGatewayAgent at startup via command line.
    # Construct classpath for JADE runtime
    runtime_classpath_list = [JADE_JAR_PATH, PY4J_JAR_PATH, compiled_classes_path]
    if os.path.exists(JSON_JAR_PATH):
        runtime_classpath_list.append(JSON_JAR_PATH)
    else:
        print(f"WARNING: org.json.jar not found at '{JSON_JAR_PATH}' for JADE runtime. MasterRoutingAgent might fail if it uses org.json.")
    
    runtime_classpath = classpath_separator.join(runtime_classpath_list)

    cmd = [
        "java", 
        "-cp", 
        runtime_classpath, 
        "jade.Boot", 
        "-gui", 
        "-port", "30018",
        "py4jgw:jadeagents.Py4jGatewayAgent" # Updated package for gateway agent
    ]
    print(f"JADE startup command: {' '.join(cmd)}") # Log the command for debugging

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
        
        # Wait a few seconds to see if JADE starts successfully or fails quickly
        print("JADE process launched. Waiting a few seconds to check status...")
        time.sleep(4) # Allow JADE time to initialize or fail
        
        if process.poll() is None:
            # Process is still running, attempt Py4J connection.
            print("JADE process is running. Attempting Py4J connection...")
            gateway = None
            try:
                # Allow some time for JADE and the Py4J GatewayServer within JADE to start.
                print("Waiting for JADE Py4J GatewayServer to initialize...")
                time.sleep(5) # Increased from 3 to 5 seconds
                gateway = JavaGateway(
                    gateway_parameters=GatewayParameters(address=PY4J_ADDRESS, port=PY4J_PORT, auto_convert=True)
                )
                # Optionally, test the connection by calling a simple method on the entry_point
                # gateway.jvm.System.out.println("Py4J Gateway Connected from Python!")
                print(f"Successfully connected to Py4J GatewayServer on {PY4J_ADDRESS}:{PY4J_PORT}.")
                return True, "JADE platform process is running and Py4J gateway connected.", process, gateway
            except Py4JNetworkError as e:
                err_msg = f"JADE process started, but Py4J connection failed: {str(e)}. Ensure a Py4J GatewayServer is running in JADE on port {PY4J_PORT}."
                print(err_msg)
                # Even if Py4J fails, the JADE process itself might be running (e.g., GUI is up).
                # We return the process so it can be managed, but no gateway.
                return True, err_msg, process, None # JADE running, Py4J failed
            except Exception as e_gw:
                err_msg = f"JADE process started, but an unexpected error occurred with Py4J: {str(e_gw)}."
                print(err_msg)
                return True, err_msg, process, None # JADE running, Py4J failed
        else:
            # Process terminated, JADE likely failed to start
            stdout_output = process.stdout.read().strip() if process.stdout else ""
            stderr_output = process.stderr.read().strip() if process.stderr else ""
            exit_code = process.returncode
            
            error_details = []
            if stdout_output:
                # JADE often prints "JADE is closing down now." to stdout on port binding failure.
                error_details.append(f"STDOUT: {stdout_output}")
            if stderr_output:
                error_details.append(f"STDERR: {stderr_output}")
            
            full_error_msg = f"JADE process terminated early (exit code {exit_code})."
            if error_details:
                full_error_msg += " Details: " + " | ".join(error_details)
            else:
                full_error_msg += " No output captured on stdout/stderr."
            print(full_error_msg)
            return False, full_error_msg, None, None
    except FileNotFoundError:
        return False, "Java command not found. Is Java installed and in PATH?", None, None
    except Exception as e:
        return False, f"Error starting JADE: {str(e)}", None, None

def compile_java_agents():
    """
    Compiles the JADE agent Java source files.
    Returns: (success_bool, message_str)
    """
    print("Attempting to compile JADE agent Java source files...")
    
    source_path = os.path.join("packages", "simulation", "java", "src", "jadeagents")
    output_classes_path = os.path.join("packages", "simulation", "java", "classes")
    
    # Ensure the output directory for classes exists
    try:
        os.makedirs(output_classes_path, exist_ok=True)
    except Exception as e:
        err_msg = f"Error creating output directory for compiled classes '{output_classes_path}': {str(e)}"
        print(err_msg)
        return False, err_msg

    if not os.path.exists(JADE_JAR_PATH):
        err_msg = f"JADE JAR not found at '{JADE_JAR_PATH}' for compilation."
        print(err_msg)
        return False, err_msg
    if not os.path.exists(PY4J_JAR_PATH):
        err_msg = f"Py4J JAR not found at '{PY4J_JAR_PATH}' for compilation."
        print(err_msg)
        return False, err_msg
    
    if not os.path.exists(JSON_JAR_PATH):
        err_msg = f"org.json.jar not found at '{JSON_JAR_PATH}'. This is required for compiling JADE agents. Please ensure the JAR is present at this location."
        print(err_msg)
        return False, err_msg

    # Check if source files exist
    java_source_files = [f for f in os.listdir(source_path) if f.endswith(".java")]
    if not java_source_files:
        err_msg = f"No Java source files found in '{source_path}'."
        print(err_msg)
        return False, err_msg
    
    source_files_pattern = os.path.join(source_path, "*.java")

    classpath_separator = ";" if platform.system() == "Windows" else ":"
    # All required JARs (JADE, Py4J, JSON) are confirmed to exist at this point.
    compile_classpath = f"{JADE_JAR_PATH}{classpath_separator}{PY4J_JAR_PATH}{classpath_separator}{JSON_JAR_PATH}"

    # Construct the javac command
    # Using os.path.normpath to ensure paths are in the correct format for the OS.
    javac_cmd = [
        "javac",
        "-cp", compile_classpath,
        "-d", os.path.normpath(output_classes_path),
        os.path.normpath(source_files_pattern) # Path to all .java files in the source directory
    ]

    print(f"Compilation command: {' '.join(javac_cmd)}")

    try:
        # Using shell=False is generally safer. subprocess.run handles arguments as a list.
        result = subprocess.run(javac_cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print("Java agents compiled successfully.")
            return True, "JADE agents compiled successfully."
        else:
            # Compilation failed, provide error details.
            error_output = result.stderr if result.stderr else result.stdout
            err_msg = f"JADE agent compilation failed (exit code {result.returncode}):\n{error_output}"
            print(err_msg)
            return False, err_msg
            
    except FileNotFoundError:
        err_msg = "javac command not found. Is Java Development Kit (JDK) installed and in PATH?"
        print(err_msg)
        return False, err_msg
    except Exception as e:
        err_msg = f"An unexpected error occurred during Java agent compilation: {str(e)}"
        print(err_msg)
        return False, err_msg

def stop_jade_platform(process_info, gateway_obj):
    """
    Attempts to stop the JADE platform process and shutdown Py4J gateway.
    'process_info' is expected to be a subprocess.Popen object.
    Returns: (success_bool, message_str)
    """
    print("Attempting to stop JADE platform...")
    
    py4j_shutdown_msg = ""
    if gateway_obj:
        try:
            gateway_obj.shutdown()
            print("Py4J Gateway shut down successfully.")
            py4j_shutdown_msg = "Py4J Gateway shut down. "
        except Exception as e:
            print(f"Error shutting down Py4J Gateway: {str(e)}")
            py4j_shutdown_msg = f"Error shutting down Py4J Gateway: {str(e)}. "

    if not process_info or not hasattr(process_info, 'pid'):
        return False, py4j_shutdown_msg + "No valid JADE process information available to stop."

    pid = process_info.pid # Get PID before poll, in case it terminates mid-check
    if process_info.poll() is not None:
        return True, f"JADE platform process (PID: {pid}) was already terminated (exit code {process_info.returncode})."

    print(f"Stopping JADE platform process (PID: {pid})...")

    if platform.system() == "Windows":
        print(f"Attempting to stop JADE process (PID: {pid}) on Windows using taskkill /F /T...")
        try:
            # Directly use taskkill to terminate the process and its children.
            # This is generally more effective for GUI applications or those with complex process trees on Windows.
            kill_cmd = ["taskkill", "/PID", str(pid), "/F", "/T"]
            # Using CREATE_NO_WINDOW for taskkill to prevent flashing a console window
            kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Wait for the process_info object to update its state after taskkill.
            # This helps Popen.poll() reflect the actual process state.
            try:
                process_info.wait(timeout=3) # Give it a few seconds
            except subprocess.TimeoutExpired:
                print(f"JADE process (PID: {pid}) Popen status did not update within timeout after taskkill.")
            except Exception as e_wait: # Catch other potential errors during wait
                print(f"Error during Popen.wait() for PID {pid} after taskkill: {str(e_wait)}")

            final_poll_code = process_info.poll()

            if kill_result.returncode == 0: # taskkill reported success
                if final_poll_code is not None:
                    print(f"taskkill successfully terminated PID {pid}. Process poll confirms termination (exit code {final_poll_code}).")
                    return True, "JADE platform terminated via taskkill."
                else:
                    # taskkill succeeded, but Popen object still thinks the process is running.
                    # This might indicate the main PID is stubborn or Popen's state is slow to update.
                    print(f"taskkill reported success for PID {pid}, but Popen object still reports process as running. Attempting Popen.kill().")
                    try:
                        process_info.kill()
                        process_info.wait(timeout=2) # Wait for kill to take effect
                        if process_info.poll() is not None:
                            print(f"JADE process (PID: {pid}) terminated via Popen.kill() after inconsistent taskkill report.")
                            return True, "JADE platform terminated (taskkill success, Popen inconsistent, then Popen.kill() success)."
                        else:
                            print(f"JADE process (PID: {pid}) still running after Popen.kill().")
                            return False, f"Failed to confirm JADE termination for PID {pid} (taskkill success, Popen inconsistent, Popen.kill() failed to confirm)."
                    except Exception as e_kill:
                        print(f"Error during Popen.kill() for PID {pid}: {str(e_kill)}")
                        return False, f"Error during Popen.kill() after inconsistent taskkill for PID {pid}."

            elif kill_result.returncode == 128: # "Process not found" by taskkill
                if final_poll_code is not None:
                    # taskkill couldn't find it, and Popen confirms it's terminated. Good.
                    print(f"taskkill for PID {pid} reported process not found (RC: 128). Process poll confirms termination (exit code {final_poll_code}).")
                    return True, "JADE platform terminated (taskkill confirmed process not running)."
                else:
                    # taskkill couldn't find it, but Popen thinks it's still running. This is a problematic inconsistency.
                    print(f"taskkill for PID {pid} reported process not found (RC: 128), but Popen object still reports process as running. This is unexpected. Taskkill stderr: {kill_result.stderr.strip()}")
                    return False, f"Failed to confirm JADE termination for PID {pid} (taskkill: process not found, Popen poll inconsistent)."
            else: # taskkill failed for other reasons (e.g., access denied, other errors)
                error_message = kill_result.stderr.strip() or kill_result.stdout.strip() or f"Unknown taskkill error (RC: {kill_result.returncode})"
                print(f"taskkill failed for PID {pid}. Error: {error_message}. Process poll after taskkill: {final_poll_code}")
                if final_poll_code is not None: # If it died despite taskkill error message
                    return True, f"JADE platform terminated (found dead after taskkill error for PID {pid}: {error_message})"
                
                # Fallback to Popen methods if taskkill failed and process is still alive according to Popen
                print(f"taskkill failed for PID {pid}. Attempting Popen.terminate() then Popen.kill() as fallback.")
                try:
                    process_info.terminate()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        print(f"JADE process (PID: {pid}) terminated via Popen.terminate() after taskkill failure.")
                        return True, "JADE platform terminated (taskkill failed, Popen.terminate() success)."
                except subprocess.TimeoutExpired:
                    print(f"Popen.terminate() timed out for PID {pid} after taskkill failure.")
                except Exception as e_term:
                    print(f"Error during Popen.terminate() for PID {pid}: {str(e_term)}")

                try:
                    process_info.kill()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        print(f"JADE process (PID: {pid}) terminated via Popen.kill() after taskkill/terminate failure.")
                        return True, "JADE platform terminated (taskkill failed, Popen.kill() success)."
                except Exception as e_kill_fallback:
                    print(f"Error during Popen.kill() fallback for PID {pid}: {str(e_kill_fallback)}")
                
                return False, f"Failed to terminate JADE platform (PID: {pid}) using taskkill and Popen methods. Taskkill Error: {error_message}"
        except Exception as e:
            # General exception during the Windows stop process
            print(f"General exception during Windows stop procedure for PID {pid}: {str(e)}")
            if process_info.poll() is not None: # Check if process died despite exception
                return True, py4j_shutdown_msg + f"JADE platform (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, py4j_shutdown_msg + f"Error stopping JADE process (PID: {pid}) on Windows: {str(e)}"
    else: # For non-Windows OS
        try:
            process_info.terminate() # SIGTERM
            process_info.wait(timeout=5)
            print(f"JADE process (PID: {pid}) terminated via Popen.terminate().")
            return True, "JADE platform terminated."
        except subprocess.TimeoutExpired:
            print(f"JADE process (PID: {pid}) did not respond to terminate(). Using Popen.kill().")
            process_info.kill() # SIGKILL
            try:
                process_info.wait(timeout=2) # Wait for kill to take effect
                print(f"JADE process (PID: {pid}) terminated via Popen.kill().")
                return True, "JADE platform forcefully killed."
            except subprocess.TimeoutExpired:
                print(f"JADE process (PID: {pid}) did not terminate even after Popen.kill(). This is unexpected.")
                return False, f"Failed to confirm JADE platform (PID: {pid}) termination after kill."
        except Exception as e:
            print(f"Exception during non-Windows stop procedure for PID {pid}: {str(e)}")
            if process_info.poll() is not None: # Check if process died despite exception
                 return True, py4j_shutdown_msg + f"JADE platform (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, py4j_shutdown_msg + f"Error stopping JADE process (PID: {pid}): {str(e)}"
    
    # Fallback, should ideally not be reached
    return False, py4j_shutdown_msg + "Could not stop JADE platform due to an unknown issue."

def _create_agent_in_jade(gateway_obj, agent_name, agent_class, agent_args_list_of_strings):
    """
    Creates an agent in JADE using Py4J.
    'gateway_obj' is the Py4J JavaGateway object.
    'agent_args_list_of_strings' should be a list of strings. Complex objects need prior serialization (e.g., to JSON).
    Returns: (success_bool, message_str)
    """
    if not gateway_obj:
        return False, "Py4J Gateway not available. Cannot create agent."
    
    try:
        # This assumes your JADE GatewayServer's entry point provides an object
        # (e.g., "jadePlatformController") that has a method "createAgent".
        # You will need to implement this on the Java/JADE side.
        # Example: java_controller = gateway_obj.entry_point.getJadePlatformController()
        # For direct container controller access (less common for remote agent creation):
        # main_container_controller = gateway_obj.jvm.jade.core.Runtime.instance().getContainer(True).getPlatformController()
        
        # A common approach is to have a dedicated JADE agent that listens for Py4J calls
        # and then uses JADE's internal mechanisms to create agents.
        # Let's assume an entry point 'jadeEntryPoint' with a method 'createAgentByController'.
        jade_entry_point = gateway_obj.entry_point 
        
        # Convert Python list of strings to Java String array
        java_args_array = gateway_obj.new_array(gateway_obj.jvm.java.lang.String, len(agent_args_list_of_strings))
        for i, arg_str in enumerate(agent_args_list_of_strings):
            java_args_array[i] = arg_str
            
        # The method signature on the Java side should be:
        # public String createAgentByController(String agentName, String agentClass, String[] agentArgs)
        # It should return a message indicating success or failure.
        print(f"Py4J: Calling createAgentByController with Name: {agent_name}, Class: {agent_class}, Args: {agent_args_list_of_strings}")
        result_message = jade_entry_point.createAgentByController(agent_name, agent_class, java_args_array)
        
        print(f"Py4J: Agent creation request for '{agent_name}' (Class: {agent_class}) sent. JADE response: {result_message}")
        # We assume the Java method returns a string that indicates success if it doesn't throw an exception
        # or if the message doesn't explicitly state "error" or "fail". This might need refinement.
        if "error" in result_message.lower() or "fail" in result_message.lower():
            return False, f"JADE reported an error for agent '{agent_name}': {result_message}"
        return True, f"Agent '{agent_name}' creation request processed by JADE. Response: {result_message}"
    except Py4JNetworkError as e:
        return False, f"Py4J Network Error creating agent '{agent_name}': {str(e)}. Check JADE GatewayServer."
    except Exception as e:
        # This can include errors if the Java method doesn't exist, wrong signature, or Java-side exceptions.
        return False, f"Error creating agent '{agent_name}' via Py4J: {str(e)}"

def create_mra_agent(gateway_obj, agent_name, agent_java_class, config_data_dict):
    """
    Creates the Master Routing Agent (MRA) in JADE.
    'config_data_dict' is the Python dictionary for configuration.
    It is passed as a JSON string argument to the JADE agent.
    """
    try:
        agent_args_str = [json.dumps(config_data_dict)] 
    except Exception as e:
        return False, f"Error serializing config_data_dict for MRA to JSON: {str(e)}"
    return _create_agent_in_jade(gateway_obj, agent_name, agent_java_class, agent_args_str)

def create_da_agent(gateway_obj, agent_name, agent_java_class, agent_config_dict):
    """
    Creates a Delivery Agent (DA) in JADE.
    'agent_config_dict' is the Python dictionary for this specific agent's configuration,
    passed as a JSON string argument.
    """
    try:
        agent_args_str = [json.dumps(agent_config_dict)]
    except Exception as e:
        return False, f"Error serializing agent_config_dict for DA '{agent_name}' to JSON: {str(e)}"
    return _create_agent_in_jade(gateway_obj, agent_name, agent_java_class, agent_args_str)

def send_optimisation_results_to_mra(gateway_obj, mra_agent_name, optimisation_results_py_dict):
    """
    Sends the full optimisation results to the Master Routing Agent (MRA) in JADE via Py4J.
    The MRA will then be responsible for parsing these results and dispatching individual routes to DAs.
    Returns: (success_bool, message_str)
    """
    if not gateway_obj:
        return False, "Py4J Gateway not available. Cannot send results to MRA."
        
    if not optimisation_results_py_dict:
        return False, "Optimisation results are missing. Cannot send to MRA."

    try:
        full_results_json_str = json.dumps(optimisation_results_py_dict)
        
        # Assume the JADE entry point (Py4jGatewayAgent) has a method
        # to forward this data to the MRA.
        # public String forwardOptimisationResultsToMRA(String mraName, String fullResultsJson)
        jade_entry_point = gateway_obj.entry_point
        response_message = jade_entry_point.forwardOptimisationResultsToMRA(mra_agent_name, full_results_json_str)
        
        print(f"Py4J: Sent full optimisation results to MRA '{mra_agent_name}'. JADE response: {response_message}")
        if "error" in response_message.lower() or "fail" in response_message.lower():
            return False, f"JADE reported an error forwarding results to MRA '{mra_agent_name}': {response_message}"
        return True, f"Full optimisation results sent to MRA '{mra_agent_name}'. JADE response: {response_message}"
    except Py4JNetworkError as e:
        return False, f"Py4J Network Error sending results to MRA '{mra_agent_name}': {str(e)}. Check JADE GatewayServer."
    except Exception as e:
        return False, f"Error sending results to MRA '{mra_agent_name}' via Py4J: {str(e)}"
