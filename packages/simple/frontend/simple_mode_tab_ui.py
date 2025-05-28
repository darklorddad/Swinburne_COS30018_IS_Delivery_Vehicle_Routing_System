import streamlit
from packages.configuration.backend import config_logic
from packages.optimisation.backend import optimisation_logic
from packages.execution.backend import execution_logic
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab
from packages.optimisation.frontend.optimisation_ui_utils import render_optimisation_results_display
from packages.configuration.frontend.ui_utils import display_operation_result
from packages.simple.backend import simple_logic

def render_simple_mode_tab(ss):
    streamlit.header("🚚 Simplified Workflow")

    # Configure Section
    with streamlit.expander("Step 1: Setup Configuration", expanded=True):
        col_create, col_load = streamlit.columns(2)
        with col_create:
            if streamlit.button("Create New Blank Configuration", key="simple_create_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot create new configuration while JADE is running.")
                else:
                    config_logic.handle_new_config_action(ss)
                    streamlit.rerun()
        with col_load:
            if streamlit.button("Load Configuration from File", key="simple_load_btn", use_container_width=True):
                if ss.get("jade_platform_running"):
                    streamlit.warning("Cannot load configuration while JADE is running.")
                else:
                    config_logic.handle_load_config_action(ss)
                    streamlit.rerun()

        # Quick Generate Section
        streamlit.markdown("---")
        streamlit.write("#### Quick Generate Configuration")
        num_parcels = streamlit.number_input("Number of Parcels", min_value=0, value=ss.get("simple_num_parcels_to_generate", 5), key="simple_num_parcels")
        num_agents = streamlit.number_input("Number of Delivery Agents", min_value=0, value=ss.get("simple_num_agents_to_generate", 2), key="simple_num_agents")
        if streamlit.button("Generate and Load Quick Config", key="simple_generate_btn", use_container_width=True):
            result = simple_logic.generate_quick_config(ss, num_parcels, num_agents)
            display_operation_result(result)
            streamlit.rerun()

    # Optimisation Section
    with streamlit.expander("Step 2: Select Optimisation Method", expanded=True):
        if ss.get("jade_platform_running"):
            streamlit.warning("Optimisation script cannot be changed while JADE is running.")
        else:
            if ss.optimisation_script_loaded_successfully:
                streamlit.success(f"Loaded Script: {ss.optimisation_script_filename}")
            else:
                streamlit.info("No optimisation script loaded.")
            if streamlit.button("Load Optimisation Script", key="simple_load_script_btn", use_container_width=True):
                optimisation_logic.handle_initiate_load_script_action(ss)
                streamlit.rerun()

    # Execution Section
    with streamlit.expander("Step 3: Run Simulation & View Results", expanded=True):
        if not ss.get("jade_platform_running"):
            if streamlit.button("🚀 Start JADE Platform", key="simple_start_jade_btn", use_container_width=True, 
                              disabled=(not ss.config_data or not ss.optimisation_script_loaded_successfully)):
                execution_logic.handle_start_jade(ss)
                streamlit.rerun()
        else:
            streamlit.success("JADE Platform is Running")
            if streamlit.button("🏁 Run Full Optimisation", key="simple_run_btn", use_container_width=True):
                execution_logic.handle_trigger_mra_optimisation_cycle(                optimisation                optimisation_logic.run_optimisation_script(ss)
                execution_logic.handle_send_optimised_routes_to_mra(ss)
                streamlit.rerun()

        if ss.get("optimisation_run_complete"):
            render_optimisation_results_display(ss.optimisation_results)
            render_visualisation_tab(ss)

        if ss.get("jade_platform_running"):
            if streamlit.button("🛑 Stop JADE Platform", key="simple_stop_jade_btn", use_container_width=True):
                execution_logic.handle_stop_jade(ss)
                streamlit.rerun()
