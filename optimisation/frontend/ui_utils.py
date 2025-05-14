# This file is for UI utility functions specific to the Optimisation tab.
import streamlit
from optimisation.backend import optimisation_logic # Added for script management actions

# Renders the detailed display of optimisation results.
# Args:
#   results (dict): The optimisation results dictionary.
def render_optimisation_results_display(results):
    # Display results using a combination of columns for route summary and st.table for parcel details
    if "optimised_routes" in results and results["optimised_routes"]:
        for i, route in enumerate(results["optimised_routes"]):
            # Row 1: Agent ID and Total Distance
            col_agent, col_dist = streamlit.columns(2)
            with col_agent:
                streamlit.markdown("**Agent**") 
                streamlit.caption(f"{route.get('agent_id', 'N/A')}")
            with col_dist:
                streamlit.markdown("**Total Distance**")
                streamlit.caption(f"{route.get('total_distance', 'N/A')} units")
            
            # Row 2: Capacity and Stop Sequence
            col_capacity, col_seq = streamlit.columns(2) 
            with col_capacity:
                streamlit.markdown("**Capacity**") 
                streamlit.caption(f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (weight)") 
            
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

# Renders the script management section for the optimisation tab.
# Args:
#   ss (streamlit.SessionState): The current session state.
def render_script_management_section(ss):
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
