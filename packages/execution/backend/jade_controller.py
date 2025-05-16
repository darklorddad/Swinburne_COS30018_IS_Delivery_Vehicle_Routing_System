import os
from . import jade_process_manager, java_compiler, py4j_gateway

# Path configurations
JADE_JAR_PATH = os.path.join("dependencies", "java", "JADE-all-4.6.0", "jade", "lib", "jade.jar")
PY4J_JAR_PATH = os.path.join("dependencies", "python", "py4j-0.10.9.9", "py4j-java", "py4j0.10.9.9.jar")
JSON_JAR_PATH = os.path.join("dependencies", "java", "libs", "json-20250107.jar")
COMPILED_CLASSES_PATH = os.path.join("packages", "execution", "backend", "java", "classes")
JAVA_SOURCE_PATH = os.path.join("packages", "execution", "backend", "java", "scr")


# Default Py4J connection parameters
PY4J_PORT = 25333  # Must match the port used by GatewayServer in Py4jGatewayAgent.java
PY4J_ADDRESS = "127.0.0.1"

# Helper function to read from a stream in a separate thread
def _stream_reader_thread(stream, stop_event, prefix=""):
    try:
        # iter(callable, sentinel) reads until callable returns sentinel
        for line in iter(stream.readline, ''): 
            if stop_event.is_set():
                # print(f"Stream reader ({prefix}) stopping due to event.", flush=True)
                break
            if line: # Ensure line is not empty
                print(f"{prefix}{line.strip()}", flush=True)
    except Exception as e:
        # This might happen if the stream is closed abruptly, e.g., process killed
        if not stop_event.is_set(): # Don't log error if we intended to stop
             print(f"Exception in stream reader thread ({prefix}): {e}", flush=True)
    finally:
        if hasattr(stream, 'close') and not stream.closed:
            try:
                stream.close()
            except Exception as e_close:
                print(f"Exception closing stream in reader thread ({prefix}): {e_close}", flush=True)
        # print(f"Stream reader thread ({prefix}) finished.", flush=True)

def start_jade_platform():
    # Compile Java agents first
    compile_success, compile_message = compile_java_agents()
    if not compile_success:
        return False, f"JADE startup aborted: {compile_message}", None, None, None

    # Start JADE platform process
    success, message, process, log_stop_event = jade_process_manager.start_jade_platform(
        JADE_JAR_PATH,
        PY4J_JAR_PATH,
        JSON_JAR_PATH,
        COMPILED_CLASSES_PATH
    )
    
    # Connect to Py4J gateway if process started successfully
    gateway = None
    if success and process:
        gateway, gw_error = py4j_gateway.connect_to_gateway()
        if gw_error:
            message += f" | {gw_error}"
            
    return success, message, process, gateway, log_stop_event
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
            
            full_error_msg = f"JADE process terminated early (exit code {exit_code})"
            if error_details:
                full_error_msg += " Details: " + " | ".join(error_details)
            else:
                full_error_msg += " No output captured on stdout/stderr"
            print(full_error_msg)
            return False, full_error_msg, None, None, None
    except FileNotFoundError:
        return False, "Java command not found. Is Java installed and in PATH?", None, None, None
    except Exception as e:
        return False, f"Error starting JADE: {str(e)}", None, None, None

def compile_java_agents():
    return java_compiler.compile_java_agents(
        JAVA_SOURCE_PATH,
        COMPILED_CLASSES_PATH,
        JADE_JAR_PATH,
        PY4J_JAR_PATH,
        JSON_JAR_PATH
    )

def stop_jade_platform(process_info, gateway_obj, log_stop_event):
    """
    Attempts to stop the JADE platform process, Py4J gateway, and log reader threads.
    'process_info' is expected to be a subprocess.Popen object.
    'log_stop_event' is a threading.Event to signal log reader threads to stop.
    Returns: (success_bool, message_str)
    """
    print("Attempting to stop JADE platform...")

    if log_stop_event:
        # print("Signalling JADE log reader threads to stop...", flush=True)
        log_stop_event.set()
        # Give threads a moment to stop. Since they are daemonic, explicit join isn't strictly
        # necessary for program exit, but good if we want to ensure they finish before process kill.
        # For simplicity here, we'll rely on them being daemonic and the event signal.
    
    py4j_shutdown_msg = ""
    if gateway_obj:
        try:
            gateway_obj.shutdown()
            print("Py4J Gateway shut down successfully")
            py4j_shutdown_msg = "Py4J Gateway shut down. "
        except Exception as e:
            print(f"Error shutting down Py4J Gateway: {str(e)}")
            py4j_shutdown_msg = f"Error shutting down Py4J Gateway: {str(e)}. "

    if not process_info or not hasattr(process_info, 'pid'):
        return False, py4j_shutdown_msg + "No valid JADE process information available to stop"

    pid = process_info.pid # Get PID before poll, in case it terminates mid-check
    if process_info.poll() is not None:
        return True, f"JADE process (PID: {pid}) was already terminated (exit code {process_info.returncode})"

    print(f"Stopping JADE process (PID: {pid})...")

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
                print(f"JADE process (PID: {pid}) Popen status did not update within timeout after taskkill")
            except Exception as e_wait: # Catch other potential errors during wait
                print(f"Error during Popen.wait() for PID {pid} after taskkill: {str(e_wait)}")

            final_poll_code = process_info.poll()

            if kill_result.returncode == 0: # taskkill reported success
                if final_poll_code is not None:
                    print(f"taskkill successfully terminated PID {pid}. Process poll confirms termination (exit code {final_poll_code})")
                    return True, "JADE terminated via taskkill"
                else:
                    # taskkill succeeded, but Popen object still thinks the process is running.
                    # This might indicate the main PID is stubborn or Popen's state is slow to update.
                    print(f"taskkill reported success for PID {pid}, but Popen object still reports process as running. Attempting Popen.kill()")
                    try:
                        process_info.kill()
                        process_info.wait(timeout=2) # Wait for kill to take effect
                        if process_info.poll() is not None:
                            print(f"JADE process (PID: {pid}) terminated via Popen.kill() after inconsistent taskkill report")
                            return True, "JADE platform terminated (taskkill success, Popen inconsistent, then Popen.kill() success)"
                        else:
                            print(f"JADE process (PID: {pid}) still running after Popen.kill()")
                            return False, f"Failed to confirm JADE termination for PID {pid} (taskkill success, Popen inconsistent, Popen.kill() failed to confirm)"
                    except Exception as e_kill:
                        print(f"Error during Popen.kill() for PID {pid}: {str(e_kill)}")
                        return False, f"Error during Popen.kill() after inconsistent taskkill for PID {pid}"

            elif kill_result.returncode == 128: # "Process not found" by taskkill
                if final_poll_code is not None:
                    # taskkill couldn't find it, and Popen confirms it's terminated. Good.
                    print(f"taskkill for PID {pid} reported process not found (RC: 128). Process poll confirms termination (exit code {final_poll_code})")
                    return True, "JADE terminated (taskkill confirmed process not running)"
                else:
                    # taskkill couldn't find it, but Popen thinks it's still running. This is a problematic inconsistency.
                    print(f"taskkill for PID {pid} reported process not found (RC: 128), but Popen object still reports process as running. This is unexpected. Taskkill stderr: {kill_result.stderr.strip()}")
                    return False, f"Failed to confirm JADE termination for PID {pid} (taskkill: process not found, Popen poll inconsistent)"
            else: # taskkill failed for other reasons (e.g., access denied, other errors)
                error_message = kill_result.stderr.strip() or kill_result.stdout.strip() or f"Unknown taskkill error (RC: {kill_result.returncode})"
                print(f"taskkill failed for PID {pid}. Error: {error_message}. Process poll after taskkill: {final_poll_code}")
                if final_poll_code is not None: # If it died despite taskkill error message
                    return True, f"JADE terminated (found dead after taskkill error for PID {pid}: {error_message})"
                
                # Fallback to Popen methods if taskkill failed and process is still alive according to Popen
                print(f"taskkill failed for PID {pid}. Attempting Popen.terminate() then Popen.kill() as fallback")
                try:
                    process_info.terminate()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        print(f"JADE process (PID: {pid}) terminated via Popen.terminate() after taskkill failure")
                        return True, "JADE terminated (taskkill failed, Popen.terminate() success)"
                except subprocess.TimeoutExpired:
                    print(f"Popen.terminate() timed out for PID {pid} after taskkill failure")
                except Exception as e_term:
                    print(f"Error during Popen.terminate() for PID {pid}: {str(e_term)}")

                try:
                    process_info.kill()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        print(f"JADE process (PID: {pid}) terminated via Popen.kill() after taskkill/terminate failure")
                        return True, "JADE terminated (taskkill failed, Popen.kill() success)"
                except Exception as e_kill_fallback:
                    print(f"Error during Popen.kill() fallback for PID {pid}: {str(e_kill_fallback)}")
                
                return False, f"Failed to terminate JADE (PID: {pid}) using taskkill and Popen methods. Taskkill Error: {error_message}"
        except Exception as e:
            # General exception during the Windows stop process
            print(f"General exception during Windows stop procedure for PID {pid}: {str(e)}")
            if process_info.poll() is not None: # Check if process died despite exception
                return True, py4j_shutdown_msg + f"JADE (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, py4j_shutdown_msg + f"Error stopping JADE process (PID: {pid}) on Windows: {str(e)}"
    else: # For non-Windows OS
        try:
            process_info.terminate() # SIGTERM
            process_info.wait(timeout=5)
            print(f"JADE process (PID: {pid}) terminated via Popen.terminate()")
            return True, "JADE terminated"
        except subprocess.TimeoutExpired:
            print(f"JADE process (PID: {pid}) did not respond to terminate(). Using Popen.kill()")
            process_info.kill() # SIGKILL
            try:
                process_info.wait(timeout=2) # Wait for kill to take effect
                print(f"JADE process (PID: {pid}) terminated via Popen.kill()")
                return True, "JADE forcefully killed"
            except subprocess.TimeoutExpired:
                print(f"JADE process (PID: {pid}) did not terminate even after Popen.kill(). This is unexpected")
                return False, f"Failed to confirm JADE (PID: {pid}) termination after kill"
        except Exception as e:
            print(f"Exception during non-Windows stop procedure for PID {pid}: {str(e)}")
            if process_info.poll() is not None: # Check if process died despite exception
                 return True, py4j_shutdown_msg + f"JADE (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, py4j_shutdown_msg + f"Error stopping JADE process (PID: {pid}): {str(e)}"
    
    # Fallback, should ideally not be reached
    return False, py4j_shutdown_msg + "Could not stop JADE platform due to an unknown issue."

def create_mra_agent(gateway, agent_name, config_data):
    return py4j_gateway.create_mra_agent(gateway, agent_name, config_data)

def create_da_agent(gateway, agent_name, agent_config):
    return py4j_gateway.create_da_agent(gateway, agent_name, agent_config)

def send_optimisation_results_to_mra(gateway, mra_name, results):
    return py4j_gateway.send_optimisation_results(gateway, mra_name, results)
