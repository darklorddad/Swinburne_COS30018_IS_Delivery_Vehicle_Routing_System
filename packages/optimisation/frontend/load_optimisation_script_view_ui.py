import streamlit
from packages.optimisation.backend import optimisation_logic

# Renders the view for uploading and loading an optimisation script.
def render_load_optimisation_script_view(ss):
    with streamlit.expander("Upload Optimisation Script", expanded = True):
        streamlit.markdown("---")
        streamlit.file_uploader(
            "Select a Python optimisation script to prepare for loading",
            type = ["py"],
            key = "optimisation_file_uploader_widget",
        )

    # Display error message from script loading attempt if any
    if ss.optimisation_script_error_message:
        streamlit.error(ss.optimisation_script_error_message)

    col_cancel, col_load = streamlit.columns(2) # Buttons inverted: Cancel on left, Load on right
    with col_cancel: # Cancel button now on the left
        if streamlit.button("Cancel", key = "cancel_load_script_btn", use_container_width = True):
            optimisation_logic.handle_cancel_load_script_action(ss)
            if ss.get("simple_mode"):
                ss.simple_config_action_selected = None  # Clear the action to return to main simple view
            else:
                ss.optimisation_action_selected = None  # Clear the action for standard mode
            streamlit.rerun()

    with col_load: # Load button now on the right
        load_script_button_disabled = ss.get("optimisation_file_uploader_widget") is None
        if streamlit.button("Load selected script", 
                            key = "load_optimisation_script_button", 
                            use_container_width = True, 
                            disabled = load_script_button_disabled):
            # handle_optimisation_file_upload will set error messages or transition state
            success = optimisation_logic.handle_optimisation_file_upload(ss)
            if success:
                if ss.get("simple_mode"):
                    ss.simple_config_action_selected = None  # Clear the action to return to main simple view
                else:
                    ss.optimisation_action_selected = None  # Clear the action for standard mode
                # Clear the file uploader widget to reset the UI for next time
                if 'optimisation_file_uploader_widget' in ss:
                    del ss.optimisation_file_uploader_widget
            # Rerun to reflect state changes (either error message or transition to initial view)
            streamlit.rerun()
