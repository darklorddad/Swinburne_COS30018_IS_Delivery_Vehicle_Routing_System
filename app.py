import streamlit
import config_manager # Our new module for backend config logic

# Define a default configuration template
DEFAULT_CONFIG_TEMPLATE = {
    "project_name": "new_project_config", # Will be used as default filename
    "warehouse_location": [0.0, 0.0], # Example: [latitude, longitude] or [x, y]
    "parcels": [
        # Example structure:
        # { "id": "P001", "location": [2.5, 3.1], "weight": 10 }
    ],
    "agents": [
        # Example structure:
        # { "id": "DA01", "capacity_weight": 100 }
    ],
    "optimization_settings": { # Kept for future use, not directly edited in this UI iteration
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
    if "processed_file_id" not in streamlit.session_state:
        streamlit.session_state.processed_file_id = None
    if "edit_mode" not in streamlit.session_state:
        streamlit.session_state.edit_mode = False
    if "last_uploaded_filename" not in streamlit.session_state: # Retained for potential use or can be removed if not needed
        streamlit.session_state.last_uploaded_filename = None
    if "action_selected" not in streamlit.session_state: # To manage create/load flow
        streamlit.session_state.action_selected = None


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

            if not streamlit.session_state.edit_mode:
                # --- Initial View: Choose Action ---
                streamlit.subheader("Start New or Load Existing Configuration")
                
                col_create_btn, col_load_btn = streamlit.columns(2)
                with col_create_btn:
                    if streamlit.button("Create New Configuration", key="create_new_config_action_btn", help="Start with a default template.", use_container_width=True):
                        streamlit.session_state.config_data = DEFAULT_CONFIG_TEMPLATE.copy()
                        streamlit.session_state.config_filename = "new_config.json"
                        streamlit.session_state.processed_file_id = None 
                        streamlit.session_state.last_uploaded_filename = None
                        streamlit.session_state.action_selected = None # Clear load action if any
                        streamlit.session_state.edit_mode = True
                        streamlit.rerun()
                
                with col_load_btn:
                    if streamlit.button("Load Configuration from File", key="load_config_action_btn", help="Upload a JSON configuration file.", use_container_width=True):
                        streamlit.session_state.action_selected = "load"
                        streamlit.rerun()

                if streamlit.session_state.action_selected == "load":
                    streamlit.markdown("---") # Separator
                    streamlit.subheader("Upload Configuration File")
                    uploaded_file = streamlit.file_uploader(
                        "Select a JSON configuration file. This will replace any current configuration if loaded.",
                        type=["json"],
                        key="config_uploader_conditional" 
                    )

                    if uploaded_file is not None:
                        # Process only if it's a new file instance
                        if uploaded_file.file_id != streamlit.session_state.processed_file_id:
                            loaded_config = config_manager.load_config_from_uploaded_file(uploaded_file)
                            if loaded_config is not None:
                                streamlit.session_state.config_data = loaded_config
                                streamlit.session_state.config_filename = uploaded_file.name
                                streamlit.session_state.processed_file_id = uploaded_file.file_id
                                streamlit.session_state.last_uploaded_filename = uploaded_file.name
                                streamlit.session_state.edit_mode = True
                                streamlit.session_state.action_selected = None # Reset action
                                streamlit.success(f"Configuration '{uploaded_file.name}' loaded successfully.")
                                streamlit.rerun()
                            else:
                                streamlit.error(f"Failed to load or parse '{uploaded_file.name}'. Ensure it's valid JSON.")
                                # Mark as processed with error to avoid re-processing same error without re-upload
                                streamlit.session_state.processed_file_id = f"error_{uploaded_file.file_id}"
                        # If file_id is same as processed_file_id, do nothing to prevent re-processing on simple reruns
                        # unless it's an error state, then user must re-upload.
                
                # Option to resume editing if a config is loaded but user navigated away from edit_mode
                # and no specific "load" action is currently pending.
                if streamlit.session_state.config_data is not None and \
                   not streamlit.session_state.edit_mode and \
                   streamlit.session_state.action_selected is None:
                     streamlit.markdown("---") # Separator
                     streamlit.info(f"A configuration ('{streamlit.session_state.config_filename}') is already in memory.")
                     if streamlit.button("Resume Editing This Configuration", key="resume_editing_btn", use_container_width=True):
                         streamlit.session_state.edit_mode = True
                         streamlit.rerun()

            else: # if streamlit.session_state.edit_mode is True
                if streamlit.session_state.config_data is None:
                    # Should not happen if logic is correct, but as a fallback:
                    streamlit.warning("No configuration data found. Returning to selection.")
                    streamlit.session_state.edit_mode = False
                    streamlit.rerun()
                    return

                streamlit.subheader(f"Editing Configuration: {streamlit.session_state.config_filename}")
                
                with streamlit.expander("General Settings", expanded=True):
                    # Use project_name from config_data for the input field, but update session_state.config_filename
                    # This keeps config_data structure consistent if "project_name" is a meaningful field internally.
                    # For saving, session_state.config_filename is used.
                    current_filename_base = streamlit.session_state.config_data.get("project_name", streamlit.session_state.config_filename.replace(".json", ""))
                    
                    new_filename_base = streamlit.text_input(
                        "Filename (without .json extension)", 
                        value=current_filename_base,
                        key="filename_input"
                    )
                    # Update project_name in config_data and config_filename in session_state
                    streamlit.session_state.config_data["project_name"] = new_filename_base
                    streamlit.session_state.config_filename = f"{new_filename_base}.json" if not new_filename_base.endswith(".json") else new_filename_base


                    wh_loc = streamlit.session_state.config_data.get("warehouse_location", [0.0, 0.0])
                    col_wh_lat, col_wh_lon = streamlit.columns(2)
                    wh_lat = col_wh_lat.number_input("Warehouse Latitude/X", value=float(wh_loc[0]), key="wh_lat_input", format="%.4f")
                    wh_lon = col_wh_lon.number_input("Warehouse Longitude/Y", value=float(wh_loc[1]), key="wh_lon_input", format="%.4f")
                    streamlit.session_state.config_data["warehouse_location"] = [wh_lat, wh_lon]

                with streamlit.expander("Parcels Management", expanded=True):
                    if "parcels" not in streamlit.session_state.config_data:
                        streamlit.session_state.config_data["parcels"] = []

                    col_p_id, col_p_loc_x, col_p_loc_y, col_p_weight = streamlit.columns([2,1,1,1])
                    new_parcel_id = col_p_id.text_input("Parcel ID", key="new_parcel_id")
                    new_parcel_loc_x = col_p_loc_x.number_input("Location X", key="new_parcel_loc_x", format="%.4f")
                    new_parcel_loc_y = col_p_loc_y.number_input("Location Y", key="new_parcel_loc_y", format="%.4f")
                    new_parcel_weight = col_p_weight.number_input("Weight", key="new_parcel_weight", min_value=0.0, format="%.2f")
                    
                    if streamlit.button("Add Parcel", key="add_parcel_btn", use_container_width=True):
                        if new_parcel_id and not any(p['id'] == new_parcel_id for p in streamlit.session_state.config_data["parcels"]):
                            streamlit.session_state.config_data["parcels"].append({
                                "id": new_parcel_id,
                                "location": [new_parcel_loc_x, new_parcel_loc_y],
                                "weight": new_parcel_weight
                            })
                            # Clear inputs after adding by rerunning (Streamlit's default behavior for new keys might also clear them)
                            streamlit.rerun() 
                        elif not new_parcel_id:
                            streamlit.warning("Parcel ID cannot be empty.")
                        else:
                            streamlit.warning(f"Parcel ID '{new_parcel_id}' already exists.")
                    
                    # Section for Removing Parcels (below add, above table)
                    if streamlit.session_state.config_data["parcels"]:
                        col_select_remove_parcel, col_btn_remove_parcel = streamlit.columns([3,1])
                        with col_select_remove_parcel:
                            parcel_ids_to_remove = [p['id'] for p in streamlit.session_state.config_data["parcels"]]
                            selected_parcel_to_remove = streamlit.selectbox(
                                "Select Parcel ID to Remove", 
                                options=[""] + parcel_ids_to_remove,
                                key="remove_parcel_select"
                            )
                        with col_btn_remove_parcel:
                            # Add some space to align button better if needed, or use container width
                            streamlit.write("") # Placeholder for alignment or use CSS
                            if streamlit.button("Remove Parcel", key="remove_parcel_btn_inline", use_container_width=True) and selected_parcel_to_remove:
                                streamlit.session_state.config_data["parcels"] = [
                                    p for p in streamlit.session_state.config_data["parcels"] if p['id'] != selected_parcel_to_remove
                                ]
                                streamlit.rerun()
                        
                        streamlit.dataframe(streamlit.session_state.config_data["parcels"], use_container_width=True)
                    else:
                        streamlit.info("No parcels added yet.")

                with streamlit.expander("Delivery Agents Management", expanded=True):
                    if "agents" not in streamlit.session_state.config_data:
                        streamlit.session_state.config_data["agents"] = []

                    # Simplified Add New Agent section
                    col_a_id, col_a_cap_weight = streamlit.columns([2,1])
                    new_agent_id = col_a_id.text_input("Agent ID", key="new_agent_id_simplified")
                    new_agent_cap_weight = col_a_cap_weight.number_input("Capacity (Weight)", min_value=0.0, format="%.2f", key="new_agent_cap_weight_simplified")

                    if streamlit.button("Add Agent", key="add_agent_btn_simplified", use_container_width=True):
                        if new_agent_id and not any(a['id'] == new_agent_id for a in streamlit.session_state.config_data["agents"]):
                            streamlit.session_state.config_data["agents"].append({
                                "id": new_agent_id,
                                "capacity_weight": new_agent_cap_weight
                            })
                            streamlit.rerun()
                        elif not new_agent_id:
                            streamlit.warning("Agent ID cannot be empty.")
                        else:
                            streamlit.warning(f"Agent ID '{new_agent_id}' already exists.")

                    # Section for Removing Agents (below add, above table)
                    if streamlit.session_state.config_data["agents"]:
                        col_select_remove_agent, col_btn_remove_agent = streamlit.columns([3,1])
                        with col_select_remove_agent:
                            agent_ids_to_remove = [a['id'] for a in streamlit.session_state.config_data["agents"]]
                            selected_agent_to_remove = streamlit.selectbox(
                                "Select Agent ID to Remove", 
                                options=[""] + agent_ids_to_remove,
                                key="remove_agent_select_simplified"
                            )
                        with col_btn_remove_agent:
                            streamlit.write("") # Placeholder for alignment
                            if streamlit.button("Remove Agent", key="remove_agent_btn_inline_simplified", use_container_width=True) and selected_agent_to_remove:
                                streamlit.session_state.config_data["agents"] = [
                                    a for a in streamlit.session_state.config_data["agents"] if a['id'] != selected_agent_to_remove
                                ]
                                streamlit.rerun()
                        
                        streamlit.dataframe(streamlit.session_state.config_data["agents"], use_container_width=True)
                    else:
                        streamlit.info("No delivery agents added yet.")
                
                streamlit.markdown("---") # Separator before bottom actions
                # --- Bottom Actions: Save, Back, Status ---
                col_save, col_back, col_status = streamlit.columns([1,1,2])
                with col_save:
                    # Prepare data for download button
                    config_json_string = config_manager.config_to_json_string(streamlit.session_state.config_data)
                    streamlit.download_button(
                        label="Save Configuration",
                        data=config_json_string,
                        file_name=streamlit.session_state.config_filename, # Uses current filename
                        mime="application/json",
                        key="save_config_btn_edit_mode",
                        help="Saves the current configuration to a JSON file."
                    )
                with col_back:
                    if streamlit.button("Back to Main Menu", key="back_to_main_btn"):
                        streamlit.session_state.edit_mode = False
                        streamlit.session_state.action_selected = None # Reset any pending action
                        # Config_data is preserved, allowing "Resume Editing"
                        streamlit.rerun()
                with col_status:
                    streamlit.caption(f"Status: Editing '{streamlit.session_state.config_filename}'.")
            
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
