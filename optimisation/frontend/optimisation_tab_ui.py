import streamlit
from optimisation.backend import optimisation_logic
from .initial_optimisation_view_ui import render_initial_optimisation_view
from .load_optimisation_script_view_ui import render_load_optimisation_script_view
from .edit_optimisation_parameters_view_ui import render_edit_optimisation_parameters_view

# Renders the entire Optimisation tab.
def render_optimisation_tab(ss):
    # Check if config data is missing or if the configuration is currently being edited.
    if not ss.config_data or ss.get("edit_mode", False):
        if not ss.config_data:
            warning_message = "Please create or load a configuration first"
        else: # This implies ss.config_data exists, so ss.get("edit_mode", False) must be True
            warning_message = "Please save or cancel the current configuration edits"
        streamlit.warning(warning_message)
        return # Prevent rendering the rest of the tab
    
    # If config_data exists and is not in edit_mode, proceed with view rendering.
    action = ss.get("optimisation_action_selected")

    if action == "load_script":
        render_load_optimisation_script_view(ss)
    elif action == "edit_parameters":
        render_edit_optimisation_parameters_view(ss)
    else: # This includes None (initial view) or any other unhandled actions.
        render_initial_optimisation_view(ss)
