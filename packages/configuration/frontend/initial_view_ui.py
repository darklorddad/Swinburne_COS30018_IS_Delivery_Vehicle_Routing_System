import streamlit
from packages.configuration.backend import config_logic
from .ui_utils import display_operation_result # Import the utility function

# Renders the initial view of the Configuration tab.
def render_initial_view(ss):
    with streamlit.expander("Create or Load Configuration", expanded = True):
        streamlit.markdown("---")
        # New Configuration button at top
        if streamlit.button("New configuration", key = "create_new_config_action_btn", use_container_width = True):
            config_logic.handle_new_config_action(ss)
            streamlit.rerun()
            
        # Load Configuration button at bottom
        if streamlit.button("Load configuration", key = "load_config_action_btn", use_container_width = True):
            config_logic.handle_load_config_action(ss)
            streamlit.rerun()

    # Option to edit if a configuration is in memory
    if ss.config_data is not None:
        with streamlit.expander("Manage Current Configuration", expanded = True):
            streamlit.markdown("---")
            
            if ss.config_data.get("parcels"):
                streamlit.dataframe(ss.config_data["parcels"], use_container_width=True)
            else:
                streamlit.info("No parcels currently defined in the configuration.")
            
            if ss.config_data.get("delivery_agents"):
                streamlit.dataframe(ss.config_data["delivery_agents"], use_container_width=True)
            else:
                streamlit.info("No delivery agents currently defined in the configuration.")

            streamlit.markdown("---")
            
            config_status_message = (f"{ss.config_filename}")
            streamlit.success(config_status_message)
            if streamlit.button("Edit configuration", key = "edit_config_btn", use_container_width = True):
                config_logic.enter_edit_mode(ss)
                streamlit.rerun()
            
            if streamlit.button("Clear configuration", key = "clear_memory_btn", use_container_width = True):
                result = config_logic.clear_config_from_memory(ss)
                display_operation_result(result) # Use the utility function to display the message
                streamlit.rerun()
