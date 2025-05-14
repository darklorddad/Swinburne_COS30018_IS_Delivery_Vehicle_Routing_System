import streamlit
from optimisation.backend import optimisation_logic
from . import ui_utils # Import the optimisation UI utils

# Renders the initial view of the Optimisation tab, 
# including script management, parameter configuration, and execution.
def render_initial_optimisation_view(ss):
    # Delegate rendering of the script management section
    ui_utils.render_script_management_section(ss)

    # Display of parameters and run button are now conditional on script being loaded.
    # Parameter configuration itself is moved to a separate view.
    # The "Current Script Parameters (Read-Only)" expander has been removed.
    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        # The info message about no configurable parameters has been removed as per request.
        # If parameters exist, they are edited in the "Edit Script Parameters" view.
        # No need to display them here in read-only mode.

        with streamlit.expander("Route Optimisation", expanded=True): # Renamed expander
            streamlit.markdown("---") # Divider above "Run optimisation" button
            # Action button: Run Optimisation
            run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
            if streamlit.button("Run optimisation", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True): # Renamed button
                if not ss.config_data: 
                     streamlit.error("Cannot run: Main configuration data is missing.")
                else:
                    optimisation_logic.execute_optimisation_script(ss)
                    streamlit.rerun() 
            
            # Removed divider between button and feedback message

            # Display execution results or errors
            if ss.optimisation_run_error:
                streamlit.error(f"Execution Error: {ss.optimisation_run_error}")
            
            if ss.optimisation_run_complete:
                if ss.optimisation_results is not None:
                    streamlit.success("Route optimised") # Renamed success message
                    results = ss.optimisation_results # Ensure results is defined for the check below

                    # Display "All parcels assigned" message if applicable
                    all_parcels_assigned = (
                        "optimised_routes" in results and results["optimised_routes"] and
                        not ("unassigned_parcels_details" in results and results["unassigned_parcels_details"])
                    )
                    if all_parcels_assigned:
                        streamlit.info("All parcels were assigned") # Moved and text confirmed

                    streamlit.markdown("---") # Divider between feedback message(s) and detailed results

                    # Delegate results display to the utility function
                    ui_utils.render_optimisation_results_display(results)
                        
                else: 
                     streamlit.warning("Optimisation script completed but returned no results (None).")
        
        # Expander to view the raw script content - REMOVED
        
        # Expander to view the raw optimisation output
        if ss.optimisation_run_complete and ss.optimisation_results:
            with streamlit.expander("Raw Output", expanded=False): # Renamed expander
                streamlit.markdown("---") # Added divider
                streamlit.json(ss.optimisation_results)
