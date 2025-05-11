import streamlit
from configuration.backend import config_logic
import json
from configuration.frontend.config_tab_ui import render_config_tab
# import copy # No longer needed


def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state variables using the function from config_logic
    config_logic.initialize_session_state(streamlit.session_state)

    # Dynamically build CSS based on header visibility state
    header_style_properties = "background-color: #1E1E1E !important;" # Always set background color

    if not streamlit.session_state.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /* Set a darker background color for the app */
        .stApp {{
            background-color: #1E1E1E !important;
        }}

        /* Hide step buttons on number inputs */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {{
            display: none !important;
            visibility: hidden !important;
        }}
    </style>
    """

    streamlit.markdown(custom_css, unsafe_allow_html = True)

    # Create columns to center the main content
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        streamlit.title("Delivery Vehicle Routing System")

        tab_config, tab_run, tab_results, tab_settings = streamlit.tabs([
            "Configuration",
            "Run Optimization",
            "Dashboard & Results",
            "Settings"
        ])

        with tab_config:
            render_config_tab(streamlit.session_state)
            
        with tab_run:
            streamlit.header("Run Optimization")
            if streamlit.session_state.config_data is None:
                streamlit.warning("Please load a configuration in the 'Configuration' tab first.")
            else:
                streamlit.write("Initiate the route optimization process here. Progress and logs may be displayed.")
                streamlit.write("Using configuration:")
                streamlit.json(streamlit.session_state.config_data)


        with tab_results:
            streamlit.header("Dashboard & Results")
            if streamlit.session_state.config_data is None: # Or more specific check like "if results exist"
                streamlit.warning("Please load a configuration and run optimization to see results.")
            else:
                streamlit.write("Route visualizations and results will appear here.")

        with tab_settings:
            streamlit.header("UI Settings")
            streamlit.toggle(
                "Show Streamlit Header",
                value=streamlit.session_state.show_header,
                key="show_header_toggle_widget", # Changed key to match config_logic
                on_change=config_logic.handle_show_header_toggle,
                args=(streamlit.session_state,),
                help="Toggle the visibility of the default Streamlit header bar."
            )

if __name__ == "__main__":
    main()
