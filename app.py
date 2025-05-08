import streamlit
import json # Though primarily used by config_manager, good for type hints or direct use if needed
import config_manager # Our new module for backend config logic

def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state variables
    if "show_header" not in streamlit.session_state:
        streamlit.session_state.show_header = False # Default is off (header hidden)
    if "config_data" not in streamlit.session_state:
        streamlit.session_state.config_data = None
    if "config_filename" not in streamlit.session_state:
        streamlit.session_state.config_filename = "config.json" # Default for download
    if "config_edit_buffer" not in streamlit.session_state:
        # This buffer will hold the string version of the config for the text_area
        streamlit.session_state.config_edit_buffer = ""
    if "config_editor_key" not in streamlit.session_state:
        # This will store the live content of the text_area, updated by user input
        streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer


    # Dynamically build CSS based on header visibility state
    header_style_properties = "background-color: #1E1E1E !important;" # Always set background color

    if not streamlit.session_state.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /* Set a darker background color for the app */
        .stApp {{
            background-color: #1E1E1E !important;
        }}
    </style>
    """

    streamlit.markdown(custom_css, unsafe_allow_html = True)

    # Create columns to center the main content
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        streamlit.title("Delivery Vehicle Routing System")

        tab_config, tab_run, tab_results, tab_settings = streamlit.tabs([
            "Configuration",
            "Run Optimization",
            "Dashboard & Results",
            "Settings"
        ])

        with tab_config:
            streamlit.header("Configuration Management")
            
            uploaded_file = streamlit.file_uploader(
                "Upload Configuration File (JSON)", type=["json"], key="config_uploader"
            )

            if uploaded_file is not None:
                # Process uploaded file only once or if it changes
                # Note: Streamlit reruns script on widget interaction.
                # A common pattern is to process file then set it to None or use a flag.
                # For simplicity here, we process if uploaded_file is present.
                # Consider adding a button "Load selected file" for more control.
                
                # To prevent reprocessing on every rerun if file is already loaded and shown:
                # Check if this is a new upload or if config_data is already from this file.
                # This simple check might not be perfect for all scenarios.
                # A more robust way is to store a hash or timestamp of the loaded file.
                if streamlit.session_state.config_data is None or \
                   streamlit.session_state.get("last_uploaded_filename") != uploaded_file.name:

                    loaded_config = config_manager.load_config_from_uploaded_file(uploaded_file)
                    if loaded_config is not None:
                        streamlit.session_state.config_data = loaded_config
                        streamlit.session_state.config_filename = uploaded_file.name
                        streamlit.session_state.config_edit_buffer = config_manager.config_to_json_string(loaded_config)
                        streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer # Initialize text area content
                        streamlit.session_state.last_uploaded_filename = uploaded_file.name # Track last loaded file
                        streamlit.success(f"Configuration '{uploaded_file.name}' loaded successfully.")
                        # Force a rerun to update the text_area with the new value,
                        # if not already handled by Streamlit's flow for session_state changes.
                        # streamlit.experimental_rerun() # Usually not needed if state change correctly triggers UI update
                    else:
                        streamlit.error(f"Failed to load or parse '{uploaded_file.name}'. Ensure it's valid JSON.")
                        # Clear potentially stale data if load fails
                        streamlit.session_state.config_data = None
                        streamlit.session_state.config_edit_buffer = ""
                        streamlit.session_state.config_editor_key = ""


            if streamlit.session_state.config_data is not None:
                streamlit.subheader("Edit Configuration")
                
                # The text_area's content is now managed by streamlit.session_state.config_editor_key
                # The 'value' parameter is used for initial setting or when programmatically changing it.
                # The 'key' parameter makes its current content accessible via session_state.
                edited_text = streamlit.text_area(
                    "Configuration (JSON format):",
                    value=streamlit.session_state.config_edit_buffer, # Display the buffer
                    height=400,
                    key="config_editor_key", # User edits update streamlit.session_state.config_editor_key
                    help="Edit the JSON configuration directly. Click 'Apply Changes' to update."
                )

                if streamlit.button("Apply Changes from Editor"):
                    parsed_config_from_text = config_manager.json_string_to_config(streamlit.session_state.config_editor_key)
                    if parsed_config_from_text is not None:
                        streamlit.session_state.config_data = parsed_config_from_text
                        # Refresh buffer with potentially reformatted JSON
                        streamlit.session_state.config_edit_buffer = config_manager.config_to_json_string(parsed_config_from_text)
                        # Update the text_area's displayed content to the canonical form by resetting its key's value
                        streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer
                        streamlit.success("Configuration updated from editor and applied.")
                        streamlit.experimental_rerun() # Rerun to ensure text_area reflects the canonical buffer
                    else:
                        streamlit.error("Invalid JSON in editor. Please correct and try again.")

                streamlit.download_button(
                    label="Download Configuration File",
                    data=streamlit.session_state.config_edit_buffer, # Download the content of the editor
                    file_name=streamlit.session_state.config_filename,
                    mime="application/json"
                )
                
                streamlit.subheader("Current Loaded Configuration")
                streamlit.json(streamlit.session_state.config_data) # Display the active config object
            else:
                streamlit.info("Upload a configuration file (JSON) to get started.")

        with tab_run:
            streamlit.header("Run Optimization")
            if streamlit.session_state.config_data is None:
                streamlit.warning("Please load a configuration in the 'Configuration' tab first.")
            else:
                streamlit.write("Initiate the route optimization process here. Progress and logs may be displayed.")
                streamlit.write("Using configuration:")
                streamlit.json(streamlit.session_state.config_data)


        with tab_results:
            streamlit.header("Dashboard & Results")
            if streamlit.session_state.config_data is None: # Or more specific check like "if results exist"
                streamlit.warning("Please load a configuration and run optimization to see results.")
            else:
                streamlit.write("Route visualizations and results will appear here.")

        with tab_settings:
            streamlit.header("UI Settings")
            streamlit.toggle(
                "Show Streamlit Header",
                value=streamlit.session_state.show_header, # Bind to existing state
                key="show_header_toggle", # Use a distinct key for the widget itself
                on_change=lambda: setattr(streamlit.session_state, 'show_header', streamlit.session_state.show_header_toggle),
                help="Toggle the visibility of the default Streamlit header bar."
            )

if __name__ == "__main__":
    main()
