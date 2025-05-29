import streamlit
import os
from packages.configuration.backend import config_logic
from packages.configuration.frontend.edit_view_ui import render_edit_view
from packages.configuration.frontend.load_view_ui import render_load_view
from packages.optimisation.backend import optimisation_logic
from packages.optimisation.frontend.edit_optimisation_parameters_view_ui import render_edit_optimisation_parameters_view
from packages.execution.backend import execution_logic
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab
from packages.optimisation.frontend.optimisation_ui_utils import render_optimisation_results_display
from packages.configuration.frontend.ui_utils import display_operation_result
from packages.simple.backend import simple_logic

# New view for generating configuration in simple mode
def render_generate_config_view_simple(ss):
    with streamlit.expander("Generate Configuration", expanded=True):
        streamlit.markdown("---")
        config_name = streamlit.text_input("Configuration name", value="generated-config", key="simple_gen_config_name")
        num_parcels = streamlit.number_input("Number of parcels", min_value=0, value=ss.get("simple_num_parcels_to_generate", 5), key="simple_gen_num_parcels")
        num_agents = streamlit.number_input("Number of delivery agents", min_value=0, value=ss.get("simple_num_agents_to_generate", 2), key="simple_gen_num_agents")
    
    col_cancel, col_generate = streamlit.columns(2)
    with col_cancel:
        if streamlit.button("Cancel", key="simple_cancel_generate_btn", use_container_width=True):
            ss.simple_config_action_selected = None # Go back to main simple view
            streamlit.rerun()
    with col_generate:
        if streamlit.button("Generate", key="simple_generate_btn", use_container_width=True):
            result = simple_logic.generate_quick_config(ss, num_parcels, num_agents, config_name)
            display_operation_result(result)
            if result.get('type') == 'success':
                ss.simple_config_action_selected = None # Return to main view
            streamlit.rerun()
        

def render_simple_mode_tab(ss):
    # Configuration Action Rendering
    simple_config_action = ss.get("simple_config_action_selected")

    if simple_config_action in ["edit", "new_edit"]:
        render_edit_view(ss)
    elif simple_config_action == "load":
        render_load_view(ss)
    elif simple_config_action == "generate":
        render_generate_config_view_simple(ss)
    elif simple_config_action == "load_script":
        from packages.optimisation.frontend.load_optimisation_script_view_ui import render_load_optimisation_script_view
        render_load_optimisation_script_view(ss)
    elif simple_config_action == "edit_script_params":
        render_edit_optimisation_parameters_view(ss)
    else:
        # This is the main view of the simple tab when not editing or loading a config
        # Configuration Management Section
        with streamlit.expander("Configuration Management", expanded=True):
            streamlit.markdown("---")
            if streamlit.button("New configuration", key="simple_create_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot create new configuration while JADE is running")
                else:
                    config_logic.handle_new_config_action(ss)
                    streamlit.rerun()
            
            if streamlit.button("Load configuration", key="simple_load_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot load configuration while JADE is running")
                else:
                    config_logic.handle_load_config_action(ss)
                    ss.simple_config_action_selected = "load"
                    streamlit.rerun()
            
            if streamlit.button("Generate configuration", key="simple_generate_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot generate configuration while JADE is running")
                else:
                    ss.simple_config_action_selected = "generate"
                    streamlit.rerun()

        # Manage current configuration (only shows if a config exists)
        if ss.config_data:
            with streamlit.expander("Manage Current Configuration", expanded=True):
                streamlit.markdown("---")
                
                # Show config data tables
                if "parcels" in ss.config_data and ss.config_data["parcels"]:
                    streamlit.dataframe(ss.config_data["parcels"], use_container_width=True)
                
                if "delivery_agents" in ss.config_data and ss.config_data["delivery_agents"]:
                    streamlit.dataframe(ss.config_data["delivery_agents"], use_container_width=True)
                
                # Moved filename above the separator
                streamlit.success(f"{ss.config_filename}")
                streamlit.markdown("---")  # Separator before buttons
                
                # Buttons stacked vertically
                if streamlit.button("Edit configuration", key="simple_config_edit_current_btn", use_container_width=True):
                    ss.simple_config_action_selected = "edit"
                    config_logic.enter_edit_mode(ss)
                    streamlit.rerun()
                
                if streamlit.button("Clear configuration", key="simple_config_clear_current_btn", use_container_width=True):
                    config_logic.clear_config_from_memory(ss)
                    config_logic.reset_simple_config_action(ss)
                    streamlit.rerun()

        # Optimisation Section (Only shown in the main simple view, not edit/load)
        if not simple_config_action and ss.config_data:
            with streamlit.expander("Manage Optimisation Script", expanded=True):
                streamlit.markdown("---")  # Separator below expander title
                
                if ss.get("jade_platform_running"):
                    streamlit.warning("Optimisation script cannot be changed while JADE is running")
                else:
                    # Current script status and parameters
                    if ss.optimisation_script_loaded_successfully:
                        # Show parameters if available
                        if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema:
                            params_list = ss.optimisation_script_param_schema["parameters"]
                            if params_list:
                                table_data = []
                                for param in params_list:
                                    table_data.append({
                                        "Parameter": param.get("label", param.get("name", "")),
                                        "Type": param.get("type", ""),
                                        "Value": str(ss.optimisation_script_user_values.get(param["name"], "")),
                                        "Description": param.get("help", "")
                                    })
                                streamlit.dataframe(
                                    table_data,
                                    use_container_width=True,
                                    column_config={
                                        "Parameter": "Parameter",
                                        "Type": "Type",
                                        "Value": "Current Value", 
                                        "Description": "Description"
                                    }
                                )
                            else:
                                streamlit.info("No configurable parameters defined in this script")
                        
                        # Moved filename above the separator
                        streamlit.success(f"{ss.optimisation_script_filename}")
                        streamlit.markdown("---")  # Separator after parameters and filename
                    
                    # Featured scripts dropdown
                    if ss.get("featured_optimisation_scripts"):
                        selected_script = streamlit.selectbox(
                            "Select optimisation script", # Renamed label
                            options=["None"] + ss.featured_optimisation_scripts,
                            key="selected_featured_script"
                        )
                        
                        if streamlit.button("Select script", 
                                         key="select_featured_script_btn",
                                         use_container_width=True,
                                         disabled=selected_script == "None"):
                            try:
                                script_path = os.path.join("pnp", "featured", selected_script)
                                if not os.path.exists(script_path):
                                    raise FileNotFoundError(f"Script file not found at: {script_path}")
                            
                                with open(script_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                            
                                # Reset error state before loading
                                ss.optimisation_script_error_message = None
                            
                                # Create file-like object
                                ss.optimisation_file_uploader_widget = type('FileObj', (), {
                                    'name': selected_script,
                                    'getvalue': lambda: file_content.encode('utf-8'),
                                    'file_id': hash(file_content)  # Add unique file_id
                                })
                            
                                # Process the script
                                success = optimisation_logic.handle_optimisation_file_upload(ss)
                            
                                if success:
                                    ss.optimisation_script_loaded_successfully = True
                                    # Clear all relevant state to return to main view
                                    if 'selected_featured_script' in ss:
                                        del ss.selected_featured_script
                                    if 'optimisation_file_uploader_widget' in ss:
                                        del ss.optimisation_file_uploader_widget
                                    ss.simple_config_action_selected = None
                                    # Force immediate UI update
                                    streamlit.rerun()
                                else:
                                    # Use explicit error if available
                                    error_msg = ss.optimisation_script_error_message or "Unknown error loading script"
                                    ss.optimisation_script_error_message = error_msg
                                    streamlit.rerun()
                            
                            except Exception as e:
                                ss.optimisation_script_error_message = f"Error loading script: {str(e)}"
                                streamlit.rerun()
                    
                    streamlit.markdown("---")  # Separator between featured scripts and file loader
                    if streamlit.button("Load script",  # Renamed button
                                     key="load_script_menu_btn_simple", # Adjusted key for clarity
                                     use_container_width=True):
                        ss.simple_config_action_selected = "load_script"
                        streamlit.rerun()
                    
                    # Edit parameters button
                    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema:
                        if streamlit.button("Edit parameters",
                                         key="edit_parameters_btn_simple",
                                         use_container_width=True):
                            optimisation_logic.handle_edit_parameters_action(ss)
                            ss.simple_config_action_selected = "edit_script_params"
                            streamlit.rerun()
                    
                    # Clear script button
                    if ss.optimisation_script_loaded_successfully:
                        if streamlit.button("Clear script",
                                         key="clear_script_btn",
                                         use_container_width=True):
                            optimisation_logic.clear_optimisation_script(ss)
                            streamlit.rerun()

        # Execution Section (Only shown in the view, view, not edit/load)
        if not simple_config_action and ss.config_data and ss.get("optimisation_script_loaded_successfully", False):
            with streamlit.expander("Run and View Results", expanded=True): # Renamed expander
                if not ss.get("jade_platform_running"):
                    if streamlit.button("Start JADE Platform", key="simple_start_jade_btn", use_container_width=True,
                                      disabled=(not ss.config_data or not ss.optimisation_script_loaded_successfully)):
                        execution_logic.handle_start_jade(ss)
                        streamlit.rerun()
                else:
                    streamlit.success("JADE Platform is Running")
                    if streamlit.button("Run Full Optimisation", key="simple_run_btn", use_container_width=True):
                        execution_logic.handle_trigger_mra_optimisation_cycle(ss)
                        optimisation_logic.run_optimisation_script(ss)
                        execution_logic.handle_send_optimised_routes_to_mra(ss)
                        streamlit.rerun()

                if ss.get("optimisation_run_complete"):
                    render_optimisation_results_display(ss.optimisation_results)
                    render_visualisation_tab(ss)

                if ss.get("jade_platform_running"):
                    if streamlit.button("Stop JADE Platform", key="simple_stop_jade_btn", use_container_width=True):
                        execution_logic.handle_stop_jade(ss)
                        streamlit.rerun()
