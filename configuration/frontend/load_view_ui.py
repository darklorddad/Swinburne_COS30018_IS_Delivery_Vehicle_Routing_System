import streamlit
import backend.config_logic

def render_load_view(ss):
    """Renders the 'Load Configuration' view."""
    with streamlit.expander("Upload Configuration File", expanded=True):
        streamlit.markdown("---")
        # File uploader now stores to a buffer, managed by on_change
        streamlit.file_uploader(
            "Select a JSON configuration file to prepare for loading",
            type=["json"],
            key="config_uploader_buffer_widget",
            on_change=backend.config_logic.handle_file_uploader_change
        )
        # Direct buffer manipulation logic removed

    # Buttons for Load View - Cancel on left, Load on right
    col_cancel_load_action, col_load_action = streamlit.columns([1,1])

    with col_cancel_load_action:
        if streamlit.button("Cancel", key="cancel_load_action_btn", use_container_width=True):
            backend.config_logic.handle_cancel_load_action(ss)
            streamlit.rerun()

    with col_load_action:
        load_disabled = ss.uploaded_file_buffer is None
        if streamlit.button("Load selected configuration", key="confirm_load_btn", use_container_width=True, disabled=load_disabled):
            result = backend.config_logic.confirm_load_configuration(ss)
            if result:
                if result['type'] == 'success':
                    streamlit.success(result['message'])
                elif result['type'] == 'error':
                    streamlit.error(result['message'])
                elif result['type'] == 'info':
                    streamlit.info(result['message'])
                elif result['type'] == 'warning':
                    streamlit.warning(result['message'])
                # Rerun for most outcomes of confirm_load_configuration
                if result['type'] in ['success', 'info'] or \
                   (result['type'] == 'error' and "Ensure it's valid JSON" in result['message']) or \
                   (result['type'] == 'warning' and "already processed" in result['message']):
                    streamlit.rerun()
