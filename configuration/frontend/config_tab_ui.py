import streamlit
import json # For the download component
import backend.config_logic
from .initial_view_ui import render_initial_view
from .load_view_ui import render_load_view
from .edit_view_ui import render_edit_view

def render_config_tab(ss):
    """Renders the entire Configuration tab."""
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
                height=1
            )
        backend.config_logic.finalize_download(ss)
        # A streamlit.rerun() might be implicitly handled by other actions,
        # or could be added here if the "Downloading..." message needs to be cleared faster.

    if not ss.edit_mode:
        if ss.action_selected == "load":
            render_load_view(ss)
        else: # Initial View (action_selected is None)
            render_initial_view(ss)
    else: # Edit Mode
        render_edit_view(ss)
