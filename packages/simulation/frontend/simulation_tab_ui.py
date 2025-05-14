import streamlit
from ..backend import simulation_logic
from packages.configuration.frontend.ui_utils import display_operation_result 

# Renders the Simulation tab for JADE interaction.
def render_simulation_tab(ss):
    streamlit.header("Agent-Based Simulation Control (JADE)")

    # --- JADE Platform Control ---
    with streamlit.expander("JADE Platform Management", expanded=True):
        streamlit.markdown("---")
        col_start_jade, col_stop_jade = streamlit.columns(2)
        with col_start_jade:
            if streamlit.button("Start JADE Platform", 
                                key="start_jade_platform_btn", 
                                use_container_width=True,
                                disabled=ss.get("jade_platform_running", False)):
                simulation_logic.handle_start_jade(ss)
                streamlit.rerun()
        with col_stop_jade:
            if streamlit.button("Stop JADE Platform", 
                                key="stop_jade_platform_btn", 
                                use_container_width=True,
                                disabled=not ss.get("jade_platform_running", False)):
                simulation_logic.handle_stop_jade(ss)
                streamlit.rerun()

        if ss.get("jade_platform_status_message"):
            # Determine message type based on keywords for better display
            msg = ss.jade_platform_status_message
            if "success" in msg.lower() or "started" in msg.lower() or "stopped" in msg.lower() or "running" in msg.lower() or "requested" in msg.lower() or "terminated" in msg.lower():
                display_operation_result({'type': 'success', 'message': msg})
            elif "fail" in msg.lower() or "error" in msg.lower():
                display_operation_result({'type': 'error', 'message': msg})
            else:
                display_operation_result({'type': 'info', 'message': msg})
    
    # --- Agent Management (only if JADE is running) ---
    if ss.get("jade_platform_running"):
        with streamlit.expander("Agent Creation & Management", expanded=True):
            streamlit.markdown("---")
            # Pre-requisite checks for creating agents
            config_loaded = ss.config_data is not None
            
            if not config_loaded:
                 streamlit.warning("A configuration must be loaded ('Configuration' tab) before agents can be created.")

            if streamlit.button("Create Agents in JADE", 
                                key="create_jade_agents_btn", 
                                use_container_width=True,
                                disabled=not config_loaded or ss.get("jade_agents_created", False)):
                result = simulation_logic.handle_create_agents(ss)
                displayed = display_operation_result(result) # This will display success or error
                # Only rerun if the operation was successful, allowing error/warning messages to persist.
                if displayed and result.get('type') == 'success':
                    streamlit.rerun()
                elif not displayed: # Fallback if display_operation_result didn't show anything
                    streamlit.rerun()


            # The status message is now handled by the display_operation_result call above.
            # The session state ss.jade_agent_creation_status_message is still set by
            # simulation_logic.handle_create_agents for potential other uses,
            # but we don't need to re-display it here immediately after the button action.


        # --- Simulation Run (only if JADE is running and agents are created) ---
        if ss.get("jade_agents_created"):
            with streamlit.expander("Simulation Execution", expanded=True):
                streamlit.markdown("---")
                # Pre-requisite checks for running simulation
                optimisation_complete = ss.get("optimisation_run_complete", False) and ss.get("optimisation_results") is not None

                if not optimisation_complete:
                    streamlit.warning("Optimisation results are not available. Please run an optimisation in the 'Optimisation' tab first.")

                if streamlit.button("Run Simulation with JADE Agents", 
                                    key="run_jade_simulation_btn", 
                                    use_container_width=True,
                                    disabled=not optimisation_complete):
                    result = simulation_logic.handle_run_simulation(ss)
                    displayed = display_operation_result(result) # Displays success/error/warning
                    # Only rerun if the operation was successful, allowing error/warning messages to persist.
                    if displayed and result.get('type') == 'success':
                        streamlit.rerun()
                    elif not displayed: # Fallback if display_operation_result didn't show anything
                        streamlit.rerun()
                
                # The status message is now handled by the display_operation_result call above.
                # The session state ss.jade_simulation_status_message is still set by
                # simulation_logic.handle_run_simulation for potential other uses,
                # but we don't need to re-display it here immediately after the button action.

        elif ss.get("jade_platform_running"): # Platform running, but agents not created
            streamlit.info("Create agents in JADE to enable simulation execution.")

    else: # JADE platform not running
        streamlit.info("Start the JADE platform to enable agent management and simulation.")
