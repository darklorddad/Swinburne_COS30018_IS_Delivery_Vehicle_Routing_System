import streamlit
import config_manager
import app_logic # Import the new logic module
import json
import copy # Keep copy for other parts of app.py for now


def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state variables using the function from app_logic
    app_logic.initialize_session_state(streamlit.session_state)

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

        /* Hide step buttons on number inputs */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {{
            display: none !important;
            visibility: hidden !important;
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
                # Reset flags and data using the new app_logic function
                app_logic.finalize_download(streamlit.session_state)
                # Rerun might be good here to clean up the "Downloading..." message immediately
                # However, the navigation to main menu is already handled by edit_mode=False
                # Let's see if a rerun is needed after testing. If the "Downloading..." message persists, add streamlit.rerun().

            if not streamlit.session_state.edit_mode:
                if streamlit.session_state.action_selected == "load":
                    # --- Load View ---
                    with streamlit.expander("Upload Configuration File", expanded=True):
                        streamlit.markdown("---")
                        # File uploader now stores to a buffer, managed by on_change
                        streamlit.file_uploader(
                            "Select a JSON configuration file to prepare for loading",
                            type=["json"],
                            key="config_uploader_buffer_widget",
                            on_change=app_logic.handle_file_uploader_change
                        )
                        # Direct buffer manipulation logic removed

                    # Buttons for Load View - Cancel on left, Load on right
                    col_cancel_load_action, col_load_action = streamlit.columns([1,1])

                    with col_cancel_load_action:
                        if streamlit.button("Cancel", key="cancel_load_action_btn", use_container_width=True):
                            app_logic.handle_cancel_load_action(streamlit.session_state)
                            streamlit.rerun()

                    with col_load_action:
                        load_disabled = streamlit.session_state.uploaded_file_buffer is None
                        if streamlit.button("Load selected configuration", key="confirm_load_btn", use_container_width=True, disabled=load_disabled):
                            result = app_logic.confirm_load_configuration(streamlit.session_state)
                            if result:
                                if result['type'] == 'success':
                                    streamlit.success(result['message'])
                                elif result['type'] == 'error':
                                    streamlit.error(result['message'])
                                elif result['type'] == 'info':
                                    streamlit.info(result['message'])
                                elif result['type'] == 'warning':
                                    streamlit.warning(result['message'])
                                # Rerun for most outcomes of confirm_load_configuration
                                if result['type'] in ['success', 'info'] or \
                                   (result['type'] == 'error' and "Ensure it's valid JSON" in result['message']) or \
                                   (result['type'] == 'warning' and "already processed" in result['message']):
                                    streamlit.rerun()


                else: # --- Initial View: Choose Action (action_selected is None) ---
                    with streamlit.expander("Create or Load Configuration", expanded=True):
                        streamlit.markdown("---")
                        col_create_btn, col_load_btn = streamlit.columns(2)
                        with col_create_btn:
                            if streamlit.button("New configuration", key="create_new_config_action_btn", help="Create a new configuration", use_container_width=True):
                                app_logic.handle_new_config_action(streamlit.session_state)
                                streamlit.rerun()
                        
                        with col_load_btn:
                            if streamlit.button("Load configuration", key="load_config_action_btn", help="Load configuration by uploading a JSON configuration file", use_container_width=True):
                                app_logic.handle_load_config_action(streamlit.session_state)
                                streamlit.rerun()
                    
                    # Option to edit if a configuration is in memory
                    if streamlit.session_state.config_data is not None:
                        with streamlit.expander("Manage Current Configuration", expanded=True):
                             streamlit.markdown("---")
                             config_status_message = f"A loaded configuration ('{streamlit.session_state.config_filename}') is in memory" \
                                 if streamlit.session_state.last_uploaded_filename is not None \
                                 else f"A new configuration ('{streamlit.session_state.config_filename}') is in memory"
                             streamlit.info(config_status_message)
                             if streamlit.button("Edit configuration", key="edit_config_btn", use_container_width=True): # Unified edit button
                                 app_logic.enter_edit_mode(streamlit.session_state)
                                 streamlit.rerun()
                            
                             # Option to clear memory (this is still inside the outer "if streamlit.session_state.config_data is not None:")
                             if streamlit.button("Clear configuration from memory", key="clear_memory_btn", use_container_width=True, help="Removes any loaded or new configuration from the current session"):
                                result = app_logic.clear_config_from_memory(streamlit.session_state)
                                if result and result.get('message'):
                                    streamlit.info(result['message'])
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
                    # Edit streamlit.session_state.config_filename directly
                    # The filename is not stored within config_data.
                    current_filename_base = streamlit.session_state.config_filename.replace(".json", "")
                    
                    streamlit.text_input(
                        "Filename", 
                        value=current_filename_base,
                        key="filename_input_widget", # Changed key
                        on_change=app_logic.handle_filename_update # Added on_change handler
                    )
                    # Direct update logic removed, now handled by app_logic.handle_filename_update
                    # "project_name" key is no longer used in config_data for the filename.


                    wh_coords = streamlit.session_state.config_data.get("warehouse_coordinates_x_y", [0, 0])
                    col_wh_x, col_wh_y = streamlit.columns(2)
                    
                    col_wh_x.number_input(
                        "Warehouse X", 
                        value=int(wh_coords[0]), 
                        key="wh_x_input_widget", # Changed key
                        format="%d",
                        on_change=app_logic.handle_warehouse_coordinates_update # Added on_change handler
                    )
                    col_wh_y.number_input(
                        "Warehouse Y", 
                        value=int(wh_coords[1]), 
                        key="wh_y_input_widget", # Changed key
                        format="%d",
                        on_change=app_logic.handle_warehouse_coordinates_update # Added on_change handler
                    )
                    # Direct update logic removed, now handled by app_logic.handle_warehouse_coordinates_update

                with streamlit.expander("Parcels Management", expanded=True):
                    streamlit.markdown("---")
                    # Initialization of "parcels" list is now handled by app_logic.enter_edit_mode
                    # if "parcels" not in streamlit.session_state.config_data:
                    #     streamlit.session_state.config_data["parcels"] = []

                    col_p_id, col_p_x, col_p_y, col_p_weight = streamlit.columns([2,1,1,1]) # Renamed columns for clarity
                    new_parcel_id = col_p_id.text_input("Parcel ID", key="new_parcel_id")
                    new_parcel_x = col_p_x.number_input("Parcel X", value=0, key="new_parcel_x", format="%d") # Label and key changed
                    new_parcel_y = col_p_y.number_input("Parcel Y", value=0, key="new_parcel_y", format="%d") # Label and key changed
                    new_parcel_weight = col_p_weight.number_input("Weight", value=0, key="new_parcel_weight", min_value=0, format="%d")
                    
                    if streamlit.button("Add parcel", key="add_parcel_btn", use_container_width=True):
                        result = app_logic.add_parcel(
                            streamlit.session_state, 
                            new_parcel_id, 
                            new_parcel_x, 
                            new_parcel_y, 
                            new_parcel_weight
                        )
                        if result and result['type'] == 'warning':
                            streamlit.warning(result['message'])
                        else: # On success or if no message, rerun to clear inputs and update table
                            streamlit.rerun()
                    
                    # Section for Removing Parcels (below add, above table)
                    if streamlit.session_state.config_data["parcels"]:
                        parcel_ids_to_remove = [p['id'] for p in streamlit.session_state.config_data["parcels"]]
                        selected_parcel_to_remove = streamlit.selectbox(
                            "Select parcel ID to remove", 
                            options=[""] + parcel_ids_to_remove, # Add empty option
                            index=0, # Default to empty option
                            key="remove_parcel_select"
                        )
                        if streamlit.button("Remove selected parcel", key="remove_parcel_btn_new_row", use_container_width=True):
                            if selected_parcel_to_remove:
                                result = app_logic.remove_parcel(streamlit.session_state, selected_parcel_to_remove)
                                # Optionally display result['message'] if needed
                                streamlit.rerun()
                            else:
                                streamlit.warning("Please select a parcel ID to remove.")
                        
                        streamlit.markdown("---") # Line above table
                        streamlit.dataframe(streamlit.session_state.config_data["parcels"], use_container_width=True)
                    else:
                        streamlit.info("No parcels added yet")

                with streamlit.expander("Delivery Agents Management", expanded=True):
                    streamlit.markdown("---")
                    # Initialization of "delivery_agents" list is now handled by app_logic.enter_edit_mode
                    # if "delivery_agents" not in streamlit.session_state.config_data:
                    #     streamlit.session_state.config_data["delivery_agents"] = []

                    # Simplified Add New Agent section
                    col_a_id, col_a_cap_weight = streamlit.columns([2,1])
                    new_agent_id = col_a_id.text_input("Agent ID", key="new_agent_id_simplified")
                    new_agent_cap_weight = col_a_cap_weight.number_input("Capacity (weight)", value=0, min_value=0, format="%d", key="new_agent_cap_weight_simplified")

                    if streamlit.button("Add agent", key="add_agent_btn_simplified", use_container_width=True):
                        result = app_logic.add_delivery_agent(
                            streamlit.session_state,
                            new_agent_id,
                            new_agent_cap_weight
                        )
                        if result and result['type'] == 'warning':
                            streamlit.warning(result['message'])
                        else: # On success or if no message, rerun to clear inputs and update table
                            streamlit.rerun()

                    # Section for Removing Agents (below add, above table)
                    if streamlit.session_state.config_data["delivery_agents"]:
                        agent_ids_to_remove = [a['id'] for a in streamlit.session_state.config_data["delivery_agents"]]
                        selected_agent_to_remove = streamlit.selectbox(
                            "Select agent ID to remove", 
                            options=[""] + agent_ids_to_remove, # Add empty option
                            index=0, # Default to empty option
                            key="remove_agent_select_simplified"
                        )
                        if streamlit.button("Remove selected agent", key="remove_agent_btn_new_row", use_container_width=True):
                            if selected_agent_to_remove:
                                result = app_logic.remove_delivery_agent(streamlit.session_state, selected_agent_to_remove)
                                # Optionally display result['message'] if needed
                                streamlit.rerun()
                            else:
                                streamlit.warning("Please select an agent ID to remove.")
                        
                        streamlit.markdown("---") # Line above table
                        streamlit.dataframe(streamlit.session_state.config_data["delivery_agents"], use_container_width=True)
                    else:
                        streamlit.info("No delivery agents added yet")
                
                # --- Bottom Actions: Cancel, Save Edits, Save & Download ---
                col_cancel_action, col_save_edits_action, col_save_download_action = streamlit.columns([1,1,1])

                with col_cancel_action:
                    if streamlit.button("Cancel", key="cancel_edit_btn", use_container_width=True):
                        app_logic.handle_cancel_edit(streamlit.session_state)
                        streamlit.rerun()

                with col_save_edits_action:
                    if streamlit.button("Save", key="save_edits_btn", use_container_width=True, help="Saves the current configuration and returns to the menu"):
                        result = app_logic.handle_save_edits(streamlit.session_state)
                        if result and result.get('type') == 'success':
                            streamlit.success(result['message'])
                        streamlit.rerun()
                
                with col_save_download_action:
                    if streamlit.button("Save and download", key="save_download_btn", use_container_width=True, help="Saves the current configuration, downloads it, and returns to the menu"):
                        app_logic.handle_save_and_download(streamlit.session_state)
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
                value=streamlit.session_state.show_header,
                key="show_header_toggle_widget", # Changed key to match app_logic
                on_change=app_logic.handle_show_header_toggle,
                help="Toggle the visibility of the default Streamlit header bar."
            )

if __name__ == "__main__":
    main()
