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
            # handle_optimisation_file_upload will set error messages,
            # set ss.optimisation_action_selected = None on success (for standard mode nav),
            # and return success status.
            success = optimisation_logic.handle_optimisation_file_upload(ss)
            if success:
                # For standard mode, ss.optimisation_action_selected = None (set by backend)
                # will correctly navigate back to the initial optimisation view.

                if ss.get("simple_mode"):
                    # For simple mode, we also need to ensure its specific action state is cleared
                    # to return to the main simple view.
                    ss.simple_config_action_selected = None  
                
                # Clear the file uploader widget after successful processing in both modes
                if 'optimisation_file_uploader_widget' in ss:
                    del ss.optimisation_file_uploader_widget
                
                # Rerun to reflect changes 
                # (navigation in standard mode, navigation in simple mode, or cleared widget)
                streamlit.rerun()
            else:
                # If not successful, an error message is set in ss.
                # Rerun to display the error and stay on the load script page.
                streamlit.rerun()
