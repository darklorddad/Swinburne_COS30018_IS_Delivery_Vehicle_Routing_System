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
    streamlit.subheader("Generate New Configuration")
    num_parcels = streamlit.number_input("Number of Parcels", min_value=0, value=ss.get("simple_num_parcels_to_generate", 5), key="simple_gen_num_parcels")
    num_agents = streamlit.number_input("Number of Delivery Agents", min_value=0, value=ss.get("simple_num_agents_to_generate", 2), key="simple_gen_num_agents")
    
    col1, col2 = streamlit.columns(2)
    with col1:
        if streamlit.button("Generate and Edit", key="simple_generate_and_edit_btn", use_container_width=True):
            result = simple_logic.generate_quick_config(ss, num_parcels, num_agents)
            display_operation_result(result)
            if result.get('type') == 'success':
                ss.edit_mode = True # Prepare for edit view
                ss.simple_config_action_selected = "new_edit" # Transition to edit view (as generated is like a new one to edit)
            streamlit.rerun()
    with col2:
        if streamlit.button("Cancel", key="simple_cancel_generate_btn", use_container_width=True):
            ss.simple_config_action_selected = None # Go back to main simple view
            streamlit.rerun()
    streamlit.markdown("---")
    if ss.config_data and ss.config_filename == "generated-quick-config.json": # Check if a generated config exists
         streamlit.info(f"Previously generated: {ss.config_filename}. The 'Generate and Edit' button will overwrite this.")

def render_simple_mode_tab(ss):
    # Configuration Action Rendering
    simple_config_action = ss.get("simple_config_action_selected")

    if simple_config_action in ["edit", "new_edit"]:
        render_edit_view(ss)
    elif simple_config_action == "load":
        render_load_view(ss)
    else:
        # This is the main view of the simple tab when not editing or loading a config
        # Configure Section
        with streamlit.expander("Setup Configuration", expanded=True):
            col_create, col_load_buttons = streamlit.columns(2)
            with col_create:
                if streamlit.button("New configuration", key="simple_create_btn", use_container_width=True):
                    if ss.get("jade_platform_running"):
                        streamlit.warning("Cannot create new configuration while JADE is running")
                    else:
                        config_logic.handle_new_config_action(ss)
                        streamlit.rerun()
            with col_load_buttons:
                if streamlit.button("Load configuration", key="simple_load_btn", use_container_width=True):
                    if ss.get("jade_platform_running"):
                        streamlit.warning("Cannot load configuration while JADE is running")
                    else:
                        config_logic.handle_load_config_action(ss)
                        ss.simple_config_action_selected = "load"
                        streamlit.rerun()

        # Manage current configuration (only shows if a config exists and not in a sub-action)
        if ss.config_data:
            with streamlit.expander("Manage current configuration", expanded=True):
                streamlit.markdown("---")
                streamlit.success(f"{ss.config_filename}")
                col_manage_load, col_manage_edit, col_manage_clear = streamlit.columns(3)
                with col_manage_edit:
                    if streamlit.button("Edit current configuration", key="simple_config_edit_current_btn", use_container_width=True):
                        ss.simple_config_action_selected = "edit"
                        config_logic.enter_edit_mode(ss)
                        streamlit.rerun()
                with col_manage_load:
                    if streamlit.button("Load another configuration", key="simple_config_load_another_btn", use_container_width=True):
                        ss.simple_config_action_selected = "load"
                        config_logic.handle_load_config_action(ss)
                        streamlit.rerun()
                with col_manage_clear:
                    if streamlit.button("Clear current configuration", key="simple_config_clear_current_btn", use_container_width=True):
                        config_logic.clear_config_from_memory(ss)
                        config_logic.reset_simple_config_action(ss)
                        streamlit.rerun()
        elif not simple_config_action:
            with streamlit.expander("Manage current configuration", expanded=True):
                streamlit.info("No configuration currently loaded. Create or Load one above.")

        # Optimisation Section (Only shown in the main simple view, not edit/load)
        if not simple_config_action:
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
