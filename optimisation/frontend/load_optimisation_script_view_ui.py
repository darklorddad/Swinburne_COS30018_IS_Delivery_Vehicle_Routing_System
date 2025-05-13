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
            help = "The script must be UTF-8 encoded and contain 'get_params_schema()' and 'run_optimisation(config_data, params)' functions."
        )

    # Display error message from script loading attempt if any
    if ss.optimisation_script_error_message:
        streamlit.error(ss.optimisation_script_error_message)

    col_cancel, col_load = streamlit.columns(2)
    with col_cancel:
        if streamlit.button("Cancel", key = "cancel_load_script_btn", use_container_width = True):
            optimisation_logic.handle_cancel_load_script_action(ss)
            streamlit.rerun()
    
    with col_load:
        load_script_button_disabled = ss.get("optimisation_file_uploader_widget") is None
        if streamlit.button("Load selected script", 
                            key = "load_optimisation_script_button", 
                            use_container_width = True, 
                            disabled = load_script_button_disabled,
                            help = "Load the script selected in the uploader above. The button is disabled if no script is selected."):
            # handle_optimisation_file_upload will set error messages or transition state
            optimisation_logic.handle_optimisation_file_upload(ss)
            # Rerun to reflect state changes (either error message or transition to initial view)
            streamlit.rerun()
