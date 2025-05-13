import streamlit
from optimisation.backend import optimisation_logic

# Renders the initial view of the Optimisation tab, 
# including script management, parameter configuration, and execution.
def render_initial_optimisation_view(ss):
    with streamlit.expander("Manage Optimisation Script", expanded = True):
        streamlit.markdown("---")
        if streamlit.button("Load script", key = "initiate_load_script_btn", use_container_width = True, help = "Load a new Python script for optimisation."):
            optimisation_logic.handle_initiate_load_script_action(ss)
            streamlit.rerun()

        if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
            streamlit.success(f"Script '{ss.optimisation_script_filename}' loaded successfully.")
            if streamlit.button("Clear Current Optimisation Script", key = "clear_optimisation_script_initial_view_btn", use_container_width = True, help = "Clears the loaded script and its parameters."):
                optimisation_logic.clear_optimisation_script(ss) # This also resets action_selected
                streamlit.rerun()
        elif ss.optimisation_script_error_message and not ss.optimisation_script_loaded_successfully:
            # This error message might have been set during a previous load attempt that failed,
            # and the user navigated away and came back.
            # Or if handle_initiate_load_script_action clears it, this might not be hit often here.
            streamlit.error(ss.optimisation_script_error_message)


    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema:
            params_list = ss.optimisation_script_param_schema["parameters"]
            if not params_list:
                streamlit.info("The optimisation script does not define any configurable parameters.")
            else:
                streamlit.subheader("Configure Optimisation Parameters")
                with streamlit.form(key = "optimisation_params_form"):
                    for param_info in params_list:
                        name = param_info.get("name")
                        label = param_info.get("label", name if name else "Unnamed Parameter")
                        ptype = param_info.get("type", "string")
                        current_value = ss.optimisation_script_user_values.get(name) 
                        help_text = param_info.get("help")
                        widget_key = f"param_widget_{name}"

                        if name is None:
                            streamlit.warning(f"Skipping parameter with no name: {param_info.get('label', '')}")
                            continue

                        if ptype == "integer":
                            val = current_value if isinstance(current_value, int) else param_info.get("default", 0)
                            ss.optimisation_script_user_values[name] = streamlit.number_input(
                                label, value = int(val),
                                min_value = param_info.get("min"), max_value = param_info.get("max"),
                                step = param_info.get("step", 1), help = help_text, key = widget_key
                            )
                        elif ptype == "float":
                            val = current_value if isinstance(current_value, (float, int)) else param_info.get("default", 0.0)
                            step = param_info.get("step", 0.01)
                            fmt = "%.5f" if step < 0.001 else ("%.3f" if step < 0.01 else "%.2f")
                            ss.optimisation_script_user_values[name] = streamlit.number_input(
                                label, value = float(val),
                                min_value = param_info.get("min"), max_value = param_info.get("max"),
                                step = step, format = fmt, help = help_text, key = widget_key
                            )
                        elif ptype == "boolean":
                            val = current_value if isinstance(current_value, bool) else param_info.get("default", False)
                            ss.optimisation_script_user_values[name] = streamlit.checkbox(
                                label, value = bool(val), help = help_text, key = widget_key
                            )
                        elif ptype == "selectbox":
                            options = param_info.get("options", [])
                            val = current_value if current_value in options else (options[0] if options else None)
                            idx = options.index(val) if val in options else 0
                            if val is not None:
                                ss.optimisation_script_user_values[name] = streamlit.selectbox(
                                    label, options = options, index = idx, help = help_text, key = widget_key
                                )
                            else:
                                streamlit.warning(f"Parameter '{label}' (selectbox) has no options or valid default.")
                        else: # Default to string/text input
                            val = str(current_value) if current_value is not None else str(param_info.get("default", ""))
                            ss.optimisation_script_user_values[name] = streamlit.text_input(
                                label, value = val, help = help_text, key = widget_key
                            )
                    
                    if streamlit.form_submit_button("Confirm Parameters"):
                        streamlit.success("Parameters confirmed and updated.")
                        streamlit.rerun() 
        else: 
             streamlit.info("No configurable parameters found or schema is missing/invalid for the loaded script.")

        # Action button: Run Optimisation
        run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
        if streamlit.button("Run Optimisation Script", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True, help = "Runs the loaded script with current configuration and parameters."):
            if not ss.config_data: 
                 streamlit.error("Cannot run: Main configuration data is missing.")
            else:
                optimisation_logic.execute_optimisation_script(ss)
                streamlit.rerun() 
        
        # Display execution results or errors
        if ss.optimisation_run_error:
            streamlit.error(f"Execution Error: {ss.optimisation_run_error}")
        if ss.optimisation_run_complete:
            if ss.optimisation_results is not None:
                streamlit.success("Optimisation script executed successfully!")
                with streamlit.expander("Optimisation Results", expanded = True):
                    streamlit.json(ss.optimisation_results)
            else: 
                 streamlit.warning("Optimisation script completed but returned no results (None).")

    elif not ss.optimisation_script_error_message: # No script loaded and no persistent error from previous attempt shown in manage section
        streamlit.caption("Click 'Load New Optimisation Script' to begin configuring an optimisation technique.")
