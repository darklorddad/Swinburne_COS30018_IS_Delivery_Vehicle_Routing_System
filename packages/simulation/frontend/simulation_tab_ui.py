import streamlit
import pandas as pd # For creating DataFrames for tables
from ..backend import simulation_logic
from packages.configuration.frontend.ui_utils import display_operation_result

# Helper to determine message type from a string for display_operation_result
def _determine_message_type_from_string(message_str):
    if not message_str:
        return 'info' 
    msg_lower = message_str.lower()
    if "success" in msg_lower or "started" in msg_lower or "stopped" in msg_lower or \
       "running" in msg_lower or "requested" in msg_lower or "terminated" in msg_lower or \
       "created" in msg_lower or "sent" in msg_lower or "processed" in msg_lower or \
       "forwarded" in msg_lower or "completed" in msg_lower or "connected" in msg_lower:
        return 'success'
    elif "fail" in msg_lower or "error" in msg_lower:
        return 'error'
    elif "warn" in msg_lower:
        return 'warning'
    return 'info'

# Renders the JADE tab for JADE interaction.
def render_jade_operations_tab(ss):
    # Removed streamlit.header("JADE Agent Operations")

    # --- JADE Platform Control ---
    with streamlit.expander("Platform Management", expanded=True):
        streamlit.markdown("---")
        
        # Display platform status message first
        if ss.get("jade_platform_status_message"):
            msg_str = ss.jade_platform_status_message
            msg_type = _determine_message_type_from_string(msg_str)
            display_operation_result({'type': msg_type, 'message': msg_str})

        col_start_jade, col_stop_jade = streamlit.columns(2)
        with col_start_jade:
            if streamlit.button("Start", 
                                key="start_jade_platform_btn", 
                                use_container_width=True,
                                disabled=ss.get("jade_platform_running", False)):
                simulation_logic.handle_start_jade(ss)
                streamlit.rerun()
        with col_stop_jade:
            if streamlit.button("Stop", 
                                key="stop_jade_platform_btn", 
                                use_container_width=True,
                                disabled=not ss.get("jade_platform_running", False)):
                simulation_logic.handle_stop_jade(ss)
                streamlit.rerun()
    
    # --- Agent Management (only if JADE is running) ---
    if ss.get("jade_platform_running"):
        with streamlit.expander("Agent Management", expanded=True):
            streamlit.markdown("---")
            config_loaded = ss.config_data is not None
            
            if not config_loaded:
                 streamlit.warning("A configuration must be loaded ('Configuration' tab) before agents can be created.")
            else:
                # Display agents to be created
                agents_to_create_data = []
                # MRA
                agents_to_create_data.append({
                    "Agent Name": simulation_logic.DEFAULT_MRA_NAME,
                    "Agent Class": simulation_logic.DEFAULT_MRA_CLASS,
                    "Type": "Master Routing Agent"
                })
                # DAs
                if ss.config_data.get("delivery_agents"):
                    for da_config in ss.config_data["delivery_agents"]:
                        agents_to_create_data.append({
                            "Agent Name": da_config.get("id", "N/A"),
                            "Agent Class": simulation_logic.DEFAULT_DA_CLASS,
                            "Type": "Delivery Agent"
                        })
                if agents_to_create_data:
                    streamlit.caption("The following agents will be configured for creation:")
                    streamlit.table(pd.DataFrame(agents_to_create_data)) # Use pandas for better table
                else:
                    streamlit.info("No delivery agents defined in the current configuration.")


            if streamlit.button("Create agents", 
                                key="create_jade_agents_btn", 
                                use_container_width=True,
                                disabled=not config_loaded or ss.get("jade_agents_created", False)):
                result = simulation_logic.handle_create_agents(ss)
                # ss.jade_agent_creation_status_message is set by the backend.
                # It will be displayed by the logic below.
                if result and result.get('type') == 'success':
                    streamlit.rerun() # Rerun to update button state etc.

            # Display agent creation status message (persistently)
            if ss.get("jade_agent_creation_status_message"):
                msg_str = ss.jade_agent_creation_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})

        # --- Route Management (only if JADE is running and agents are created) ---
        if ss.get("jade_agents_created"):
            with streamlit.expander("Route Management", expanded=True):
                streamlit.markdown("---")
                optimisation_complete = ss.get("optimisation_run_complete", False) and ss.get("optimisation_results") is not None

                if not optimisation_complete:
                    streamlit.warning("Optimisation results are not available. Please run an optimisation in the 'Optimisation' tab first.")
                else:
                    # Display routes to be sent
                    if ss.optimisation_results.get("optimised_routes"):
                        routes_to_display_data = []
                        for route in ss.optimisation_results["optimised_routes"]:
                            routes_to_display_data.append({
                                "Agent ID": route.get("agent_id"),
                                "Route Stops": " -> ".join(route.get("route_stop_ids", [])),
                                "Total Weight": route.get("total_weight"),
                                "Total Distance": route.get("total_distance")
                            })
                        if routes_to_display_data:
                            streamlit.caption("The following optimised routes will be sent to the MRA:")
                            streamlit.dataframe(pd.DataFrame(routes_to_display_data), use_container_width=True)
                        else:
                            streamlit.info("No optimised routes to display or send from results.")
                    else:
                        streamlit.info("Optimisation results exist, but no 'optimised_routes' found to display or send.")


                if streamlit.button("Send results to MRA", 
                                    key="trigger_mra_dispatch_btn", 
                                    use_container_width=True,
                                    disabled=not optimisation_complete):
                    result = simulation_logic.handle_trigger_mra_processing(ss)
                    # ss.jade_dispatch_status_message is set by the backend.
                    # It will be displayed by the logic below.
                    if result and result.get('type') == 'success':
                         streamlit.rerun()

                # Display route dispatch status message (persistently)
                if ss.get("jade_dispatch_status_message"):
                    msg_str = ss.jade_dispatch_status_message
                    msg_type = _determine_message_type_from_string(msg_str)
                    display_operation_result({'type': msg_type, 'message': msg_str})
                
        elif ss.get("jade_platform_running"): # Platform running, but agents not created
            streamlit.info("Create agents in JADE to enable route management.")

    else: # JADE platform not running
        streamlit.info("Start the JADE platform to enable agent and route management.")

    # --- JADE Logs & Communication ---
    with streamlit.expander("JADE Logs & Communication", expanded=False):
        streamlit.markdown("---")
        log_messages_to_display = []
        if ss.get("jade_platform_status_message"):
            log_messages_to_display.append(("Platform Status", ss.jade_platform_status_message))
        if ss.get("jade_agent_creation_status_message"):
            log_messages_to_display.append(("Agent Creation Status", ss.jade_agent_creation_status_message))
        # Assuming 'jade_dispatch_status_message' is the correct key for route dispatch status
        if ss.get("jade_dispatch_status_message"): 
            log_messages_to_display.append(("Route Dispatch Status", ss.jade_dispatch_status_message))

        if not log_messages_to_display:
            streamlit.info("No JADE log messages to display yet.")
        else:
            for category, msg_str in reversed(log_messages_to_display): # Show most recent first
                streamlit.caption(f"{category}:")
                msg_type = _determine_message_type_from_string(msg_str)
                
                if msg_type == 'success': streamlit.success(msg_str)
                elif msg_type == 'error': streamlit.error(msg_str)
                elif msg_type == 'warning': streamlit.warning(msg_str)
                else: streamlit.info(msg_str)
                # streamlit.markdown("---") # Optional: Separator between log entries
