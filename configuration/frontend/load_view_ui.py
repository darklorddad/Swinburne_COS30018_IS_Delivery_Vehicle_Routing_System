import streamlit
from packages.configuration.backend import config_logic
from .ui_utils import display_operation_result

# Renders the 'Load Configuration' view.
def render_load_view(ss):
    with streamlit.expander("Upload Configuration File", expanded = True):
        streamlit.markdown("---")
        # File uploader now stores to a buffer, managed by on_change.
        streamlit.file_uploader(
            "Select a JSON configuration file to prepare for loading",
            type = ["json"],
            key = "config_uploader_buffer_widget",
            on_change = config_logic.handle_file_uploader_change,
            args = (ss,)
        )
        # Direct buffer manipulation logic removed

    # Buttons for Load View - Cancel on left, Load on right
    col_cancel_load_action, col_load_action = streamlit.columns([1,1])

    with col_cancel_load_action:
        if streamlit.button("Cancel", key = "cancel_load_action_btn", use_container_width = True):
            config_logic.handle_cancel_load_action(ss)
            streamlit.rerun()

    with col_load_action:
        load_disabled = ss.uploaded_file_buffer is None
        if streamlit.button("Load selected configuration", key = "confirm_load_btn", use_container_width = True, disabled = load_disabled):
            result = config_logic.confirm_load_configuration(ss)
            if display_operation_result(result):
                # Rerun for most outcomes of confirm_load_configuration
                if result and (
                    result.get('type') in ['success', 'info'] or
                    (result.get('type') == 'error' and "Ensure it's valid JSON" in result.get('message', '')) or
                    (result.get('type') == 'warning' and "already processed" in result.get('message', ''))
                ):
                    streamlit.rerun()
