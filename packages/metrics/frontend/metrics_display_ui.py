import streamlit

def render_metrics_display(ss, final_status):
    """Renders performance metrics in a logical grouped format.
    
    Args:
        ss: Streamlit session state
        final_status: Dictionary containing workflow status info
    """
    if ss.get("performance_metrics") and final_status and final_status.get('type') == 'success':
        metrics = ss.performance_metrics
        if "error" in metrics:
            streamlit.error(f"Metrics Calculation Error: {metrics['error']}")
        else:
            # Include workflow duration if available
            if ss.get("simple_workflow_duration"):
                streamlit.dataframe(
                    [{"Workflow performance": "Total workflow duration", "Value": f"{ss.simple_workflow_duration} seconds"}],
                    use_container_width=True,
                    hide_index=True
                )

            # Input Summary
            input_summary_metrics = [
                ("total_parcels_configured", "Total parcels configured"),
                ("total_agents_configured", "Total agents configured")
            ]
            input_summary_data = []
            for key, label in input_summary_metrics:
                if key in metrics:
                    input_summary_data.append({"Input summary": label, "Value": str(metrics[key])})
            if input_summary_data:
                streamlit.dataframe(input_summary_data, 
                    use_container_width=True, 
                    hide_index=True
                )

            # Optimisation Effectiveness
            effectiveness_metrics = [
                ("parcels_assigned_for_delivery", "Parcels assigned"),
                ("percentage_parcels_assigned", "Parcels assigned (%)"), 
                ("number_of_agents_utilised", "Agents utilised")
            ]
            effectiveness_data = []
            for key, label in effectiveness_metrics:
                if key in metrics:
                    effectiveness_data.append({"Optimisation effectiveness": label, "Value": str(metrics[key])})
            if effectiveness_data:
                streamlit.dataframe(effectiveness_data,
                    use_container_width=True,
                    hide_index=True
                )

            # Optimisation Efficiency
            efficiency_metrics = [
                ("total_planned_distance_units", "Total distance (units)"),
                ("average_capacity_utilisation_percentage", "Capacity utilisation (%)")
            ]
            efficiency_data = []
            for key, label in efficiency_metrics:
                if key in metrics:
                    efficiency_data.append({"Optimisation efficiency": label, "Value": str(metrics[key])})
            if efficiency_data:
                streamlit.dataframe(efficiency_data,
                    use_container_width=True,
                    hide_index=True
                )
