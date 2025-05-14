import subprocess
import os
import time # Added for checking JADE startup
import platform # Added for OS-specific stop logic
# import json # Would be needed for serializing complex agent arguments

# Attempt to locate jade.jar. This is a common location.
# Users might need to configure this path if it's different.
JADE_JAR_PATH = os.path.join("dependencies", "JADE-all-4.6.0", "jade", "lib", "jade.jar")

# Placeholder for Py4J gateway, would be initialized if Py4J is used.
# py4j_gateway = None 

def start_jade_platform():
    """
    Attempts to start the JADE platform using subprocess.
    Returns: (success_bool, message_str, process_obj_or_None)
    """
    print(f"Attempting to start JADE platform. JADE JAR expected at: {JADE_JAR_PATH}")
    if not os.path.exists(JADE_JAR_PATH):
        return False, f"JADE JAR not found at {JADE_JAR_PATH}. Please check the path.", None
    
    # Starting JADE with -gui. For Py4J, a GatewayServer would need to be started by a JADE agent.
    # The -host and -port parameters for JADE main container might be relevant.
    # Setting port back to 30018 as requested.
    cmd = ["java", "-cp", JADE_JAR_PATH, "jade.Boot", "-gui", "-port", "30018"]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
        
        # Wait a few seconds to see if JADE starts successfully or fails quickly
        print("JADE process launched. Waiting a few seconds to check status...")
        time.sleep(4) # Allow JADE time to initialize or fail
        
        if process.poll() is None:
            # Process is still running, assume JADE started successfully for now.
            print("JADE process is still running. Assuming successful start.")
            return True, "JADE platform process is running.", process
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
            return False, full_error_msg, None
    except FileNotFoundError:
        return False, "Java command not found. Is Java installed and in PATH?", None
    except Exception as e:
        return False, f"Error starting JADE: {str(e)}", None

def stop_jade_platform(process_info, gateway_obj): # gateway_obj is unused
    """
    Attempts to stop the JADE platform process.
    'process_info' is expected to be a subprocess.Popen object.
    Returns: (success_bool, message_str)
    """
    print("Attempting to stop JADE platform...")

    if not process_info or not hasattr(process_info, 'pid'):
        return False, "No valid JADE process information available to stop."

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
                return True, f"JADE platform (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, f"Error stopping JADE process (PID: {pid}) on Windows: {str(e)}"
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
                 return True, f"JADE platform (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, f"Error stopping JADE process (PID: {pid}): {str(e)}"
    
    # Fallback, should ideally not be reached
    return False, "Could not stop JADE platform due to an unknown issue."

def _create_agent_in_jade_simulated(agent_name, agent_class, agent_args_list_of_strings):
    """
    Simulates creating an agent in JADE.
    In a real implementation, this would use Py4J to call JADE's agent creation methods.
    'agent_args_list_of_strings' should be a list of strings. Complex objects need prior serialization.
    Returns: (success_bool, message_str)
    """
    # global py4j_gateway
    # if py4j_gateway:
    #     try:
    #         # Example: Assuming a controller object on the Java side accessible via gateway
    #         # java_controller = py4j_gateway.entry_point.getJadePlatformController()
    #         # java_args_array = py4j_gateway.new_array(py4j_gateway.jvm.String, len(agent_args_list_of_strings))
    #         # for i, arg_str in enumerate(agent_args_list_of_strings):
    #         #     java_args_array[i] = arg_str
    #         # java_controller.createAgent(agent_name, agent_class, java_args_array)
    #         print(f"Py4J: Requesting creation of agent: {agent_name}, Class: {agent_class}, Args: {agent_args_list_of_strings}")
    #         return True, f"Agent {agent_name} creation request sent to JADE (simulated)."
    #     except Exception as e:
    #         return False, f"Error creating agent {agent_name} via Py4J (simulated): {str(e)}"
    # else:
    #     return False, "Py4J Gateway not available (simulated)."
    print(f"Simulating creation of JADE agent: Name='{agent_name}', Class='{agent_class}', Args='{agent_args_list_of_strings}'")
    return True, f"Agent '{agent_name}' creation simulated successfully."

def create_mra_agent(agent_name, agent_java_class, config_data_dict):
    """
    Simulates creating the Master Routing Agent (MRA).
    'config_data_dict' is the Python dictionary for configuration.
    It would need to be passed appropriately, perhaps as a JSON string argument.
    """
    # For simulation, we might just pass a reference or key.
    # In reality, you might pass the config as a JSON string.
    # agent_args_str = [json.dumps(config_data_dict)] 
    agent_args_str = ["config_placeholder_for_mra"] # Simplified for simulation
    return _create_agent_in_jade_simulated(agent_name, agent_java_class, agent_args_str)

def create_da_agent(agent_name, agent_java_class, agent_config_dict):
    """
    Simulates creating a Delivery Agent (DA).
    'agent_config_dict' is the Python dictionary for this specific agent's configuration.
    """
    # agent_args_str = [json.dumps(agent_config_dict)]
    agent_args_str = [f"config_for_{agent_name}"] # Simplified for simulation
    return _create_agent_in_jade_simulated(agent_name, agent_java_class, agent_args_str)

def trigger_mra_optimisation_and_notify_das(mra_agent_name, optimisation_results_py_dict):
    """
    Simulates sending optimisation results to the MRA in JADE.
    The MRA would then (in a real JADE implementation) parse these results,
    create ACL messages with routes, and send them to the respective DAs.
    Returns: (success_bool, message_str)
    """
    # global py4j_gateway
    # if py4j_gateway:
    #     try:
    #         # results_json_str = json.dumps(optimisation_results_py_dict)
    #         # Example: Send an ACL message via Py4J to the MRA
    #         # acl = py4j_gateway.jvm.jade.lang.acl.ACLMessage(py4j_gateway.jvm.jade.lang.acl.ACLMessage.REQUEST)
    #         # mra_aid = py4j_gateway.jvm.jade.core.AID(mra_agent_name, py4j_gateway.jvm.jade.core.AID.ISLOCALNAME)
    #         # acl.addReceiver(mra_aid)
    #         # acl.setContent(results_json_str)
    #         # acl.setOntology("VRPResults")
    #         # py4j_gateway.entry_point.getAgent(mra_agent_name).postMessage(acl) # Assuming agent has postMessage or similar
    #         print(f"Py4J: Sending optimisation results to MRA {mra_agent_name} (simulated).")
    #         return True, f"Optimisation results sent to MRA {mra_agent_name} (simulated)."
    #     except Exception as e:
    #         return False, f"Error sending results to MRA {mra_agent_name} via Py4J (simulated): {str(e)}"
    # else:
    #   return False, "Py4J Gateway not available (simulated)."
    print(f"Simulating sending optimisation results to MRA '{mra_agent_name}'. Results: {optimisation_results_py_dict}")
    return True, "Simulation triggered with MRA (simulated) and results sent."
