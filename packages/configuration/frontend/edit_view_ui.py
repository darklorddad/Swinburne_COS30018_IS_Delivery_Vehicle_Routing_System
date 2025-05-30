import streamlit
from packages.configuration.backend import config_logic
from packages.simple.backend import simple_logic
from .ui_utils import display_operation_result, handle_ui_action_with_conditional_rerun

# Renders the 'Edit Configuration' view.
def render_edit_view(ss):
    validation_result = config_logic.validate_edit_mode_preconditions(ss)
    

    if not validation_result['valid']:
        if validation_result.get('message') and validation_result.get('type') == 'warning':
            streamlit.warning(validation_result['message'])
        streamlit.rerun()
        return

    with streamlit.expander("General Settings", expanded = True):
        streamlit.markdown("---")
        current_filename_base = ss.config_filename.replace(".json", "")
        
        streamlit.text_input(
            "Filename", 
            value = current_filename_base,
            key = "filename_input_widget",
            on_change = config_logic.handle_filename_update,
            args = (ss,)
        )

        wh_coords = ss.config_data.get("warehouse_coordinates_x_y", [0, 0])
        col_wh_x, col_wh_y = streamlit.columns(2)
        
        col_wh_x.number_input(
            "Warehouse X", 
            value = int(wh_coords[0]), 
            key = "wh_x_input_widget",
            format = "%d",
            on_change = config_logic.handle_warehouse_coordinates_update,
            args = (ss,)
        )
        col_wh_y.number_input(
            "Warehouse Y", 
            value = int(wh_coords[1]), 
            key = "wh_y_input_widget",
            format = "%d",
            on_change = config_logic.handle_warehouse_coordinates_update,
            args = (ss,)
        )

    with streamlit.expander("Parcel Management", expanded = True):
        streamlit.markdown("---")
        col_p_id, col_p_x, col_p_y, col_p_weight = streamlit.columns([2,1,1,1])
        new_parcel_id = col_p_id.text_input("Parcel ID", key = "new_parcel_id")
        new_parcel_x = col_p_x.number_input("Parcel X", value = 0, key = "new_parcel_x", format = "%d")
        new_parcel_y = col_p_y.number_input("Parcel Y", value = 0, key = "new_parcel_y", format = "%d")
        new_parcel_weight = col_p_weight.number_input("Weight", value = 0, key = "new_parcel_weight", min_value = 0, format = "%d")
        
        col_p_tw_open, col_p_tw_close, col_p_service = streamlit.columns(3)
        new_parcel_tw_open = col_p_tw_open.number_input("Time Window Open (min)", value = 480, min_value=0, max_value=1439, step=15, key = "new_parcel_tw_open", format = "%d")
        new_parcel_tw_close = col_p_tw_close.number_input("Time Window Close (min)", value = 1020, min_value=0, max_value=1439, step=15, key = "new_parcel_tw_close", format = "%d")
        new_parcel_service_time = col_p_service.number_input("Service Time (min)", value = 10, min_value=0, step=5, key = "new_parcel_service_time", format = "%d")

        if streamlit.button("Add parcel", key = "add_parcel_btn", use_container_width = True):
            handle_ui_action_with_conditional_rerun(
                config_logic.add_parcel,
                ss, 
                new_parcel_id, 
                new_parcel_x, 
                new_parcel_y, 
                new_parcel_weight,
                new_parcel_tw_open,
                new_parcel_tw_close,
                new_parcel_service_time
            )
        
        if ss.config_data["parcels"]:
            parcel_ids_to_remove = [p['id'] for p in ss.config_data["parcels"]]
            selected_parcel_to_remove = streamlit.selectbox(
                "Select parcel ID to remove", 
                options = [""] + parcel_ids_to_remove,
                index = 0,
                key = "remove_parcel_select"
            )
            if streamlit.button("Remove selected parcel", key = "remove_parcel_btn_new_row", use_container_width = True):
                # The backend's remove_parcel (via _remove_entity) handles the case where selected_parcel_to_remove is empty.
                result = config_logic.remove_parcel(ss, selected_parcel_to_remove)
                display_operation_result(result)
                if result and result.get('type') == 'success': # Rerun only on successful removal to update dataframe.
                    streamlit.rerun()
            
            streamlit.markdown("---")
            streamlit.dataframe(ss.config_data["parcels"], use_container_width = True)
        else:
            streamlit.info("No parcels added yet")

    with streamlit.expander("Delivery Agent Management", expanded = True):
        streamlit.markdown("---")
        col_a_id, col_a_cap_weight = streamlit.columns([3,2])
        new_agent_id = col_a_id.text_input("Agent ID", key = "new_agent_id_simplified")
        new_agent_cap_weight = col_a_cap_weight.number_input("Capacity (weight)", value = 0, min_value = 0, format = "%d", key = "new_agent_cap_weight_simplified")
        
        col_da_op_start, col_da_op_end = streamlit.columns(2)
        new_agent_op_start = col_da_op_start.number_input("Operating Hours Start (min)", value=480, min_value=0, max_value=1439, step=15, key="new_agent_op_start", format="%d")
        new_agent_op_end = col_da_op_end.number_input("Operating Hours End (min)", value=1080, min_value=0, max_value=1439, step=15, key="new_agent_op_end", format="%d")

        if streamlit.button("Add agent", key = "add_agent_btn_simplified", use_container_width = True):
            handle_ui_action_with_conditional_rerun(
                config_logic.add_delivery_agent,
                ss,
                new_agent_id,
                new_agent_cap_weight,
                new_agent_op_start,
                new_agent_op_end
            )

        if ss.config_data["delivery_agents"]:
            agent_ids_to_remove = [a['id'] for a in ss.config_data["delivery_agents"]]
            selected_agent_to_remove = streamlit.selectbox(
                "Select agent ID to remove", 
                options = [""] + agent_ids_to_remove,
                index = 0,
                key = "remove_agent_select_simplified"
            )
            if streamlit.button("Remove selected agent", key = "remove_agent_btn_new_row", use_container_width = True):
                # The backend's remove_delivery_agent (via _remove_entity) handles the case where selected_agent_to_remove is empty.
                result = config_logic.remove_delivery_agent(ss, selected_agent_to_remove)
                display_operation_result(result)
                if result and result.get('type') == 'success': # Rerun only on successful removal to update dataframe.
                    streamlit.rerun()
            
            streamlit.markdown("---")
            streamlit.dataframe(ss.config_data["delivery_agents"], use_container_width = True)
        else:
            streamlit.info("No delivery agents added yet")
    
    col_cancel_action, col_save_edits_action, col_save_download_action = streamlit.columns([1, 1, 1])

    with col_cancel_action:
        if streamlit.button("Cancel", key = "cancel_edit_btn", use_container_width = True):
            config_logic.handle_cancel_edit(ss)
            streamlit.rerun()

    with col_save_edits_action:
        if streamlit.button("Save", key = "save_edits_btn", use_container_width = True):
            result = config_logic.handle_save_edits(ss)
            display_operation_result(result) # Display success message
            if ss.get("simple_mode"):
                ss.simple_config_action_selected = None
            else:
                ss.action_selected = None
            streamlit.rerun()
    
    with col_save_download_action:
        if streamlit.button("Save and download", key = "save_download_btn", use_container_width = True):
            config_logic.handle_save_and_download(ss)
            streamlit.rerun()
