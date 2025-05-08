import streamlit
import config_manager # Our new module for backend config logic
import json # For safely embedding data into JavaScript for download
import copy # For deep copying configuration data

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
    ]
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
    if "last_uploaded_filename" not in streamlit.session_state: 
        streamlit.session_state.last_uploaded_filename = None
    if "action_selected" not in streamlit.session_state: 
        streamlit.session_state.action_selected = None
    # For managing custom download flow
    if "initiate_download" not in streamlit.session_state:
        streamlit.session_state.initiate_download = False
    if "pending_download_data" not in streamlit.session_state:
        streamlit.session_state.pending_download_data = None
    if "pending_download_filename" not in streamlit.session_state:
        streamlit.session_state.pending_download_filename = None
    if "uploaded_file_buffer" not in streamlit.session_state: # To hold uploaded file before explicit load
        streamlit.session_state.uploaded_file_buffer = None
    if "config_data_snapshot" not in streamlit.session_state: # For reverting edits
        streamlit.session_state.config_data_snapshot = None
    if "new_config_saved_to_memory_at_least_once" not in streamlit.session_state:
        streamlit.session_state.new_config_saved_to_memory_at_least_once = False
    if "fallback_config_state" not in streamlit.session_state: # To store state of a new-saved config if another new one is started
        streamlit.session_state.fallback_config_state = None


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
            # Handle pending download if initiated
            if streamlit.session_state.get("initiate_download", False):
                if streamlit.session_state.pending_download_data and streamlit.session_state.pending_download_filename:
                    # Use JavaScript to trigger the download
                    streamlit.components.v1.html(
                        f"""
                        <html>
                            <head>
                                <title>Downloading...</title>
                                <script>
                                    window.onload = function() {{
                                        var link = document.createElement('a');
                                        link.href = 'data:application/json;charset=utf-8,' + encodeURIComponent({json.dumps(streamlit.session_state.pending_download_data)});
                                        link.download = {json.dumps(streamlit.session_state.pending_download_filename)};
                                        document.body.appendChild(link);
                                        link.click();
                                        document.body.removeChild(link);
                                        // Consider adding a brief message or a way to signal completion if needed
                                    }};
                                </script>
                            </head>
                            <body>
                                <!-- "Your download is starting..." text removed -->
                            </body>
                        </html>
                        """,
                        height=1 # Minimal height as there's no visible content
                    )
                # Reset flags and data
                streamlit.session_state.initiate_download = False
                streamlit.session_state.pending_download_data = None
                streamlit.session_state.pending_download_filename = None
                # Rerun might be good here to clean up the "Downloading..." message immediately
                # However, the navigation to main menu is already handled by edit_mode=False
                # Let's see if a rerun is needed after testing. If the "Downloading..." message persists, add streamlit.rerun().

            if not streamlit.session_state.edit_mode:
                if streamlit.session_state.action_selected == "load":
                    # --- Load View ---
                    # streamlit.subheader("Upload Configuration File") # Removed
                    
                    # File uploader now stores to a buffer
                    uploaded_file_widget_val = streamlit.file_uploader(
                        "Select a JSON configuration file to prepare for loading.",
                        type=["json"],
                        key="config_uploader_buffer_widget" 
                    )

                    # If a new file is uploaded by the widget, update the buffer
                    if uploaded_file_widget_val is not None:
                        streamlit.session_state.uploaded_file_buffer = uploaded_file_widget_val
                        # Reset processed_file_id_for_buffer when a new file is selected by the uploader
                        streamlit.session_state.processed_file_id_for_buffer = None 

                    # Buttons for Load View - Cancel on left, Load on right
                    col_cancel_load_action, col_load_action = streamlit.columns([1,1])
                    
                    with col_cancel_load_action:
                        if streamlit.button("Cancel", key="cancel_load_action_btn", use_container_width=True):
                            streamlit.session_state.action_selected = None
                            streamlit.session_state.uploaded_file_buffer = None 
                            streamlit.session_state.processed_file_id_for_buffer = None 
                            streamlit.rerun()

                    with col_load_action:
                        load_disabled = streamlit.session_state.uploaded_file_buffer is None
                        if streamlit.button("Load Selected Configuration", key="confirm_load_btn", use_container_width=True, disabled=load_disabled):
                            if streamlit.session_state.uploaded_file_buffer is not None: 
                                if streamlit.session_state.uploaded_file_buffer.file_id != streamlit.session_state.get("processed_file_id_for_buffer"):
                                    loaded_config = config_manager.load_config_from_uploaded_file(streamlit.session_state.uploaded_file_buffer)
                                    if loaded_config is not None:
                                        if streamlit.session_state.config_data is not None:
                                            streamlit.session_state.fallback_config_state = {
                                                'data': copy.deepcopy(streamlit.session_state.config_data),
                                                'filename': streamlit.session_state.config_filename,
                                                'snapshot': copy.deepcopy(streamlit.session_state.config_data_snapshot),
                                                'last_uploaded': streamlit.session_state.last_uploaded_filename,
                                                'saved_once': streamlit.session_state.new_config_saved_to_memory_at_least_once
                                            }
                                        else:
                                            streamlit.session_state.fallback_config_state = None

                                        streamlit.session_state.config_data = loaded_config
                                        streamlit.session_state.config_filename = streamlit.session_state.uploaded_file_buffer.name
                                        streamlit.session_state.processed_file_id = streamlit.session_state.uploaded_file_buffer.file_id
                                        streamlit.session_state.last_uploaded_filename = streamlit.session_state.uploaded_file_buffer.name 
                                        streamlit.session_state.new_config_saved_to_memory_at_least_once = False 
                                        
                                        streamlit.session_state.edit_mode = False 
                                        streamlit.session_state.action_selected = None 
                                        streamlit.session_state.fallback_config_state = None
                                        streamlit.session_state.uploaded_file_buffer = None 
                                        streamlit.session_state.processed_file_id_for_buffer = streamlit.session_state.processed_file_id 
                                        streamlit.success(f"Configuration '{streamlit.session_state.config_filename}' loaded successfully.")
                                        streamlit.rerun()
                                    else:
                                        streamlit.error(f"Failed to load or parse '{streamlit.session_state.uploaded_file_buffer.name}'. Ensure it's valid JSON.")
                                        streamlit.session_state.processed_file_id_for_buffer = streamlit.session_state.uploaded_file_buffer.file_id 
                                else: 
                                    if streamlit.session_state.config_data and streamlit.session_state.config_filename == streamlit.session_state.uploaded_file_buffer.name:
                                        streamlit.info(f"'{streamlit.session_state.uploaded_file_buffer.name}' is already loaded. Returning to menu.")
                                        streamlit.session_state.edit_mode = False 
                                        streamlit.session_state.action_selected = None 
                                        streamlit.session_state.uploaded_file_buffer = None
                                        streamlit.rerun()
                                    else:
                                         streamlit.warning(f"This file instance was already processed. If it failed, please select a new or corrected file.")

                else: # --- Initial View: Choose Action (action_selected is None) ---
                    col_create_btn, col_load_btn = streamlit.columns(2)
                    with col_create_btn:
                        if streamlit.button("New Configuration", key="create_new_config_action_btn", help="Start with a default template.", use_container_width=True):
                            # If there's any config in memory (loaded or new-saved), stash it as fallback
                            if streamlit.session_state.config_data is not None:
                                streamlit.session_state.fallback_config_state = {
                                    'data': copy.deepcopy(streamlit.session_state.config_data),
                                    'filename': streamlit.session_state.config_filename,
                                    'snapshot': copy.deepcopy(streamlit.session_state.config_data_snapshot), # Snapshot of the config being stashed
                                    'last_uploaded': streamlit.session_state.last_uploaded_filename,
                                    'saved_once': streamlit.session_state.new_config_saved_to_memory_at_least_once
                                }
                            else:
                                streamlit.session_state.fallback_config_state = None

                            # Initialize new config
                            streamlit.session_state.config_data = DEFAULT_CONFIG_TEMPLATE.copy()
                            streamlit.session_state.config_filename = "new_config.json"
                            streamlit.session_state.processed_file_id = None 
                            streamlit.session_state.last_uploaded_filename = None
                            streamlit.session_state.action_selected = None 
                            streamlit.session_state.edit_mode = True 
                            streamlit.session_state.config_data_snapshot = copy.deepcopy(streamlit.session_state.config_data) 
                            streamlit.session_state.new_config_saved_to_memory_at_least_once = False 
                            streamlit.rerun()
                    
                    with col_load_btn:
                        if streamlit.button("Load Configuration", key="load_config_action_btn", help="Upload a JSON configuration file.", use_container_width=True):
                            streamlit.session_state.action_selected = "load" # Switch to load view
                            streamlit.rerun()
                    
                    # Option to edit if a configuration is in memory
                    if streamlit.session_state.config_data is not None:
                         streamlit.markdown("---")
                         config_status_message = f"A loaded configuration ('{streamlit.session_state.config_filename}') is in memory." \
                             if streamlit.session_state.last_uploaded_filename is not None \
                             else f"An unsaved new configuration ('{streamlit.session_state.config_filename}') is in memory."
                         streamlit.info(config_status_message)
                         if streamlit.button("Edit Configuration", key="edit_config_btn", use_container_width=True): # Unified edit button
                             streamlit.session_state.edit_mode = True
                             # Snapshot is already set when entering edit mode or after "Save Edits"
                             # Ensure snapshot is taken if it's somehow None (e.g. direct state manipulation outside flow)
                             if streamlit.session_state.config_data_snapshot is None:
                                 streamlit.session_state.config_data_snapshot = copy.deepcopy(streamlit.session_state.config_data)
                             streamlit.rerun()

            else: # if streamlit.session_state.edit_mode is True
                if streamlit.session_state.config_data is None:
                    # Should not happen if logic is correct, but as a fallback:
                    streamlit.warning("No configuration data found. Returning to selection.")
                    streamlit.session_state.edit_mode = False
                    streamlit.rerun()
                    return

                # streamlit.subheader(f"Editing Configuration: {streamlit.session_state.config_filename}") # Removed
                
                with streamlit.expander("General Settings", expanded=True):
                    streamlit.markdown("---")
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
                    streamlit.markdown("---")
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
                        parcel_ids_to_remove = [p['id'] for p in streamlit.session_state.config_data["parcels"]]
                        selected_parcel_to_remove = streamlit.selectbox(
                            "Select Parcel ID to Remove", 
                            options=[""] + parcel_ids_to_remove,
                            key="remove_parcel_select"
                        )
                        if streamlit.button("Remove Selected Parcel", key="remove_parcel_btn_new_row", use_container_width=True) and selected_parcel_to_remove:
                            streamlit.session_state.config_data["parcels"] = [
                                p for p in streamlit.session_state.config_data["parcels"] if p['id'] != selected_parcel_to_remove
                            ]
                            streamlit.rerun()
                        
                        streamlit.markdown("---") # Line above table
                        streamlit.dataframe(streamlit.session_state.config_data["parcels"], use_container_width=True)
                    else:
                        streamlit.info("No parcels added yet.")

                with streamlit.expander("Delivery Agents Management", expanded=True):
                    streamlit.markdown("---")
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
                        agent_ids_to_remove = [a['id'] for a in streamlit.session_state.config_data["agents"]]
                        selected_agent_to_remove = streamlit.selectbox(
                            "Select Agent ID to Remove", 
                            options=[""] + agent_ids_to_remove,
                            key="remove_agent_select_simplified"
                        )
                        if streamlit.button("Remove Selected Agent", key="remove_agent_btn_new_row", use_container_width=True) and selected_agent_to_remove:
                            streamlit.session_state.config_data["agents"] = [
                                a for a in streamlit.session_state.config_data["agents"] if a['id'] != selected_agent_to_remove
                            ]
                            streamlit.rerun()
                        
                        streamlit.markdown("---") # Line above table
                        streamlit.dataframe(streamlit.session_state.config_data["agents"], use_container_width=True)
                    else:
                        streamlit.info("No delivery agents added yet.")
                
                # --- Bottom Actions: Cancel, Save Edits, Save & Download ---
                col_cancel_action, col_save_edits_action, col_save_download_action = streamlit.columns([1,1,1])

                with col_cancel_action:
                    if streamlit.button("Cancel", key="cancel_edit_btn", use_container_width=True):
                        # Revert to the snapshot
                        if streamlit.session_state.config_data_snapshot is not None:
                            streamlit.session_state.config_data = copy.deepcopy(streamlit.session_state.config_data_snapshot)
                        else: 
                            # This case implies config_data_snapshot is None.
                            # This should ideally not happen if snapshot is always set upon entering edit mode.
                            # If it's a new config and has no snapshot, it means it was never properly initialized.
                            if streamlit.session_state.last_uploaded_filename is None:
                                streamlit.session_state.config_data = None # Clear it as there's no valid state to revert to
                                streamlit.session_state.config_filename = "config.json"
                        
                        streamlit.session_state.edit_mode = False
                        streamlit.session_state.action_selected = None 
                        
                        is_current_config_new = streamlit.session_state.last_uploaded_filename is None
                        current_new_config_never_saved_via_save_edits = not streamlit.session_state.new_config_saved_to_memory_at_least_once

                        if is_current_config_new and current_new_config_never_saved_via_save_edits:
                            # Current new config should be discarded. Check for fallback.
                            if streamlit.session_state.fallback_config_state is not None:
                                # Restore from fallback
                                fallback = streamlit.session_state.fallback_config_state
                                streamlit.session_state.config_data = fallback['data']
                                streamlit.session_state.config_filename = fallback['filename']
                                streamlit.session_state.last_uploaded_filename = fallback['last_uploaded']
                                streamlit.session_state.config_data_snapshot = fallback['snapshot']
                                streamlit.session_state.new_config_saved_to_memory_at_least_once = fallback['saved_once']
                            else:
                                # No fallback, so clear to None
                                streamlit.session_state.config_data = None
                                streamlit.session_state.config_filename = "config.json"
                                streamlit.session_state.config_data_snapshot = None
                                # new_config_saved_to_memory_at_least_once is already False for the discarded config
                        # else: current config (loaded, or new+saved_via_SE) remains (reverted to its snapshot).
                        
                        streamlit.session_state.fallback_config_state = None # Fallback is consumed or no longer relevant
                        streamlit.rerun()

                with col_save_edits_action:
                    if streamlit.button("Save Edits", key="save_edits_btn", use_container_width=True, help="Saves current changes to memory and returns to the menu."):
                        streamlit.session_state.config_data_snapshot = copy.deepcopy(streamlit.session_state.config_data)
                        if streamlit.session_state.last_uploaded_filename is None: 
                            streamlit.session_state.new_config_saved_to_memory_at_least_once = True
                        
                        streamlit.session_state.edit_mode = False
                        streamlit.session_state.action_selected = None
                        streamlit.session_state.fallback_config_state = None # Edits committed, fallback irrelevant
                        streamlit.success("Edits saved to memory.") 
                        streamlit.rerun()
                
                with col_save_download_action:
                    if streamlit.button("Save & Download", key="save_download_btn", use_container_width=True, help="Saves the current configuration, downloads it, and returns to the menu."):
                        config_to_save = {
                            "project_name": streamlit.session_state.config_data.get("project_name"),
                            "warehouse_location": streamlit.session_state.config_data.get("warehouse_location"),
                            "parcels": streamlit.session_state.config_data.get("parcels", []),
                            "agents": streamlit.session_state.config_data.get("agents", [])
                        }
                        # Ensure snapshot reflects the state being saved, in case "Edit Configuration" is used later for this saved file (if it were loaded)
                        streamlit.session_state.config_data_snapshot = copy.deepcopy(streamlit.session_state.config_data)

                        # Initiate download
                        streamlit.session_state.pending_download_data = config_manager.config_to_json_string(config_to_save)
                        streamlit.session_state.pending_download_filename = streamlit.session_state.config_filename
                        streamlit.session_state.initiate_download = True
                        
                        was_new_config_being_saved = streamlit.session_state.last_uploaded_filename is None
                        
                        streamlit.session_state.edit_mode = False
                        streamlit.session_state.action_selected = None

                        if was_new_config_being_saved: 
                            streamlit.session_state.config_data = None
                            streamlit.session_state.config_filename = "config.json" 
                            streamlit.session_state.last_uploaded_filename = None
                            streamlit.session_state.processed_file_id = None
                            streamlit.session_state.config_data_snapshot = None
                            streamlit.session_state.new_config_saved_to_memory_at_least_once = False 
                        
                        streamlit.session_state.fallback_config_state = None # Config saved/downloaded, fallback irrelevant
                        streamlit.rerun()
            
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
