import streamlit
import config_manager # Our new module for backend config logic

# Define a default configuration template
DEFAULT_CONFIG_TEMPLATE = {
    "project_name": "New VRP Project",
    "description": "A default configuration for the Delivery Vehicle Routing System.",
    "warehouse_location": [0.0, 0.0], # Example: [latitude, longitude] or [x, y]
    "parcels": [
        # Example structure:
        # { "id": "P001", "location": [2.5, 3.1], "weight": 10, "required_vehicle_type": "standard" }
    ],
    "agents": [
        # Example structure:
        # { "id": "DA01", "capacity_items": 10, "capacity_weight": 100, "vehicle_type": "standard", 
        #   "start_location": [0.0, 0.0], "end_location": [0.0, 0.0] }
    ],
    "optimization_settings": {
        "algorithm": "YourCustomAlgorithm", # Placeholder, user should define
        "max_iterations": 1000,
        "time_limit_seconds": 300
    },
    "map_settings": { # For visualization
        "provider": "OpenStreetMap", 
        "default_zoom": 12
    }
}

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
    if "processed_file_id" not in streamlit.session_state:
        streamlit.session_state.processed_file_id = None


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

            # --- Action Buttons: Create New or Clear ---
            col_action_1, col_action_2 = streamlit.columns(2)
            with col_action_1:
                if streamlit.button("✨ Create New Blank Configuration", key="create_new_config_btn", help="Load a default template to start a new configuration."):
                    streamlit.session_state.config_data = DEFAULT_CONFIG_TEMPLATE.copy() # Use a copy
                    streamlit.session_state.config_filename = "new_config.json"
                    streamlit.session_state.config_edit_buffer = config_manager.config_to_json_string(streamlit.session_state.config_data)
                    streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer
                    streamlit.session_state.processed_file_id = None # No file is "active" from uploader
                    streamlit.session_state.last_uploaded_filename = None 
                    streamlit.success("New blank configuration loaded into editor.")
                    streamlit.experimental_rerun()
            
            with col_action_2:
                if streamlit.session_state.config_data is not None:
                    if streamlit.button("🗑️ Clear Configuration & Start Over", key="clear_config_btn", help="Clears the current configuration and editor."):
                        streamlit.session_state.config_data = None
                        streamlit.session_state.config_filename = "config.json" # Reset default
                        streamlit.session_state.config_edit_buffer = ""
                        streamlit.session_state.config_editor_key = ""
                        streamlit.session_state.processed_file_id = None
                        streamlit.session_state.last_uploaded_filename = None
                        # Clear the uploader state by resetting its key if necessary, or rely on user action
                        # For now, just clearing our state. The uploader widget might still show a file.
                        streamlit.info("Configuration cleared.")
                        streamlit.experimental_rerun()

            # --- File Uploader ---
            streamlit.subheader("Load Configuration from File")
            uploaded_file = streamlit.file_uploader(
                "Upload a JSON configuration file. This will replace any current configuration in the editor.",
                type=["json"],
                key="config_uploader" # Keep a consistent key
            )

            if uploaded_file is not None:
                # Check if this is a new file upload that hasn't been processed yet
                if uploaded_file.file_id != streamlit.session_state.processed_file_id:
                    loaded_config = config_manager.load_config_from_uploaded_file(uploaded_file)
                    if loaded_config is not None:
                        streamlit.session_state.config_data = loaded_config
                        streamlit.session_state.config_filename = uploaded_file.name
                        streamlit.session_state.config_edit_buffer = config_manager.config_to_json_string(loaded_config)
                        streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer
                        streamlit.session_state.processed_file_id = uploaded_file.file_id # Mark as processed
                        streamlit.session_state.last_uploaded_filename = uploaded_file.name
                        streamlit.success(f"Configuration '{uploaded_file.name}' loaded successfully into editor.")
                        streamlit.experimental_rerun() # Rerun to update UI immediately
                    else:
                        streamlit.error(f"Failed to load or parse '{uploaded_file.name}'. Ensure it's valid JSON.")
                        # Don't change processed_file_id on error, so user can't retry same broken file without re-upload
                        # Or, set processed_file_id to a unique error marker if needed:
                        # streamlit.session_state.processed_file_id = f"error_{uploaded_file.file_id}"
            
            streamlit.markdown("---")

            # --- Editor and Actions (only if config_data is present) ---
            if streamlit.session_state.config_data is not None:
                streamlit.subheader("Edit Configuration")
                
                edited_text = streamlit.text_area( # Renamed from edited_text to avoid confusion, though not strictly necessary
                    "Configuration (JSON format):",
                    value=streamlit.session_state.config_edit_buffer,
                    height=400,
                    key="config_editor_key",
                    help="Edit the JSON configuration directly. Click 'Apply Changes' to validate and update."
                )

                col_apply, col_download = streamlit.columns(2)
                with col_apply:
                    if streamlit.button("💾 Apply Changes from Editor", key="apply_config_changes_btn"):
                        parsed_config_from_text = config_manager.json_string_to_config(streamlit.session_state.config_editor_key)
                        if parsed_config_from_text is not None:
                            streamlit.session_state.config_data = parsed_config_from_text
                            streamlit.session_state.config_edit_buffer = config_manager.config_to_json_string(parsed_config_from_text)
                            # Ensure editor key is also updated to reflect canonical form
                            streamlit.session_state.config_editor_key = streamlit.session_state.config_edit_buffer 
                            streamlit.success("Configuration updated from editor and applied.")
                            streamlit.experimental_rerun() 
                        else:
                            streamlit.error("Invalid JSON in editor. Please correct and try again.")
                
                with col_download:
                    streamlit.download_button(
                        label="📥 Download Configuration File",
                        data=streamlit.session_state.config_edit_buffer, # Download the applied/buffered version
                        file_name=streamlit.session_state.config_filename,
                        mime="application/json",
                        key="download_config_btn"
                    )
                
                streamlit.subheader("Current Active Configuration Preview")
                streamlit.json(streamlit.session_state.config_data)
            else:
                streamlit.info("Create a new configuration or upload a file to get started with editing.")

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
