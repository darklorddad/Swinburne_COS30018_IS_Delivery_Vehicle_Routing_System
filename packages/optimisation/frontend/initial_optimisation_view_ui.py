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
            streamlit.info(f"{ss.optimisation_script_filename}")  # Moved script memory display here
            
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

# Renders the detailed display of optimisation results.
# Args:
#   results (dict): The optimisation results dictionary.
def _render_optimisation_results_display(results):
    # Display results using a combination of columns for route summary and st.table for parcel details
    if "optimised_routes" in results and results["optimised_routes"]:
        for i, route in enumerate(results["optimised_routes"]):
            # Row 1: Agent ID and Total Distance
            col_agent, col_dist = streamlit.columns(2)
            with col_agent:
                agent_id_value = route.get('agent_id', 'N/A')
                agent_text = f"<strong>Agent</strong><br><span style='font-size: 0.9em; color: #888;'>{agent_id_value}</span>"
                streamlit.markdown(agent_text, unsafe_allow_html=True)
            with col_dist:
                total_distance_value = f"{route.get('total_distance', 'N/A')} units"
                total_distance_text = f"<strong>Total Distance</strong><br><span style='font-size: 0.9em; color: #888;'>{total_distance_value}</span>"
                streamlit.markdown(total_distance_text, unsafe_allow_html=True)
            
            # Row 2: Capacity and Stop Sequence
            col_capacity, col_seq = streamlit.columns(2) 
            with col_capacity:
                # Using a span with inline styles to better mimic st.caption's appearance
                capacity_value = f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (weight)"
                capacity_text = f"<strong>Capacity</strong><br><span style='font-size: 0.9em; color: #888;'>{capacity_value}</span>"
                streamlit.markdown(capacity_text, unsafe_allow_html=True)
            
            # Stop Sequence moved to be beside Capacity
            with col_seq:
                stop_sequence_value = ' -> '.join(route.get('route_stop_ids', []))
                stop_sequence_text = f"<strong>Stop Sequence</strong><br><span style='font-size: 0.9em; color: #888;'>{stop_sequence_value}</span>"
                streamlit.markdown(stop_sequence_text, unsafe_allow_html=True)
            
            parcels_details = route.get("parcels_assigned_details", [])
            if parcels_details:
                # Removed streamlit.markdown("**Assigned Parcels:**")
                table_data = []
                for p_detail in parcels_details:
                    coords = p_detail.get('coordinates_x_y', ['N/A', 'N/A'])
                    table_data.append({
                        "id": p_detail.get('id', 'N/A'), 
                        "weight": p_detail.get('weight', 'N/A'), 
                        "coordinates_x_y": coords 
                    })
                if table_data:
                    streamlit.dataframe(table_data, use_container_width=True) 
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
            unassigned_table_data.append({
                "id": p_detail.get('id', 'N/A'), 
                "weight": p_detail.get('weight', 'N/A'), 
                "coordinates_x_y": coords 
            })
        if unassigned_table_data:
            streamlit.dataframe(unassigned_table_data, use_container_width=True) 
    # The "elif" for "All parcels assigned" is now handled above the main results display.

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
