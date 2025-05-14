import streamlit
import pandas as pd # Re-introducing pandas for st.dataframe
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
                    streamlit.markdown("---") # Divider between feedback message and results

                    # Display results using a combination of columns for route summary and st.dataframe for parcel details
                    results = ss.optimisation_results
                    
                    if "optimised_routes" in results and results["optimised_routes"]:
                        for i, route in enumerate(results["optimised_routes"]):
                            streamlit.markdown(f"#### Route for Agent: {route.get('agent_id', 'N/A')}")
                            
                            col1, col2 = streamlit.columns(2)
                            with col1:
                                streamlit.markdown("**Total Distance**")
                                streamlit.markdown(f"{route.get('total_distance', 'N/A')} units")
                            with col2:
                                streamlit.markdown("**Carried Weight**")
                                streamlit.markdown(f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (capacity)")
                            
                            streamlit.markdown("**Stop Sequence**")
                            streamlit.markdown(f"{' -> '.join(route.get('route_stop_ids', []))}")
                            
                            parcels_details = route.get("parcels_assigned_details", [])
                            if parcels_details:
                                streamlit.markdown("**Assigned Parcels:**")
                                display_data = []
                                for p_detail in parcels_details:
                                    coords = p_detail.get('coordinates_x_y', ['N/A', 'N/A'])
                                    coord_str = f"({coords[0]}, {coords[1]})" if isinstance(coords, list) and len(coords) == 2 else "N/A"
                                    display_data.append({
                                        "ID": p_detail.get('id', 'N/A'),
                                        "Weight": p_detail.get('weight', 'N/A'),
                                        "Coordinates": coord_str
                                    })
                                if display_data:
                                    # Using DataFrame for a look similar to Configuration tab tables
                                    df = pd.DataFrame(display_data)
                                    streamlit.dataframe(df.set_index("ID") if "ID" in df.columns else df, use_container_width=True)
                            else:
                                streamlit.info("No parcels assigned to this agent in this route.")
                            
                            if i < len(results["optimised_routes"]) - 1:
                                streamlit.markdown("---") # Divider between routes
                        streamlit.markdown("---") # Divider after all routes
                    
                    if "unassigned_parcels_details" in results and results["unassigned_parcels_details"]:
                        streamlit.subheader("Unassigned Parcels")
                        unassigned_display_data = []
                        for p_detail in results["unassigned_parcels_details"]:
                            coords = p_detail.get('coordinates_x_y', ['N/A', 'N/A'])
                            coord_str = f"({coords[0]}, {coords[1]})" if isinstance(coords, list) and len(coords) == 2 else "N/A"
                            unassigned_display_data.append({
                                "ID": p_detail.get('id', 'N/A'),
                                "Weight": p_detail.get('weight', 'N/A'),
                                "Coordinates": coord_str
                            })
                        if unassigned_display_data:
                            df_unassigned = pd.DataFrame(unassigned_display_data)
                            streamlit.dataframe(df_unassigned.set_index("ID") if "ID" in df_unassigned.columns else df_unassigned, use_container_width=True)
                    elif "optimised_routes" in results: # Only show if routes were processed
                        streamlit.info("All parcels were assigned.")
                        
                else: 
                     streamlit.warning("Optimisation script completed but returned no results (None).")
