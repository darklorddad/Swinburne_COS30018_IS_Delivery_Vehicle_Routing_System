import subprocess
import os
import platform

def compile_java_agents(source_path, output_classes_path, jade_jar_path, py4j_jar_path, json_jar_path):
    print("Attempting to compile JADE agent Java source files...")
    
    try:
        os.makedirs(source_path, exist_ok=True)
        os.makedirs(output_classes_path, exist_ok=True)
    except Exception as e:
        return False, f"Error creating directories: {str(e)}"

    if not os.path.exists(jade_jar_path):
        return False, f"JADE JAR not found at '{jade_jar_path}'"
    if not os.path.exists(py4j_jar_path):
        return False, f"Py4J JAR not found at '{py4j_jar_path}'"
    if not os.path.exists(json_jar_path):
        return False, f"org.json.jar not found at '{json_jar_path}'"

    java_source_files = [f for f in os.listdir(source_path) if f.endswith(".java")]
    if not java_source_files:
        return False, f"No Java source files found in '{source_path}'"

    classpath_separator = ";" if platform.system() == "Windows" else ":"
    compile_classpath = f"{jade_jar_path}{classpath_separator}{py4j_jar_path}{classpath_separator}{json_jar_path}"

    javac_cmd = [
        "javac",
        "-cp", compile_classpath,
        "-d", os.path.normpath(output_classes_path),
        "-sourcepath", os.path.normpath(source_path),
        os.path.normpath(os.path.join(source_path, "*.java"))
    ]

    try:
        result = subprocess.run(javac_cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            return True, "JADE agents compiled successfully"
        else:
            error_output = result.stderr if result.stderr else result.stdout
            return False, f"Compilation failed (exit code {result.returncode}):\n{error_output}"
            
    except FileNotFoundError:
        return False, "javac command not found. Is Java Development Kit (JDK) installed?"
    except Exception as e:
        return False, f"Unexpected error during compilation: {str(e)}"
