import streamlit
from packages.optimisation.backend import optimisation_logic

# --- Helper UI Rendering Functions (moved from ui_utils.py) ---

# Renders the script management section for the optimisation tab.
# Args:
#   ss (streamlit.SessionState): The current session state.
def _render_script_management_section(ss):
    with streamlit.expander("Manage Optimisation Script", expanded = True):
        streamlit.markdown("---")

        if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
            # Display current parameters in a table
            if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema:
                params_list = ss.optimisation_script_param_schema["parameters"]
                if params_list:
                    table_data = []
                    for param in params_list:
                        table_data.append({
                            "Parameter": param.get("label", param.get("name", "")),
                            "Type": param.get("type", ""),
                            "Value": str(ss.optimisation_script_user_values.get(param["name"], "")),
                            "Description": param.get("help", "")
                        })
                    streamlit.dataframe(
                        table_data,
                        use_container_width=True,
                        column_config={
                            "Parameter": "Parameter",
                            "Type": "Type",
                            "Value": "Current Value", 
                            "Description": "Description"
                        }
                    )
                else:
                    streamlit.info("No configurable parameters defined in this script")
            
            streamlit.markdown("---")  # Divider before script management buttons
            streamlit.success(f"{ss.optimisation_script_filename}")
            
            # "Load Another Optimisation Script" button moved here
            if streamlit.button("Load script", key="initiate_load_another_script_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()
            
            if streamlit.button("Edit parameters", key="edit_script_parameters_btn", use_container_width=True):
                optimisation_logic.handle_edit_parameters_action(ss)
                streamlit.rerun()
            
            if streamlit.button("Clear script", key="clear_optimisation_script_initial_view_btn", use_container_width=True):
                optimisation_logic.clear_optimisation_script(ss)
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

from .optimisation_ui_utils import render_optimisation_results_display as _render_optimisation_results_display

# --- Main Rendering Function for Initial Optimisation View ---

# Renders the initial view of the Optimisation tab, 
# including script management, parameter configuration, and execution.
def render_initial_optimisation_view(ss):
    # Delegate rendering of the script management section
    _render_script_management_section(ss)

    # Display of parameters and run button are now conditional on script being loaded.
    # Parameter configuration itself is moved to a separate view.
    # The "Current Script Parameters (Read-Only)" expander has been removed.
    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        # The info message about no configurable parameters has been removed as per request.
        # If parameters exist, they are edited in the "Edit Script Parameters" view.
        # No need to display them here in read-only mode.
        
        # The "Route Optimisation" expander and "Raw Output" expander have been removed from this view.
        # Their functionalities are moved to the Execution tab.
        pass
