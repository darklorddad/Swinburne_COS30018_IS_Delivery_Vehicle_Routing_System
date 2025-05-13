import streamlit

from optimisation.backend import optimisation_logic

def render_optimisation_tab(ss):
    # Check if config data is missing or if we are in edit mode in the configuration tab
    if not ss.config_data or ss.get("edit_mode", False):
        # The tab name itself (now "Optimisation") serves as the title.
        # No need for an additional streamlit.header() here when disabled.
        if not ss.config_data:
            warning_message = "Please create or load a configuration in the 'Configuration' tab first. The Optimisation tab requires an active configuration to proceed"
        else: # Implies ss.edit_mode is True
            warning_message = "Please save or cancel the current configuration edits in the 'Configuration' tab before proceeding with optimisation setup"
        streamlit.warning(warning_message)
        return # Prevent rendering the rest of the tab
    
    # If config_data exists and not in edit_mode, proceed with the normal tab rendering.
    # The main tab title "Optimisation" is already provided by Streamlit's tab system.
    # No need for an additional streamlit.header() here.

    # The info message below is now redundant due to the check above.
    # if not ss.config_data: 
    #     streamlit.info("INFO: Main configuration not yet loaded. You can load an optimisation script, but running it will require the main configuration from the 'Configuration' tab.")

    with streamlit.expander("Upload Optimisation Script", expanded = not ss.optimisation_script_loaded_successfully):
        streamlit.markdown("---")
        # The file uploader's state is managed by Streamlit.
        # clear_optimisation_script sets the uploader's key in session_state to None to clear it.
        streamlit.file_uploader(
            "Select a Python optimisation script to prepare for loading",
            type = ["py"],
            key = "optimisation_file_uploader_widget", # Session state key for the widget
            # on_change callback removed; loading is now triggered by the button below.
            # args parameter is not needed as on_change is removed.
            help = "The script must be UTF-8 encoded and contain 'get_params_schema()' and 'run_optimisation(config_data, params)' functions."
        )

    # Button to explicitly load the script after selection, moved outside the expander
    # Disable button if no file is selected in the uploader
    load_script_button_disabled = ss.get("optimisation_file_uploader_widget") is None
    if streamlit.button("Load selected script", 
                        key = "load_optimisation_script_button", 
                        use_container_width = True, 
                        disabled = load_script_button_disabled,
                        help = "Load the script selected in the uploader above. The button is disabled if no script is selected."):
        # The handle_optimisation_file_upload function internally checks 
        # if a file is present in ss.get("optimisation_file_uploader_widget").
        optimisation_logic.handle_optimisation_file_upload(ss)
        streamlit.rerun()

    if ss.optimisation_script_error_message:
        streamlit.error(ss.optimisation_script_error_message)

    if ss.optimisation_script_loaded_successfully and ss.optimisation_script_filename:
        streamlit.success(f"Script '{ss.optimisation_script_filename}' loaded successfully.")
        
        if ss.optimisation_script_param_schema and "parameters" in ss.optimisation_script_param_schema:
            params_list = ss.optimisation_script_param_schema["parameters"]
            if not params_list:
                streamlit.info("The optimisation script does not define any configurable parameters.")
            else:
                streamlit.subheader("Configure Optimisation Parameters")
                # Using a form for parameters. Values are updated in session state on widget interaction.
                with streamlit.form(key = "optimisation_params_form"):
                    for param_info in params_list:
                        name = param_info.get("name")
                        label = param_info.get("label", name if name else "Unnamed Parameter")
                        ptype = param_info.get("type", "string")
                        # Get current value from state, which includes defaults initially.
                        current_value = ss.optimisation_script_user_values.get(name) 
                        help_text = param_info.get("help")
                        widget_key = f"param_widget_{name}" # Unique key for each widget

                        if name is None: # Skip parameter if name is not defined
                            streamlit.warning(f"Skipping parameter with no name: {param_info.get('label', '')}")
                            continue

                        if ptype == "integer":
                            # Ensure current_value is int, or use default from schema, or 0.
                            val = current_value if isinstance(current_value, int) else param_info.get("default", 0)
                            ss.optimisation_script_user_values[name] = streamlit.number_input(
                                label, value = int(val),
                                min_value = param_info.get("min"), max_value = param_info.get("max"),
                                step = param_info.get("step", 1), help = help_text, key = widget_key
                            )
                        elif ptype == "float":
                            val = current_value if isinstance(current_value, (float, int)) else param_info.get("default", 0.0)
                            step = param_info.get("step", 0.01)
                            # Determine format based on step precision.
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
                            if val is not None: # Only render if there are options and a valid value
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
                        # Parameters are already updated in ss.optimisation_script_user_values.
                        # This button serves as an explicit confirmation step.
                        streamlit.success("Parameters confirmed and updated.")
                        streamlit.rerun() # Rerun to reflect any changes if needed by other parts of UI.
        else: # No parameters defined or schema issue
             streamlit.info("No configurable parameters found or schema is missing/invalid for the loaded script.")


        # Action buttons area
        st_cols = streamlit.columns([1, 1, 2]) # Adjust ratios for button layout
        with st_cols[0]:
            run_disabled = not (ss.optimisation_script_loaded_successfully and ss.config_data)
            if streamlit.button("Run Optimisation Script", key = "run_optimisation_script_button", disabled = run_disabled, use_container_width = True, help = "Runs the loaded script with current configuration and parameters."):
                if not ss.config_data: # Should be caught by disabled state, but double check.
                     streamlit.error("Cannot run: Main configuration data is missing.")
                else:
                    optimisation_logic.execute_optimisation_script(ss)
                    streamlit.rerun() # Rerun to display results or errors from execution.
        
        with st_cols[1]:
            if streamlit.button("Clear Optimisation Script", key = "clear_optimisation_script_button", use_container_width = True, help = "Clears the loaded script and its parameters."):
                optimisation_logic.clear_optimisation_script(ss)
                streamlit.rerun() # Rerun to update UI (e.g., clear file uploader, hide params).

        # Display execution results or errors
        if ss.optimisation_run_error:
            streamlit.error(f"Execution Error: {ss.optimisation_run_error}")
        if ss.optimisation_run_complete:
            if ss.optimisation_results is not None:
                streamlit.success("Optimisation script executed successfully!")
                with streamlit.expander("Optimisation Results", expanded = True):
                    streamlit.json(ss.optimisation_results)
            else: # Script ran but returned None
                 streamlit.warning("Optimisation script completed but returned no results (None).")

    elif not ss.optimisation_script_error_message: # If not loaded successfully AND no error message is currently shown
        # This implies optimisation_script_loaded_successfully is False.
        streamlit.caption("Upload a Python script and click 'Load selected script' to begin configuring an optimisation technique.")

    # Optional: Debug area to inspect session state related to optimisation
    # with streamlit.expander("Optimisation State (Debug)"):
    #     debug_data = {k: v for k, v in ss.items() if k.startswith("optimisation_script_") or k.startswith("optimisation_run_")}
    #     streamlit.json(debug_data)
