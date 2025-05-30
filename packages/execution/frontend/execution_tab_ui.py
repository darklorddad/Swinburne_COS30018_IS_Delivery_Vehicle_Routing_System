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
    if "jade process is running" in msg_lower or "jade terminated" in msg_lower:
        return 'success'
    elif "fail" in msg_lower or "error" in msg_lower or "exception" in msg_lower:
        return 'error'
    elif "warn" in msg_lower:
        return 'warning'
    elif "success" in msg_lower or "started" in msg_lower or "stopped" in msg_lower or \
       "running" in msg_lower or "requested" in msg_lower or "terminated" in msg_lower or \
       "created" in msg_lower or "sent" in msg_lower or "processed" in msg_lower or \
       "forwarded" in msg_lower or "completed" in msg_lower or "connected" in msg_lower or "received" in msg_lower:
        return 'info'
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
        
        # Moved out of expander and removed expander
        streamlit.warning(
            "Please complete these steps first:\n\n" + 
            "\n".join([f"- {msg}" for msg in prereq_messages_list])
        )
        return # Stop rendering the rest of the Execution tab

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
                    "id": execution_logic.DEFAULT_MRA_NAME,
                    "capacity_weight": "N/A",  # MRA doesn't have weight capacity
                    "agent_class": execution_logic.DEFAULT_MRA_CLASS
                })
                # DAs
                if ss.config_data.get("delivery_agents"):
                    for da_config in ss.config_data["delivery_agents"]:
                        agents_to_create_data.append({
                            "id": da_config.get("id", "N/A"),
                            "capacity_weight": str(da_config.get("capacity_weight", "N/A")),
                            "agent_class": execution_logic.DEFAULT_DA_CLASS
                        })
                if agents_to_create_data:
                    streamlit.dataframe(
                        pd.DataFrame(agents_to_create_data),
                        column_order=("id", "capacity_weight", "agent_class"), # Ensure desired order
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    streamlit.info("No delivery agents defined in the current configuration.")


            if streamlit.button("Create agents", 
                                key="create_jade_agents_btn", 
                                use_container_width=True,
                                disabled=not config_loaded or ss.get("jade_agents_created", False) or not ss.get("jade_platform_running")):
                result = execution_logic.handle_create_agents(ss)
                display_operation_result(result)
                streamlit.rerun()

            if ss.get("jade_agent_creation_status_message"):
                msg_str = ss.jade_agent_creation_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
                ss.jade_agent_creation_status_message = None

    # --- Master Routing Agent Operations ---
    if ss.get("jade_platform_running"): # This section only active if JADE is running
        with streamlit.expander("Master Routing Agent Operations", expanded=True):
            streamlit.markdown("---")

            # --- Display Data to be Sent (Warehouse/Parcels from ss.config_data) ---
            if ss.config_data:
                warehouse_data = ss.config_data.get("warehouse_coordinates_x_y", "Not set")
                parcels_data = ss.config_data.get("parcels", [])
                
                if isinstance(warehouse_data, list) and len(warehouse_data) == 2:
                    wh_text = f"<strong>Warehouse Coordinates</strong><br><span style='font-size: 0.9em; color: #888;'>X: {warehouse_data[0]}, Y: {warehouse_data[1]}</span>"
                else:
                    wh_text = f"<strong>Warehouse Coordinates</strong><br><span style='font-size: 0.9em; color: #888;'>{str(warehouse_data)}</span>"
                streamlit.markdown(wh_text, unsafe_allow_html=True)
                
                # Display parcels table
                if parcels_data:
                    parcels_df = pd.DataFrame(parcels_data)
                    streamlit.dataframe(parcels_df, use_container_width=True, hide_index=True)
                else:
                    streamlit.info("No parcels in the current configuration to send.")
            else:
                streamlit.info("No configuration loaded to send to MRA.")

            # --- Send Warehouse & Parcel Data to MRA ---
            if streamlit.button("Send warehouse and parcel data to MRA", 
                                 key="send_warehouse_parcel_data_to_mra_btn", 
                                 use_container_width=True,
                                 disabled=not ss.get("jade_agents_created", False) or not ss.get("jade_platform_running", False) or not ss.config_data):
                result = execution_logic.handle_send_warehouse_parcel_data_to_mra(ss)
                # Always display the result immediately
                display_operation_result(result)
                # Store the message in session state for persistence
                if result:
                    ss.mra_initialization_message = result.get('message')
                streamlit.rerun()
            
            if ss.get("mra_initialization_message"):
                msg_str = ss.mra_initialization_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
                ss.mra_initialization_message = None

            if ss.get("mra_config_subset_data"):
                streamlit.markdown("##### Confirmation: Warehouse and Parcel Data received by MRA")
                streamlit.json(ss.mra_config_subset_data, expanded=False)
            streamlit.markdown("---")


            # --- Fetch Delivery Agent Statuses Section (via MRA) ---
            # --- Display DA Status Table ---
            if ss.get("fetched_delivery_agent_statuses") is not None:
                da_statuses = ss.fetched_delivery_agent_statuses
                if da_statuses:
                    status_df_data = []
                    for da_status in da_statuses:
                        status_df_data.append({
                            "id": da_status.get("id", "N/A"),
                            "capacity_weight": str(da_status.get("capacity_weight", "N/A")),
                            "operational_status": da_status.get("operational_status", "N/A")
                        })
                    df_da_statuses = pd.DataFrame(status_df_data)
                    df_da_statuses["capacity_weight"] = pd.to_numeric(df_da_statuses["capacity_weight"], errors='coerce').fillna("Error/NA")
                    streamlit.dataframe(df_da_statuses, use_container_width=True, hide_index=True)
                elif isinstance(da_statuses, list) and not da_statuses:
                    streamlit.info("No DA statuses were reported by the MRA.")

            if streamlit.button("Fetch DA statuses",
                                key="fetch_optimisation_data_btn",
                                use_container_width=True,
                                disabled=not ss.get("jade_agents_created", False)
                                ):
                result = optimisation_logic.fetch_delivery_agent_statuses(ss)
                display_operation_result(result)
                streamlit.rerun()

            if ss.get("da_status_fetch_message"):
                msg_str = ss.da_status_fetch_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
                ss.da_status_fetch_message = None # Clear after display

            streamlit.markdown("---") # Separator before optimisation section

            # --- Trigger MRA Optimisation Cycle (MRA compiles data, Python script runs) ---
            if streamlit.button("Run route optimisation",
                                 key="trigger_mra_optimisation_cycle_btn",
                                 use_container_width=True,
                                 disabled=not ss.get("jade_agents_created", False) or not ss.get("optimisation_script_loaded_successfully", False)
                                 ):
                # Clear previous results
                ss.optimisation_run_complete = False
                ss.optimisation_run_error = None
                ss.optimisation_results = None
                
                # Step 1: Ask MRA to compile data
                result_mra_data = execution_logic.handle_trigger_mra_optimisation_cycle(ss)
                display_operation_result(result_mra_data)
                if result_mra_data and result_mra_data.get('type') in ['success', 'info']:
                    # ss.data_for_optimisation_script is set by handle_trigger_mra_optimisation_cycle
                    # Step 2: If MRA data received, run the Python script with it
                    result_script_run = optimisation_logic.run_optimisation_script(ss)
                    display_operation_result(result_script_run)
                    
                    # Explicitly update session state based on script run results
                    if result_script_run:
                        if result_script_run.get('type') == 'success':
                            ss.optimisation_run_complete = True
                            ss.optimisation_results = result_script_run.get('results', None)
                        else:
                            ss.optimisation_run_error = result_script_run.get('message')
                            ss.optimisation_run_complete = False
                            ss.optimisation_results = None
                # Always rerun to reflect any state changes from both steps
                streamlit.rerun()

            # Show send routes button (disabled if no routes)
            routes_available = ss.get("optimisation_run_complete") and ss.optimisation_results and ss.optimisation_results.get("optimised_routes")
            if streamlit.button("Send routes to MRA",
                                key="send_routes_to_mra_btn", 
                                use_container_width=True,
                                disabled=not routes_available or not ss.get("jade_agents_created", False) or not ss.get("jade_platform_running", False)
                                ):
                execution_logic.handle_send_optimised_routes_to_mra(ss)
                streamlit.rerun()

            # Show dispatch status message (from sending routes to MRA)
            if ss.get("jade_dispatch_status_message"):
                msg_str = ss.jade_dispatch_status_message.replace("'MRA' successfully", "").rstrip('.')  # Remove redundant text and trailing dot
                streamlit.info(msg_str)  # Always show as blue info alert
                ss.jade_dispatch_status_message = None # Clear after display

            if ss.get("mra_optimisation_trigger_message"): # Message from MRA data compilation step
                msg_str = ss.mra_optimisation_trigger_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
                ss.mra_optimisation_trigger_message = None
            
            # This message comes from run_optimisation_script
            if ss.get("optimisation_execution_tab_run_status_message"): 
                msg_str = ss.optimisation_execution_tab_run_status_message
                msg_type = _determine_message_type_from_string(msg_str)
                display_operation_result({'type': msg_type, 'message': msg_str})
                ss.optimisation_execution_tab_run_status_message = None

            # Show optimisation results section if we have any state about optimisation
            if ss.get("optimisation_run_complete") or ss.get("optimisation_run_error"):
                if ss.optimisation_run_complete:
                    if ss.optimisation_results is not None:
                        results = ss.optimisation_results
                        all_parcels_assigned = (
                            "optimised_routes" in results and results["optimised_routes"] and
                            not ("unassigned_parcels_details" in results and results["unassigned_parcels_details"])
                        )
                        if all_parcels_assigned:
                            streamlit.info("All parcels were assigned")
                        else:
                            streamlit.warning("Not all parcels could be assigned")
                        
                        # Display the detailed optimisation results
                        render_optimisation_results_display(results)

                elif ss.optimisation_run_error:
                    streamlit.error(f"Optimisation Script Execution Error: {ss.optimisation_run_error}")
                elif not ss.optimisation_results:
                    streamlit.warning("Optimisation completed, but no results were returned by the script.")
                

            # Show dispatch status message (from sending routes to MRA)
            if ss.get("jade_dispatch_status_message"):
                msg_str = ss.jade_dispatch_status_message
                streamlit.info(msg_str)  # Always show as blue info alert
                ss.jade_dispatch_status_message = None # Clear after display