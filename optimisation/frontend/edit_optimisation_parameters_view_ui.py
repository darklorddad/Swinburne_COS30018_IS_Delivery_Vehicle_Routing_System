import streamlit
from packages.optimisation.backend import optimisation_logic
from packages.configuration.frontend.ui_utils import display_operation_result # For displaying save result

# Renders the view for editing optimisation script parameters.
def render_edit_optimisation_parameters_view(ss):
    # streamlit.subheader("Configure Optimisation Parameters") # Removed as per request

    if not ss.optimisation_script_param_schema or "parameters" not in ss.optimisation_script_param_schema:
        streamlit.warning("Parameter schema is not available. Cannot edit parameters.")
        if streamlit.button("Cancel", key="cancel_opt_menu_no_schema", use_container_width=True): # Renamed and made full width for consistency
            optimisation_logic.handle_cancel_edit_parameters_action(ss) 
            streamlit.rerun()
        return

    params_list = ss.optimisation_script_param_schema["parameters"]
    if not params_list:
        streamlit.info("The optimisation script does not define any configurable parameters") # Removed period
        if streamlit.button("Cancel", key="cancel_opt_menu_no_params", use_container_width=True): # Renamed and made full width for consistency
            optimisation_logic.handle_cancel_edit_parameters_action(ss)
            streamlit.rerun()
        return

    # Note: Parameters are directly updated in ss.optimisation_script_user_values by widgets.
    # The form's "submit" button is not strictly necessary here if we have dedicated Save/Cancel buttons below,
    # but keeping the form structure can be good for grouping.
    # We will not use form_submit_button, but rather explicit Save/Cancel buttons.
    
    with streamlit.expander("Parameters", expanded=True):
        streamlit.markdown("---")
        for param_info in params_list:
            name = param_info.get("name")
            label = param_info.get("label", name if name else "Unnamed Parameter")
            ptype = param_info.get("type", "string")
            # Get current value from state, which includes defaults initially or user's latest edits.
            current_value = ss.optimisation_script_user_values.get(name) 
            help_text = param_info.get("help")
            widget_key = f"param_edit_widget_{name}" # Unique key for each widget

            if name is None:
                streamlit.warning(f"Skipping parameter with no name: {param_info.get('label', '')}")
                continue

            if ptype == "integer":
                val = current_value if isinstance(current_value, int) else param_info.get("default", 0)
                ss.optimisation_script_user_values[name] = streamlit.number_input(
                    label, value=int(val),
                    min_value=param_info.get("min"), max_value=param_info.get("max"),
                    step=param_info.get("step", 1), help=help_text, key=widget_key
                )
            elif ptype == "float":
                val = current_value if isinstance(current_value, (float, int)) else param_info.get("default", 0.0)
                step = param_info.get("step", 0.01)
                fmt = "%.5f" if step < 0.001 else ("%.3f" if step < 0.01 else "%.2f")
                ss.optimisation_script_user_values[name] = streamlit.number_input(
                    label, value=float(val),
                    min_value=param_info.get("min"), max_value=param_info.get("max"),
                    step=step, format=fmt, help=help_text, key=widget_key
                )
            elif ptype == "boolean":
                val = current_value if isinstance(current_value, bool) else param_info.get("default", False)
                ss.optimisation_script_user_values[name] = streamlit.checkbox(
                    label, value=bool(val), help=help_text, key=widget_key
                )
            elif ptype == "selectbox":
                options = param_info.get("options", [])
                val = current_value if current_value in options else (options[0] if options else None)
                idx = options.index(val) if val in options else 0
                if val is not None:
                    ss.optimisation_script_user_values[name] = streamlit.selectbox(
                        label, options=options, index=idx, help=help_text, key=widget_key
                    )
                else:
                    streamlit.warning(f"Parameter '{label}' (selectbox) has no options or valid default.")
            else: # Default to string/text input
                val = str(current_value) if current_value is not None else str(param_info.get("default", ""))
                ss.optimisation_script_user_values[name] = streamlit.text_input(
                    label, value=val, help=help_text, key=widget_key
                )
    
    col_save, col_cancel = streamlit.columns(2) # Swapped columns
    with col_save: # Save button now on the left
        if streamlit.button("Save", key="save_edit_params_btn", use_container_width=True):
            result = optimisation_logic.handle_save_parameters_action(ss)
            display_operation_result(result) # Show success message
            streamlit.rerun()

    with col_cancel: # Cancel button now on the right
        if streamlit.button("Cancel", key="cancel_edit_params_btn", use_container_width=True):
            optimisation_logic.handle_cancel_edit_parameters_action(ss)
            streamlit.rerun()
