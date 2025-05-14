import streamlit
import pandas as pd # Added for displaying results in a table
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

        with streamlit.expander("Execute Optimisation & View Plan", expanded=True): # Renamed expander
            # Action button: Run Optimisation
            run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
            if streamlit.button("Run optimisation", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True): # Renamed button
                if not ss.config_data: 
                     streamlit.error("Cannot run: Main configuration data is missing.")
                else:
                    optimisation_logic.execute_optimisation_script(ss)
                    streamlit.rerun() 
            
            streamlit.markdown("---") # Divider between button and feedback message

            # Display execution results or errors
            if ss.optimisation_run_error:
                streamlit.error(f"Execution Error: {ss.optimisation_run_error}")
            
            if ss.optimisation_run_complete:
                if ss.optimisation_results is not None:
                    streamlit.success("Route optimised") # Renamed success message
                    streamlit.markdown("---") # Divider between feedback message and results

                    # Display results using tables/dataframes
                    results = ss.optimisation_results
                    
                    if "optimised_routes" in results and results["optimised_routes"]:
                        streamlit.subheader("Optimised Routes")
                        for i, route in enumerate(results["optimised_routes"]):
                            streamlit.markdown(f"**Agent:** {route.get('agent_id', 'N/A')}")
                            streamlit.text(f"Stop Sequence: {' -> '.join(route.get('route_stop_ids', []))}")
                            streamlit.text(f"Total Distance: {route.get('total_distance', 'N/A')} units")
                            streamlit.text(f"Carried Weight: {route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (capacity)")
                            
                            parcels_details = route.get("parcels_assigned_details", [])
                            if parcels_details:
                                streamlit.markdown("Assigned Parcels:")
                                parcels_df = pd.DataFrame(parcels_details)
                                # Ensure essential columns exist, provide defaults if not for display
                                display_cols = {}
                                for col in ['id', 'weight', 'coordinates_x_y']:
                                    if col in parcels_df.columns:
                                        display_cols[col] = parcels_df[col]
                                    else:
                                        # Create a series of N/A if column is missing
                                        display_cols[col] = pd.Series(["N/A"] * len(parcels_df), name=col) 
                                
                                display_df = pd.DataFrame(display_cols)
                                if 'coordinates_x_y' in display_df.columns: # Prettify coordinates
                                     display_df['coordinates_x_y'] = display_df['coordinates_x_y'].apply(lambda x: f"({x[0]}, {x[1]})" if isinstance(x, list) and len(x)==2 else "N/A")
                                streamlit.dataframe(display_df, use_container_width=True)
                            else:
                                streamlit.info("No parcels assigned to this agent in this route.")
                            if i < len(results["optimised_routes"]) - 1:
                                streamlit.markdown("---") # Divider between routes
                        streamlit.markdown("---") # Divider after all routes
                    
                    if "unassigned_parcels_details" in results and results["unassigned_parcels_details"]:
                        streamlit.subheader("Unassigned Parcels")
                        unassigned_df = pd.DataFrame(results["unassigned_parcels_details"])
                        display_cols_unassigned = {}
                        for col in ['id', 'weight', 'coordinates_x_y']:
                             if col in unassigned_df.columns:
                                 display_cols_unassigned[col] = unassigned_df[col]
                             else:
                                 display_cols_unassigned[col] = pd.Series(["N/A"] * len(unassigned_df), name=col)
                        
                        display_df_unassigned = pd.DataFrame(display_cols_unassigned)
                        if 'coordinates_x_y' in display_df_unassigned.columns: # Prettify coordinates
                             display_df_unassigned['coordinates_x_y'] = display_df_unassigned['coordinates_x_y'].apply(lambda x: f"({x[0]}, {x[1]})" if isinstance(x, list) and len(x)==2 else "N/A")
                        streamlit.dataframe(display_df_unassigned, use_container_width=True)
                    elif "optimised_routes" in results: # Only show if routes were processed
                        streamlit.info("All parcels were assigned.")
                        
                else: 
                     streamlit.warning("Optimisation script completed but returned no results (None).")
