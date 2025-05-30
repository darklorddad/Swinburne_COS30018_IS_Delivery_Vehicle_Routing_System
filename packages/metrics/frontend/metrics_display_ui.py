import streamlit

def render_metrics_display(ss, final_status):
    """Renders performance metrics in a table format.
    
    Args:
        ss: Streamlit session state
        final_status: Dictionary containing workflow status info
    """
    if ss.get("performance_metrics") and final_status and final_status.get('type') == 'success':
        metrics = ss.performance_metrics
        if "error" in metrics:
            streamlit.error(f"Metrics Calculation Error: {metrics['error']}")
        else:
            # Prepare data for table display
            metrics_table_data = []
            
            # Include workflow duration if available
            if ss.get("simple_workflow_duration"):
                metrics_table_data.append({
                    "Metric": "Total Workflow Duration",
                    "Value": f"{ss.simple_workflow_duration} seconds"
                })
            
            # Add all calculated metrics    
            for key, value in metrics.items():
                label = key.replace("_", " ").title()
                metrics_table_data.append({"Metric": label, "Value": str(value)}) # Ensure value is string
        
            if metrics_table_data:
                streamlit.dataframe(
                    metrics_table_data, 
                    use_container_width=True, 
                    hide_index=True
                )
