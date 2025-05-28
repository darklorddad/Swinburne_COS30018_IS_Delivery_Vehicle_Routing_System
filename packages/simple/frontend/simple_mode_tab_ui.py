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

def render_simple_mode_tab(ss):
    # Configure Section
    with streamlit.expander("Setup Configuration", expanded=True):
        col_create, col_load = streamlit.columns(2)
        with col_create:
            if streamlit.button("New configuration", key="simple_create_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot create new configuration while JADE is running")
                else:
                    config_logic.handle_new_config_action(ss)
                    config_logic.handle_edit_config_action(ss)
                    streamlit.rerun()
        with col_load:
            if streamlit.button("Load configuration", key="simple_load_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot load configuration while JADE is running")
                else:
                    config_logic.handle_load_config_action(ss)
                    ss.simple_config_action_selected = "load"
                    streamlit.rerun()

    # Configuration Action Rendering
    simple_config_action = ss.get("simple_config_action_selected")
    if simple_config_action == "edit":
        render_edit_view(ss)
    elif simple_config_action == "load":
        render_load_view(ss)
    else:
        with streamlit.expander("Manage current configuration", expanded=True):
            streamlit.markdown("---")
            if ss.config_data:
                streamlit.success(f"{ss.config_filename}")
                col_load, col_edit, col_clear = streamlit.columns(3)
                with col_edit:
                    if streamlit.button("Edit configuration", key="simple_config_edit_btn", use_container_width=True):
                        ss.simple_config_action_selected = "edit"
                        ss.edit_mode = True
                        streamlit.rerun()
                with col_load:
                    if streamlit.button("Load configuration", key="simple_config_load_btn", use_container_width=True):
                        ss.simple_config_action_selected = "load"
                        streamlit.rerun()
                with col_clear:
                    if streamlit.button("Clear configuration", key="simple_config_clear_btn", use_container_width=True):
                        config_logic.clear_config_from_memory(ss)
                        config_logic.reset_simple_config_action(ss)
                        streamlit.rerun()
            else:
                streamlit.info("No configuration currently loaded. Create or Load one above.")

    # Optimisation Section
    with streamlit.expander("Select Optimisation Method", expanded=True):
        if ss.get("jade_platform_running"):
            streamlit.warning("Optimisation script cannot be changed while JADE is running")
        else:
            if ss.optimisation_script_loaded_successfully:
                streamlit.success(f"Loaded Script: {ss.optimisation_script_filename}")
            else:
                streamlit.info("No optimisation script loaded")
            if streamlit.button("Load script", key="simple_load_script_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()

    # Execution Section
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
