import importlib.util
import sys
import os
import tempfile
import shutil

# Helper to load a Python script content as a module.
# Manages temporary file creation and basic module loading.
def _load_module_from_string(script_content, module_name_prefix="user_opt_script"):
    temp_dir = tempfile.mkdtemp()
    module_name = f"{module_name_prefix}_{os.path.basename(temp_dir)}" # Unique module name
    temp_file_path = os.path.join(temp_dir, f"{module_name}.py")

    try:
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        spec = importlib.util.spec_from_file_location(module_name, temp_file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_name}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module # Add to sys.modules before exec_module
        
        spec.loader.exec_module(module)
    except Exception as e:
        # If any error occurs during file writing, spec creation, or module execution,
        # ensure cleanup of the temp directory and module from sys.modules.
        if module_name in sys.modules:
            del sys.modules[module_name]
        if os.path.isdir(temp_dir): # Check if temp_dir was created
            shutil.rmtree(temp_dir)
        raise e # Re-raise the original exception

    # Return module, its name, and temp_dir for caller to manage (especially for cleanup)
    return module, module_name, temp_dir

# Cleans up resources (temp directory, loaded module) for a dynamically loaded script.
def cleanup_script_module(module_name, temp_dir):
    if module_name and module_name in sys.modules:
        del sys.modules[module_name]
    if temp_dir and os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
