import streamlit
import json # For the download component
from packages.configuration.backend import config_logic
from packages.configuration.backend.state_management import reset_simple_config_action
from .initial_view_ui import render_initial_view
from .load_view_ui import render_load_view
from .edit_view_ui import render_edit_view

# Renders the entire Configuration tab.
def render_config_tab(ss):
    # If user switches to standard Config tab while a simple_config_action was active, reset it.
    if ss.get("simple_mode") is False and ss.get("simple_config_action_selected") is not None:
        if ss.get("simple_config_action_selected") in ["new_edit", "load_config", "edit_current", "generate_config"]:
            reset_simple_config_action(ss) # This sets it to None
            streamlit.rerun() # Rerun to reflect that the simple_config_action is no longer active

    # Handle pending download if initiated
    if ss.get("initiate_download", False):
        if ss.pending_download_data and ss.pending_download_filename:
            streamlit.components.v1.html(
                f"""
                <html>
                    <head>
                        <title>Downloading...</title>
                        <script>
                            window.onload = function() {{
                                var link = document.createElement('a');
                                link.href = 'data:application/json;charset=utf-8,' + encodeURIComponent({json.dumps(ss.pending_download_data)});
                                link.download = {json.dumps(ss.pending_download_filename)};
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                            }};
                        </script>
                    </head>
                    <body></body>
                </html>
                """,
                height = 1
            )
        config_logic.finalize_download(ss)
        # streamlit.rerun() could be used here to clear the "Downloading..." message faster if needed.

    if not ss.edit_mode:
        if ss.action_selected == "load":
            render_load_view(ss)
        else: # Initial View (action_selected is None)
            render_initial_view(ss)
    else: # Edit Mode
        render_edit_view(ss)
