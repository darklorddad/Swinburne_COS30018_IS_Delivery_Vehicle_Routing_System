import streamlit
from optimisation.backend import optimisation_logic

# Renders the initial view of the Optimisation tab, 
# including script management, parameter configuration, and execution.
def render_initial_optimisation_view(ss):
    with streamlit.expander("Manage Optimisation Script", expanded = True):
        streamlit.markdown("---")

        if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
            streamlit.success(f"{ss.optimisation_script_filename}")
            col_edit_btn, col_clear_btn = streamlit.columns(2)
            
            with col_edit_btn:
                if streamlit.button("Edit script", key="edit_script_parameters_btn", use_container_width=True):
                    optimisation_logic.handle_edit_parameters_action(ss)
                    streamlit.rerun()
            
            with col_clear_btn:
                if streamlit.button("Clear script", key="clear_optimisation_script_initial_view_btn", use_container_width=True):
                    optimisation_logic.clear_optimisation_script(ss)
                    streamlit.rerun()
            
            # "Load Another Optimisation Script" button moved here
            if streamlit.button("Load script", key="initiate_load_another_script_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()

        elif ss.optimisation_script_error_message and not ss.optimisation_script_loaded_successfully:
            streamlit.error(ss.optimisation_script_error_message)
            # Still show "Load New Optimisation Script" button below if there was an error and no script is loaded
            if streamlit.button("Load script", key="initiate_load_script_error_case_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()

        elif not ss.optimisation_script_loaded_successfully: # No script loaded, no error message shown yet
            # Button to load a new script
            if streamlit.button("Load script", key="initiate_load_script_no_script_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()

    # Display of parameters and run button are now conditional on script being loaded.
    # Parameter configuration itself is moved to a separate view.
    # The "Current Script Parameters (Read-Only)" expander has been removed.
    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        # Information about parameters (if any)
        if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema and not ss.optimisation_script_param_schema["parameters"]:
             streamlit.info("The loaded script does not define any configurable parameters.")
        # If parameters exist, they are edited in the "Edit Script Parameters" view.
        # No need to display them here in read-only mode as per new request.

        with streamlit.expander("Run Optimisation and View Results", expanded=True):
            # Action button: Run Optimisation
            run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
            if streamlit.button("Run Optimisation Script", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True):
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
                    # This inner expander will now be nested
                    with streamlit.expander("Optimisation Results", expanded = True):
                        streamlit.json(ss.optimisation_results)
                else: 
                     streamlit.warning("Optimisation script completed but returned no results (None).")
