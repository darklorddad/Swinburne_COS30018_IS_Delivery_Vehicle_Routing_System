import streamlit
from optimisation.backend import optimisation_logic

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

    col_load, col_cancel = streamlit.columns(2) # Swapped columns
    with col_load: # Load button now on the left
        load_script_button_disabled = ss.get("optimisation_file_uploader_widget") is None
        if streamlit.button("Load selected script", 
                            key = "load_optimisation_script_button", 
                            use_container_width = True, 
                            disabled = load_script_button_disabled):
            # handle_optimisation_file_upload will set error messages or transition state
            optimisation_logic.handle_optimisation_file_upload(ss)
            # Rerun to reflect state changes (either error message or transition to initial view)
            streamlit.rerun()

    with col_cancel: # Cancel button now on the right
        if streamlit.button("Cancel", key = "cancel_load_script_btn", use_container_width = True):
            optimisation_logic.handle_cancel_load_script_action(ss)
            streamlit.rerun()
