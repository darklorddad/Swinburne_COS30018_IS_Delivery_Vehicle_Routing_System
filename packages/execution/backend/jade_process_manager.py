import subprocess
import os
import time
import platform
import threading

def _stream_reader_thread(stream, stop_event, prefix=""):
    try:
        for line in iter(stream.readline, ''): 
            if stop_event.is_set():
                break
            if line:
                print(f"{prefix}{line.strip()}", flush=True)
    except Exception as e:
        if not stop_event.is_set():
             print(f"Exception in stream reader thread ({prefix}): {e}", flush=True)
    finally:
        if hasattr(stream, 'close') and not stream.closed:
            try:
                stream.close()
            except Exception as e_close:
                print(f"Exception closing stream in reader thread ({prefix}): {e_close}", flush=True)

def start_jade_platform(jade_jar_path, py4j_jar_path, json_jar_path, compiled_classes_path, hide_gui: bool = False):
    print(f"Attempting to start JADE. JADE JAR expected at: {jade_jar_path}")
    if not os.path.exists(jade_jar_path):
        return False, f"JADE JAR not found at {jade_jar_path}. Please check the path", None, None

    classpath_separator = ";" if platform.system() == "Windows" else ":"
    runtime_classpath_list = [jade_jar_path, py4j_jar_path, compiled_classes_path]
    
    if os.path.exists(json_jar_path):
        runtime_classpath_list.append(json_jar_path)
    else:
        print(f"WARNING: org.json.jar not found at '{json_jar_path}'")

    runtime_classpath = classpath_separator.join(runtime_classpath_list)

    cmd_core = [
        "java", 
        "-cp", 
        runtime_classpath, 
        "jade.Boot"
    ]

    if not hide_gui:
        cmd_core.append("-gui")
    
    cmd_core.extend([
        "-port", "1099",
    ])

    agent_spec = "py4jgw:Py4jGatewayAgent"
    if not hide_gui:
        agent_spec += ";dvrSniffer:jade.tools.sniffer.Sniffer(*)"
    cmd_core.append(agent_spec)
    cmd = cmd_core

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, 
                                 creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
        
        print("JADE process launched. Waiting a few seconds to check status...")
        time.sleep(4)
        
        if process.poll() is None:
            log_stop_event = threading.Event()
            
            stdout_thread = threading.Thread(
                target=_stream_reader_thread, 
                args=(process.stdout, log_stop_event, "JADE STDOUT: "),
                daemon=True 
            )
            stderr_thread = threading.Thread(
                target=_stream_reader_thread,
                args=(process.stderr, log_stop_event, "JADE STDERR: "),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            return True, "JADE process is running", process, log_stop_event
        else:
            stdout_output = process.stdout.read().strip() if process.stdout else ""
            stderr_output = process.stderr.read().strip() if process.stderr else ""
            exit_code = process.returncode
            
            error_details = []
            if stdout_output:
                error_details.append(f"STDOUT: {stdout_output}")
            if stderr_output:
                error_details.append(f"STDERR: {stderr_output}")
            
            full_error_msg = f"JADE process terminated early (exit code {exit_code})"
            if error_details:
                full_error_msg += " Details: " + " | ".join(error_details)
            return False, full_error_msg, None, None
    except FileNotFoundError:
        return False, "Java command not found. Is Java installed and in PATH?", None, None
    except Exception as e:
        return False, f"Error starting JADE: {str(e)}", None, None

def stop_jade_platform(process_info, log_stop_event):
    if log_stop_event:
        log_stop_event.set()
    
    if not process_info or not hasattr(process_info, 'pid'):
        return False, "No valid JADE process information available to stop"

    pid = process_info.pid
    if process_info.poll() is not None:
        return True, f"JADE process (PID: {pid}) was already terminated"

    print(f"Stopping JADE process (PID: {pid})...")

    if platform.system() == "Windows":
        try:
            kill_cmd = ["taskkill", "/PID", str(pid), "/F", "/T"]
            kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, check=False, 
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            
            try:
                process_info.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"JADE process (PID: {pid}) Popen status did not update within timeout after taskkill")

            final_poll_code = process_info.poll()

            if kill_result.returncode == 0:
                if final_poll_code is not None:
                    return True, "JADE terminated via taskkill"
                else:
                    try:
                        process_info.kill()
                        process_info.wait(timeout=2)
                        if process_info.poll() is not None:
                            return True, "JADE platform terminated (taskkill success, Popen inconsistent, then Popen.kill() success)"
                    except Exception as e_kill:
                        return False, f"Error during Popen.kill() after inconsistent taskkill for PID {pid}"
            elif kill_result.returncode == 128:
                if final_poll_code is not None:
                    return True, "JADE terminated (taskkill confirmed process not running)"
                else:
                    return False, f"Failed to confirm JADE termination for PID {pid}"
            else:
                error_message = kill_result.stderr.strip() or kill_result.stdout.strip()
                if final_poll_code is not None:
                    return True, f"JADE terminated (found dead after taskkill error for PID {pid}: {error_message})"
                
                try:
                    process_info.terminate()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        return True, "JADE terminated (taskkill failed, Popen.terminate() success)"
                except subprocess.TimeoutExpired:
                    pass

                try:
                    process_info.kill()
                    process_info.wait(timeout=2)
                    if process_info.poll() is not None:
                        return True, "JADE terminated (taskkill failed, Popen.kill() success)"
                except Exception as e_kill_fallback:
                    return False, f"Error during Popen.kill() fallback: {str(e_kill_fallback)}"
                
                return False, f"Failed to terminate JADE (PID: {pid}) using taskkill and Popen methods"
        except Exception as e:
            if process_info.poll() is not None:
                return True, f"JADE (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, f"Error stopping JADE process (PID: {pid}) on Windows: {str(e)}"
    else:
        try:
            process_info.terminate()
            process_info.wait(timeout=5)
            return True, "JADE terminated"
        except subprocess.TimeoutExpired:
            process_info.kill()
            try:
                process_info.wait(timeout=2)
                return True, "JADE forcefully killed"
            except subprocess.TimeoutExpired:
                return False, f"Failed to confirm JADE (PID: {pid}) termination after kill"
        except Exception as e:
            if process_info.poll() is not None:
                 return True, f"JADE (PID: {pid}) terminated (found dead after error during stop: {str(e)})"
            return False, f"Error stopping JADE process (PID: {pid}): {str(e)}"
