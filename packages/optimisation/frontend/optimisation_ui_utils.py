import streamlit

def render_optimisation_results_display(results):
    """Displays detailed optimisation results including routes, assigned parcels, and unassigned parcels."""
    # Display results using a combination of columns for route summary and st.table for parcel details
    if "optimised_routes" in results and results["optimised_routes"]:
        for i, route in enumerate(results["optimised_routes"]):
            streamlit.subheader(f"Route for Agent: {route.get('agent_id', 'N/A')}")

            summary_data = {
                "Metric": [
                    "Agent ID",
                    "Total Distance", 
                    "Total Weight / Capacity",
                    "Stop Sequence"
                ],
                "Value": [
                    route.get('agent_id', 'N/A'),
                    f"{route.get('total_distance', 'N/A')} units",
                    f"{route.get('total_weight', 'N/A')} / {route.get('capacity_weight', 'N/A')}",
                    ' -> '.join(route.get('route_stop_ids', []))
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            streamlit.table(summary_df.set_index("Metric"))
            
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
