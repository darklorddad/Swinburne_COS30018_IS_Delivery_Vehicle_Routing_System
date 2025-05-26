import streamlit
import pandas as pd # For creating DataFrames for tables
import json
from ..backend import execution_logic
from packages.optimisation.backend import optimisation_logic
from packages.optimisation.frontend.optimisation_ui_utils import render_optimisation_results_display
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
    # Check prerequisites for JADE tab functionality
    config_loaded = ss.config_data is not None
    script_loaded = ss.get("optimisation_script_loaded_successfully", False)
    
    if not config_loaded or not script_loaded:
        prereq_messages_list = []
        if not config_loaded:
            prereq_messages_list.append("A configuration must be loaded (Configuration tab)")
        if not script_loaded:
            prereq_messages_list.append("An optimisation script must be loaded (Optimisation tab)")
        
        with streamlit.expander("Prerequisites Not Met", expanded=True):
            streamlit.markdown("---")
            streamlit.warning(
                "Please complete these steps first:\n\n" + 
                "\n".join([f"- {msg}" for msg in prereq_messages_list])
            )
        return # Stop rendering the rest of the Execution tab

    # Removed streamlit.header("JADE Agent Operations")

    # --- JADE Platform Control ---
    with streamlit.expander("JADE Management", expanded=True):
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
                execution_logic.handle_start_jade(ss)
                streamlit.rerun()
        with col_stop_jade:
            if streamlit.button("Stop", 
                                key="stop_jade_platform_btn", 
                                use_container_width=True,
                                disabled=not ss.get("jade_platform_running", False)):
                execution_logic.handle_stop_jade(ss)
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
                    "Agent ID": execution_logic.DEFAULT_MRA_NAME,
                    "Capacity Weight": "N/A",  # MRA doesn't have weight capacity
                    "Agent Class": execution_logic.DEFAULT_MRA_CLASS
                })
                # DAs
                if ss.config_data.get("delivery_agents"):
                    for da_config in ss.config_data["delivery_agents"]:
                        agents_to_create_data.append({
                            "Agent ID": da_config.get("id", "N/A"),
                            "Capacity Weight": da_config.get("capacity_weight", "N/A"),
                            "Agent Class": execution_logic.DEFAULT_DA_CLASS
                        })
                if agents_to_create_data:
                    streamlit.dataframe(
                        pd.DataFrame(agents_to_create_data),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    streamlit.info("No delivery agents defined in the current configuration.")


            if streamlit.button("Create agents", 
                                key="create_jade_agents_btn", 
                                use_container_width=True,
                                disabled=not config_loaded or ss.get("jade_agents_created", False)):
                result = execution_logic.handle_create_agents(ss)
                # Force rerun to immediately show status updates
                streamlit.rerun()

            # Display agent creation status message (persistently)
            if ss.get("jade_agent_creation_status_message"):
                msg_str = ss.jade_agent_creation_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})

    # --- Master Routing Agent Operations ---
    if ss.get("jade_platform_running"): # This section only active if JADE is running
        with streamlit.expander("Master Routing Agent Operations", expanded=True):
            streamlit.markdown("---")

            # --- Fetch Data Section ---
            if streamlit.button("Fetch Data for Optimisation & DA Status",
                                key="fetch_optimisation_data_btn",
                                use_container_width=True,
                                disabled=not ss.get("jade_agents_created", False)
                                ):
                result = optimisation_logic.fetch_data_for_optimisation(ss)
                display_operation_result(result)
                streamlit.rerun()

            if ss.optimisation_data_compilation_status_message:
                msg_str = ss.optimisation_data_compilation_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})

            # --- Display DA Capacity Status ---
            if ss.get("optimisation_input_data_json_str") and ss.get("optimisation_input_data_ready"):
                try:
                    full_data = json.loads(ss.optimisation_input_data_json_str)
                    da_statuses = full_data.get("delivery_agent_statuses", [])
                    if da_statuses:
                        streamlit.markdown("##### Delivery Agent Statuses")
                        status_df_data = []
                        for da_status in da_statuses:
                            status_df_data.append({
                                "Agent ID": da_status.get("agent_id", "N/A"),
                                "Capacity Weight": da_status.get("capacity_weight", "N/A"),
                                "Operational Status": da_status.get("operational_status", "N/A")
                            })
                        streamlit.dataframe(pd.DataFrame(status_df_data), use_container_width=True, hide_index=True)
                    else:
                        streamlit.info("No Delivery Agent statuses reported by MRA in the fetched data.")
                except json.JSONDecodeError:
                    streamlit.warning("Could not parse DA statuses from fetched data (invalid JSON).")
                except Exception as e:
                    streamlit.warning(f"Could not display DA statuses: {str(e)}")
                streamlit.markdown("---")

            # --- Display Data for Optimiser ---
            if ss.get("optimisation_input_data_json_str") and ss.get("optimisation_input_data_ready"):
                streamlit.markdown("##### Input Data for Optimisation Script")
                try:
                    parsed_input_data = json.loads(ss.optimisation_input_data_json_str)

                    # Display Warehouse Coordinates
                    wh_coords = parsed_input_data.get("warehouse_coordinates_x_y")
                    if wh_coords is not None: # Check if the key exists and has a value
                        streamlit.markdown(f"**Warehouse Coordinates (X, Y):** `{wh_coords}`")
                    else:
                        streamlit.info("Warehouse coordinates not found in the input data.")

                    # Display Parcels Table
                    parcels_input_data = parsed_input_data.get("parcels", [])
                    if parcels_input_data:
                        streamlit.markdown("###### Parcels")
                        streamlit.dataframe(pd.DataFrame(parcels_input_data), use_container_width=True, hide_index=True)
                    else:
                        streamlit.info("No parcel data found in the input for the optimisation script.")

                    # Display Delivery Agent Statuses Table (as input to the script)
                    # This will be similar to the "Delivery Agent Statuses" table displayed above,
                    # but explicitly shows what the script receives.
                    da_statuses_input_data = parsed_input_data.get("delivery_agent_statuses", [])
                    if da_statuses_input_data:
                        streamlit.markdown("###### Delivery Agent Statuses")
                        streamlit.dataframe(pd.DataFrame(da_statuses_input_data), use_container_width=True, hide_index=True)
                    else:
                        streamlit.info("No delivery agent status data found in the input for the optimisation script.")

                except json.JSONDecodeError:
                    streamlit.error("Error: Could not parse the input data JSON string for tabular display.")
                except Exception as e:
                    streamlit.error(f"An unexpected error occurred while preparing input data for display: {str(e)}")
                streamlit.markdown("---")

            # --- Run Optimisation Section ---
            run_disabled = not (ss.optimisation_script_loaded_successfully and ss.optimisation_input_data_ready)
            if streamlit.button("Run Optimisation Script",
                                key="run_optimisation_script_button",
                                use_container_width=True,
                                disabled=run_disabled):
                result = optimisation_logic.run_optimisation_script_with_prepared_data(ss)
                display_operation_result(result)
                if result and result.get('type') == 'success':
                    streamlit.rerun()

            if ss.optimisation_execution_tab_run_status_message:
                 msg_str = ss.optimisation_execution_tab_run_status_message
                 msg_type = _determine_message_type_from_string(msg_str)
                 display_operation_result({'type': msg_type, 'message': msg_str})

            if ss.optimisation_run_complete:
                if ss.optimisation_results is not None:
                    results = ss.optimisation_results
                    all_parcels_assigned = (
                        "optimised_routes" in results and results["optimised_routes"] and
                        not ("unassigned_parcels_details" in results and results["unassigned_parcels_details"])
                    )
                    if all_parcels_assigned:
                        streamlit.info("All parcels were assigned by the optimisation script.")
                    else:
                        streamlit.warning("Not all parcels could be assigned by the optimisation script.")
            elif ss.optimisation_run_error:
                 streamlit.error(f"Optimisation Script Execution Error: {ss.optimisation_run_error}")
            streamlit.markdown("---")

            # --- Route Dispatch to MRA Section ---
            optimisation_complete_with_results = ss.get("optimisation_run_complete", False) and ss.get("optimisation_results") is not None

            if not optimisation_complete_with_results:
                streamlit.warning("Optimisation results are not available to be sent. Please run optimisation first.")
            else:
                if ss.optimisation_results.get("optimised_routes"):
                    streamlit.markdown("##### Optimised Routes to be Sent to MRA")
                    routes_to_display_data = []
                    for route in ss.optimisation_results["optimised_routes"]:
                        routes_to_display_data.append({
                            "Agent ID": route.get("agent_id"),
                            "Stop Sequence": ", ".join(route.get("route_stop_ids", [])),
                            "Total Weight": route.get("total_weight"),
                            "Total Distance": route.get("total_distance")
                        })
                    if routes_to_display_data:
                        streamlit.dataframe(
                            pd.DataFrame(routes_to_display_data),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        streamlit.info("No optimised routes to display or send from results.")
                else:
                    streamlit.info("Optimisation results exist, but no 'optimised_routes' found to display or send.")

            if streamlit.button("Send Optimised Routes to MRA",
                                key="trigger_mra_dispatch_btn",
                                use_container_width=True,
                                disabled=not optimisation_complete_with_results or not ss.get("jade_agents_created", False)
                                ):
                result = execution_logic.handle_trigger_mra_processing(ss)
                display_operation_result(result)
                if result and result.get('type') == 'success':
                    streamlit.rerun()

            if ss.get("jade_dispatch_status_message"):
                msg_str = ss.jade_dispatch_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
