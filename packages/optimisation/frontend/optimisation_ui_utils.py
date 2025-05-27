import streamlit
import pandas as pd

def render_optimisation_results_display(results):
    """Displays detailed optimisation results including routes, assigned parcels, and unassigned parcels."""
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
                capacity_value = f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')} (weight)"
                capacity_text = f"<strong>Capacity</strong><br><span style='font-size: 0.9em; color: #888;'>{capacity_value}</span>"
                streamlit.markdown(capacity_text, unsafe_allow_html=True)
            
            with col_seq:
                stop_sequence_value = ' -> '.join(route.get('route_stop_ids', []))
                stop_sequence_text = f"<strong>Stop Sequence</strong><br><span style='font-size: 0.9em; color: #888;'>{stop_sequence_value}</span>"
                streamlit.markdown(stop_sequence_text, unsafe_allow_html=True)
            
            parcels_details = route.get("parcels_assigned_details", [])
            if parcels_details:
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
