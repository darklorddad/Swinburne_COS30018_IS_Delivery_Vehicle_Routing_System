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
                streamlit.subheader("Workflow Performance")
                streamlit.dataframe(
                    [{"Metric": "Total Workflow Duration", "Value": f"{ss.simple_workflow_duration} seconds"}],
                    use_container_width=True,
                    hide_index=True
                )
                streamlit.markdown("---")

            # Input Summary
            input_summary_metrics = [
                ("total_parcels_configured", "Total Parcels Configured"),
                ("total_agents_configured", "Total Agents Configured")
            ]
            input_summary_data = []
            for key, label in input_summary_metrics:
                if key in metrics:
                    input_summary_data.append({"Metric": label, "Value": str(metrics[key])})
            if input_summary_data:
                streamlit.subheader("Input Summary")
                streamlit.dataframe(input_summary_data, 
                    use_container_width=True, 
                    hide_index=True
                )
                streamlit.markdown("---")

            # Optimisation Effectiveness
            effectiveness_metrics = [
                ("parcels_assigned_for_delivery", "Parcels Assigned"),
                ("percentage_parcels_assigned", "Parcels Assigned (%)"), 
                ("number_of_agents_utilised", "Agents Utilised")
            ]
            effectiveness_data = []
            for key, label in effectiveness_metrics:
                if key in metrics:
                    effectiveness_data.append({"Metric": label, "Value": str(metrics[key])})
            if effectiveness_data:
                streamlit.subheader("Optimisation Effectiveness")
                streamlit.dataframe(effectiveness_data,
                    use_container_width=True,
                    hide_index=True
                )
                streamlit.markdown("---")

            # Optimisation Efficiency
            efficiency_metrics = [
                ("total_planned_distance_units", "Total Distance (units)"),
                ("average_capacity_utilisation_percentage", "Capacity Utilisation (%)")
            ]
            efficiency_data = []
            for key, label in efficiency_metrics:
                if key in metrics:
                    efficiency_data.append({"Metric": label, "Value": str(metrics[key])})
            if efficiency_data:
                streamlit.subheader("Optimisation Efficiency")
                streamlit.dataframe(efficiency_data,
                    use_container_width=True,
                    hide_index=True
                )
