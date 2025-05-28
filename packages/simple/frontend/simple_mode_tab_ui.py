import streamlit
from packages.configuration.backend import config_logic
from packages.configuration.frontend.edit_view_ui import render_edit_view
from packages.configuration.frontend.load_view_ui import render_load_view
from packages.optimisation.backend import optimisation_logic
from packages.execution.backend import execution_logic
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab
from packages.optimisation.frontend.optimisation_ui_utils import render_optimisation_results_display
from packages.configuration.frontend.ui_utils import display_operation_result
from packages.simple.backend import simple_logic

# New view for generating configuration in simple mode
def render_generate_config_view_simple(ss):
    with streamlit.expander("Generate Configuration", expanded=True):
        streamlit.markdown("---")
        num_parcels = streamlit.number_input("Number of Parcels", min_value=0, value=ss.get("simple_num_parcels_to_generate", 5), key="simple_gen_num_parcels")
        num_agents = streamlit.number_input("Number of Delivery Agents", min_value=0, value=ss.get("simple_num_agents_to_generate", 2), key="simple_gen_num_agents")
        
        col1, col2 = streamlit.columns(2)
        with col1:
            if streamlit.button("Cancel", key="simple_cancel_generate_btn", use_container_width=True):
                ss.simple_config_action_selected = None # Go back to main simple view
                streamlit.rerun()
        with col2:
            if streamlit.button("Generate", key="simple_generate_btn", use_container_width=True):
                result = simple_logic.generate_quick_config(ss, num_parcels, num_agents)
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
    else:
        # This is the main view of the simple tab when not editing or loading a config
        # Configuration Management Section
        with streamlit.expander("Configuration Management", expanded=True):
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
                
                streamlit.success(f"{ss.config_filename}")
                
                # Buttons stacked vertically
                if streamlit.button("Edit Configuration", key="simple_config_edit_current_btn", use_container_width=True):
                    ss.simple_config_action_selected = "edit"
                    config_logic.enter_edit_mode(ss)
                    streamlit.rerun()
                
                if streamlit.button("Clear Configuration", key="simple_config_clear_current_btn", use_container_width=True):
                    config_logic.clear_config_from_memory(ss)
                    config_logic.reset_simple_config_action(ss)
                    streamlit.rerun()

        # Optimisation Section (Only shown in the main simple view, not edit/load)
        if not simple_config_action:
            with streamlit.expander("Manage Optimisation Script", expanded=True):
                if not ss.config_data:
                    streamlit.warning("Please create or load a configuration first")
                elif ss.get("jade_platform_running"):
                    streamlit.warning("Optimisation script cannot be changed while JADE is running")
                else:
                    if ss.optimisation_script_loaded_successfully:
                        streamlit.success(f"Loaded: {ss.optimisation_script_filename}")
                    
                    # Add script selection dropdown
                    script_options = ["Select script"]  # Will be populated from pnp/featured
                    selected_script = streamlit.selectbox(
                        "Select script",
                        options=script_options,
                        key="script_select_box"
                    )
                    
                    if streamlit.button("Load script", key="simple_load_script_btn", use_container_width=True):
                        if selected_script != "Select script":
                            optimisation_logic.handle_initiate_load_script_action(ss)
                            streamlit.rerun()

        # Execution Section (Only shown in the main simple view, not edit/load)
        if not simple_config_action:
            with streamlit.expander("Run Simulation and View Results", expanded=True):
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
