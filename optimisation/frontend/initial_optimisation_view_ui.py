import streamlit
# import pandas as pd # Removing pandas again
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
                    results = ss.optimisation_results # Ensure results is defined for the check below

                    # Display "All parcels assigned" message if applicable
                    all_parcels_assigned = (
                        "optimised_routes" in results and results["optimised_routes"] and
                        not ("unassigned_parcels_details" in results and results["unassigned_parcels_details"])
                    )
                    if all_parcels_assigned:
                        streamlit.info("All parcels were assigned") # Moved and text confirmed

                    streamlit.markdown("---") # Divider between feedback message(s) and detailed results

                    # Display results using a combination of columns for route summary and st.table for parcel details
                    if "optimised_routes" in results and results["optimised_routes"]:
                        for i, route in enumerate(results["optimised_routes"]):
                            # Row 1: Agent ID and Total Distance
                            col_agent, col_dist = streamlit.columns(2)
                            with col_agent:
                                streamlit.markdown("**Agent**") # Renamed
                                streamlit.caption(f"{route.get('agent_id', 'N/A')}")
                            with col_dist:
                                streamlit.markdown("**Total Distance**")
                                streamlit.caption(f"{route.get('total_distance', 'N/A')} units")
                            
                            # Row 2: Capacity and Stop Sequence
                            col_capacity, col_seq = streamlit.columns(2) 
                            with col_capacity:
                                streamlit.markdown("**Capacity**") # Renamed
                                streamlit.caption(f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (weight)") # Changed (capacity) to (weight)
                            
                            # Stop Sequence moved to be beside Capacity
                            with col_seq:
                                streamlit.markdown("**Stop Sequence**")
                                streamlit.caption(f"{' -> '.join(route.get('route_stop_ids', []))}")
                            
                            parcels_details = route.get("parcels_assigned_details", [])
                            if parcels_details:
                                # Removed streamlit.markdown("**Assigned Parcels:**")
                                table_data = []
                                for p_detail in parcels_details:
                                    coords = p_detail.get('coordinates_x_y', ['N/A', 'N/A'])
                                    coord_str = f"({coords[0]}, {coords[1]})" if isinstance(coords, list) and len(coords) == 2 else "N/A"
                                    table_data.append({
                                        "ID": p_detail.get('id', 'N/A'),
                                        "Weight": p_detail.get('weight', 'N/A'),
                                        "Coordinates": coord_str
                                    })
                                if table_data:
                                    streamlit.dataframe(table_data, use_container_width=True) # Using st.dataframe
                            else:
                                streamlit.info("No parcels assigned to this agent in this route.")
                            
                            if i < len(results["optimised_routes"]) - 1:
                                streamlit.markdown("---") # Divider between routes
                        # Removed the divider that was previously after all routes
                    
                    # Display unassigned parcels (if any, and if "All parcels assigned" was not shown)
                    if "unassigned_parcels_details" in results and results["unassigned_parcels_details"]:
                        streamlit.subheader("Unassigned Parcels")
                        unassigned_table_data = []
                        for p_detail in results["unassigned_parcels_details"]:
                            coords = p_detail.get('coordinates_x_y', ['N/A', 'N/A'])
                            coord_str = f"({coords[0]}, {coords[1]})" if isinstance(coords, list) and len(coords) == 2 else "N/A"
                            unassigned_table_data.append({
                                "ID": p_detail.get('id', 'N/A'),
                                "Weight": p_detail.get('weight', 'N/A'),
                                "Coordinates": coord_str
                            })
                        if unassigned_table_data:
                            streamlit.dataframe(unassigned_table_data, use_container_width=True) # Using st.dataframe
                    # The "elif" for "All parcels assigned" is now handled above the main results display.
                        
                else: 
                     streamlit.warning("Optimisation script completed but returned no results (None).")
