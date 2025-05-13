import streamlit
from optimisation.backend import optimisation_logic

# Renders the initial view of the Optimisation tab, 
# including script management, parameter configuration, and execution.
def render_initial_optimisation_view(ss):
    with streamlit.expander("Manage Optimisation Script", expanded = True):
        streamlit.markdown("---")

        if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
            streamlit.success(f"Script '{ss.optimisation_script_filename}' loaded successfully.")
            
            col_edit_params, col_clear_script = streamlit.columns(2)
            with col_edit_params:
                if streamlit.button("Edit Script Parameters", key="edit_script_parameters_btn", use_container_width=True, help="Edit the parameters for the loaded script."):
                    optimisation_logic.handle_edit_parameters_action(ss)
                    streamlit.rerun()
            with col_clear_script:
                if streamlit.button("Clear script from memory", key="clear_optimisation_script_initial_view_btn", use_container_width=True, help="Clears the loaded script and its parameters."):
                    optimisation_logic.clear_optimisation_script(ss)
                    streamlit.rerun()
            streamlit.markdown("---") # Separator before load new script button

        elif ss.optimisation_script_error_message and not ss.optimisation_script_loaded_successfully:
            streamlit.error(ss.optimisation_script_error_message)
            # Still show load script button below if there was an error

        # Button to load a script (new or replace existing)
        load_button_text = "Load New Optimisation Script" if not ss.optimisation_script_loaded_successfully else "Load Another Optimisation Script"
        load_button_help = "Load a Python script for optimisation." if not ss.optimisation_script_loaded_successfully else "Replace the current script with a new one."
        if streamlit.button(load_button_text, key="initiate_load_script_btn", use_container_width=True, help=load_button_help):
            optimisation_logic.handle_initiate_load_script_action(ss)
            streamlit.rerun()

    # Display of parameters and run button are now conditional on script being loaded,
    # but parameter configuration itself is moved to a separate view.
    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        # Display current parameters (read-only summary) if any are defined
        if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema and ss.optimisation_script_param_schema["parameters"]:
            with streamlit.expander("Current Script Parameters (Read-Only)", expanded=False):
                # Display user_values as a list or formatted string for quick review
                if ss.optimisation_script_user_values:
                    for name, value in ss.optimisation_script_user_values.items():
                        # Try to find label from schema for better display
                        param_label = name
                        for p_info in ss.optimisation_script_param_schema.get("parameters", []):
                            if p_info.get("name") == name:
                                param_label = p_info.get("label", name)
                                break
                        streamlit.text(f"{param_label}: {value}")
                else:
                    streamlit.caption("No parameters values set or available.")
        elif ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema and not ss.optimisation_script_param_schema["parameters"]:
             streamlit.info("The loaded script does not define any configurable parameters.")
        # else: schema might be missing, error handled in manage section or load process

        # Action button: Run Optimisation
        run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
        if streamlit.button("Run Optimisation Script", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True, help = "Runs the loaded script with current configuration and parameters."):
            if not ss.config_data: 
                 streamlit.error("Cannot run: Main configuration data is missing.")
            else:
                optimisation_logic.execute_optimisation_script(ss)
                streamlit.rerun() 
        
        # Display execution results or errors
        if ss.optimisation_run_error:
            streamlit.error(f"Execution Error: {ss.optimisation_run_error}")
        if ss.optimisation_run_complete:
            if ss.optimisation_results is not None:
                streamlit.success("Optimisation script executed successfully!")
                with streamlit.expander("Optimisation Results", expanded = True):
                    streamlit.json(ss.optimisation_results)
            else: 
                 streamlit.warning("Optimisation script completed but returned no results (None).")

    elif not ss.optimisation_script_loaded_successfully and not ss.optimisation_script_error_message: 
        # No script loaded and no persistent error message shown in manage section
        streamlit.caption("Click 'Load New Optimisation Script' to begin configuring an optimisation technique.")
