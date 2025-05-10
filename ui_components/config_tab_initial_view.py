import streamlit
import app_logic

def render_initial_view(ss):
    """Renders the initial view of the Configuration tab."""
    with streamlit.expander("Create or Load Configuration", expanded=True):
        streamlit.markdown("---")
        col_create_btn, col_load_btn = streamlit.columns(2)
        with col_create_btn:
            if streamlit.button("New configuration", key="create_new_config_action_btn", help="Create a new configuration", use_container_width=True):
                app_logic.handle_new_config_action(ss)
                streamlit.rerun()
        
        with col_load_btn:
            if streamlit.button("Load configuration", key="load_config_action_btn", help="Load configuration by uploading a JSON configuration file", use_container_width=True):
                app_logic.handle_load_config_action(ss)
                streamlit.rerun()
    
    # Option to edit if a configuration is in memory
    if ss.config_data is not None:
        with streamlit.expander("Manage Current Configuration", expanded=True):
             streamlit.markdown("---")
             config_status_message = f"A loaded configuration ('{ss.config_filename}') is in memory" \
                 if ss.last_uploaded_filename is not None \
                 else f"A new configuration ('{ss.config_filename}') is in memory"
             streamlit.info(config_status_message)
             if streamlit.button("Edit configuration", key="edit_config_btn", use_container_width=True): # Unified edit button
                 app_logic.enter_edit_mode(ss)
                 streamlit.rerun()
            
             # Option to clear memory (this is still inside the outer "if ss.config_data is not None:")
             if streamlit.button("Clear configuration from memory", key="clear_memory_btn", use_container_width=True, help="Removes any loaded or new configuration from the current session"):
                result = app_logic.clear_config_from_memory(ss)
                if result and result.get('message'):
                    streamlit.info(result['message'])
                streamlit.rerun()
