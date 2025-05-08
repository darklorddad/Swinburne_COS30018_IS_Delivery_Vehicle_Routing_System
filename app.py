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
    if "processed_file_id" not in streamlit.session_state:
        streamlit.session_state.processed_file_id = None
    if "edit_mode" not in streamlit.session_state:
        streamlit.session_state.edit_mode = False
    if "last_uploaded_filename" not in streamlit.session_state: # Retained for potential use or can be removed if not needed
        streamlit.session_state.last_uploaded_filename = None


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
                # --- Initial View: Create or Load ---
                col_create, col_load_header = streamlit.columns([1,2])
                with col_create:
                    if streamlit.button("Create New Blank Configuration", key="create_new_config_btn_main", help="Load a default template to start a new configuration."):
                        streamlit.session_state.config_data = DEFAULT_CONFIG_TEMPLATE.copy()
                        streamlit.session_state.config_filename = "new_config.json"
                        streamlit.session_state.processed_file_id = None 
                        streamlit.session_state.last_uploaded_filename = None
                        streamlit.session_state.edit_mode = True
                        streamlit.experimental_rerun()
                
                with col_load_header:
                     streamlit.subheader("Load Configuration from File")

                uploaded_file = streamlit.file_uploader(
                    "Upload a JSON configuration file. This will replace any current configuration.",
                    type=["json"],
                    key="config_uploader_main" 
                )

                if uploaded_file is not None:
                    if uploaded_file.file_id != streamlit.session_state.processed_file_id:
                        loaded_config = config_manager.load_config_from_uploaded_file(uploaded_file)
                        if loaded_config is not None:
                            streamlit.session_state.config_data = loaded_config
                            streamlit.session_state.config_filename = uploaded_file.name
                            streamlit.session_state.processed_file_id = uploaded_file.file_id
                            streamlit.session_state.last_uploaded_filename = uploaded_file.name
                            streamlit.session_state.edit_mode = True
                            streamlit.success(f"Configuration '{uploaded_file.name}' loaded successfully.")
                            streamlit.experimental_rerun()
                        else:
                            streamlit.error(f"Failed to load or parse '{uploaded_file.name}'. Ensure it's valid JSON.")
                            streamlit.session_state.processed_file_id = f"error_{uploaded_file.file_id}" # Mark to avoid re-processing same error
                
                if streamlit.session_state.config_data is not None and not streamlit.session_state.edit_mode:
                     # This case might occur if edit_mode was somehow set to False but config_data exists.
                     # Provide an option to resume editing or clear.
                     streamlit.info(f"A configuration '{streamlit.session_state.config_filename}' is loaded but not in edit mode.")
                     if streamlit.button("Resume Editing"):
                         streamlit.session_state.edit_mode = True
                         streamlit.experimental_rerun()


            else: # if streamlit.session_state.edit_mode is True
                if streamlit.session_state.config_data is None:
                    # Should not happen if logic is correct, but as a fallback:
                    streamlit.warning("No configuration data found. Returning to selection.")
                    streamlit.session_state.edit_mode = False
                    streamlit.experimental_rerun()
                    return

                streamlit.subheader(f"Editing Configuration: {streamlit.session_state.config_filename}")
                
                # --- General Configuration ---
                streamlit.markdown("#### General Settings")
                project_name = streamlit.text_input(
                    "Project Name", 
                    value=streamlit.session_state.config_data.get("project_name", ""),
                    key="proj_name_input"
                )
                streamlit.session_state.config_data["project_name"] = project_name

                description = streamlit.text_input(
                    "Description", 
                    value=streamlit.session_state.config_data.get("description", ""),
                    key="desc_input"
                )
                streamlit.session_state.config_data["description"] = description

                wh_loc = streamlit.session_state.config_data.get("warehouse_location", [0.0, 0.0])
                col_wh_lat, col_wh_lon = streamlit.columns(2)
                wh_lat = col_wh_lat.number_input("Warehouse Latitude/X", value=float(wh_loc[0]), key="wh_lat_input", format="%.4f")
                wh_lon = col_wh_lon.number_input("Warehouse Longitude/Y", value=float(wh_loc[1]), key="wh_lon_input", format="%.4f")
                streamlit.session_state.config_data["warehouse_location"] = [wh_lat, wh_lon]

                streamlit.markdown("---")

                # --- Parcels Management ---
                streamlit.markdown("#### Parcels Management")
                if "parcels" not in streamlit.session_state.config_data: # Ensure parcels list exists
                    streamlit.session_state.config_data["parcels"] = []

                col_p_id, col_p_loc_x, col_p_loc_y, col_p_add = streamlit.columns([2,1,1,1])
                new_parcel_id = col_p_id.text_input("Parcel ID", key="new_parcel_id")
                new_parcel_loc_x = col_p_loc_x.number_input("Location X", key="new_parcel_loc_x", format="%.4f")
                new_parcel_loc_y = col_p_loc_y.number_input("Location Y", key="new_parcel_loc_y", format="%.4f")
                
                if col_p_add.button("Add Parcel", key="add_parcel_btn"):
                    if new_parcel_id and not any(p['id'] == new_parcel_id for p in streamlit.session_state.config_data["parcels"]):
                        streamlit.session_state.config_data["parcels"].append({
                            "id": new_parcel_id,
                            "location": [new_parcel_loc_x, new_parcel_loc_y]
                            # Add other parcel fields from DEFAULT_CONFIG_TEMPLATE if needed e.g. weight, required_vehicle_type
                        })
                        streamlit.experimental_rerun()
                    elif not new_parcel_id:
                        streamlit.warning("Parcel ID cannot be empty.")
                    else:
                        streamlit.warning(f"Parcel ID '{new_parcel_id}' already exists.")
                
                if streamlit.session_state.config_data["parcels"]:
                    streamlit.dataframe(streamlit.session_state.config_data["parcels"], use_container_width=True)
                    parcel_ids_to_remove = [p['id'] for p in streamlit.session_state.config_data["parcels"]]
                    selected_parcel_to_remove = streamlit.selectbox(
                        "Select Parcel ID to Remove", 
                        options=[""] + parcel_ids_to_remove, # Add empty option for no selection
                        key="remove_parcel_select"
                    )
                    if streamlit.button("Remove Selected Parcel", key="remove_parcel_btn") and selected_parcel_to_remove:
                        streamlit.session_state.config_data["parcels"] = [
                            p for p in streamlit.session_state.config_data["parcels"] if p['id'] != selected_parcel_to_remove
                        ]
                        streamlit.experimental_rerun()
                else:
                    streamlit.info("No parcels added yet.")
                
                streamlit.markdown("---")

                # --- Agents Management ---
                streamlit.markdown("#### Delivery Agents Management")
                if "agents" not in streamlit.session_state.config_data: # Ensure agents list exists
                    streamlit.session_state.config_data["agents"] = []

                with streamlit.expander("Add New Agent", expanded=False):
                    new_agent_id = streamlit.text_input("Agent ID", key="new_agent_id")
                    col_cap_item, col_cap_weight = streamlit.columns(2)
                    new_agent_cap_items = col_cap_item.number_input("Capacity (Items)", min_value=0, step=1, key="new_agent_cap_items")
                    new_agent_cap_weight = col_cap_weight.number_input("Capacity (Weight)", min_value=0.0, format="%.2f", key="new_agent_cap_weight")
                    new_agent_vehicle_type = streamlit.text_input("Vehicle Type", value="standard", key="new_agent_vehicle_type")
                    
                    col_start_x, col_start_y = streamlit.columns(2)
                    new_agent_start_x = col_start_x.number_input("Start Location X", format="%.4f", key="new_agent_start_x")
                    new_agent_start_y = col_start_y.number_input("Start Location Y", format="%.4f", key="new_agent_start_y")
                    
                    col_end_x, col_end_y = streamlit.columns(2)
                    new_agent_end_x = col_end_x.number_input("End Location X", format="%.4f", key="new_agent_end_x")
                    new_agent_end_y = col_end_y.number_input("End Location Y", format="%.4f", key="new_agent_end_y")

                    if streamlit.button("Add Agent", key="add_agent_btn"):
                        if new_agent_id and not any(a['id'] == new_agent_id for a in streamlit.session_state.config_data["agents"]):
                            streamlit.session_state.config_data["agents"].append({
                                "id": new_agent_id,
                                "capacity_items": new_agent_cap_items,
                                "capacity_weight": new_agent_cap_weight,
                                "vehicle_type": new_agent_vehicle_type,
                                "start_location": [new_agent_start_x, new_agent_start_y],
                                "end_location": [new_agent_end_x, new_agent_end_y]
                            })
                            streamlit.experimental_rerun()
                        elif not new_agent_id:
                            streamlit.warning("Agent ID cannot be empty.")
                        else:
                            streamlit.warning(f"Agent ID '{new_agent_id}' already exists.")

                if streamlit.session_state.config_data["agents"]:
                    streamlit.dataframe(streamlit.session_state.config_data["agents"], use_container_width=True)
                    agent_ids_to_remove = [a['id'] for a in streamlit.session_state.config_data["agents"]]
                    selected_agent_to_remove = streamlit.selectbox(
                        "Select Agent ID to Remove", 
                        options=[""] + agent_ids_to_remove, # Add empty option for no selection
                        key="remove_agent_select"
                    )
                    if streamlit.button("Remove Selected Agent", key="remove_agent_btn") and selected_agent_to_remove:
                        streamlit.session_state.config_data["agents"] = [
                            a for a in streamlit.session_state.config_data["agents"] if a['id'] != selected_agent_to_remove
                        ]
                        streamlit.experimental_rerun()
                else:
                    streamlit.info("No delivery agents added yet.")

                streamlit.markdown("---")
                
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
                        # Decide if config_data should be cleared or preserved when going back
                        # For now, preserve it. User can explicitly create new or load another.
                        streamlit.experimental_rerun()
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
