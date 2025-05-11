import streamlit
from configuration.backend import config_logic
from configuration.frontend.config_tab_ui import render_config_tab

# Applies custom CSS to the Streamlit app.
def _apply_custom_styling(ss):
    header_style_properties = "background-color: #1E1E1E !important;" # Always set background colour

    if not ss.show_header:
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
    streamlit.markdown(custom_css, unsafe_allow_html=True)

# Renders the main layout and tabs for the application.
def _render_main_layout(ss):
    # Create columns to centre the main content.
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower.

    with col2: # This is the main content area, styled as a card.
        streamlit.title("Delivery Vehicle Routing System")

        tab_config, tab_run, tab_results, tab_settings = streamlit.tabs([
            "Configuration",
            "Run Optimization",
            "Dashboard & Results",
            "Settings"
        ])

        with tab_config:
            render_config_tab(ss)
            
        with tab_run:
            streamlit.header("Run Optimization")
            if ss.config_data is None:
                streamlit.warning("Please load a configuration in the 'Configuration' tab first.")
            else:
                streamlit.write("Initiate the route optimization process here. Progress and logs may be displayed.")
                streamlit.write("Using configuration:")
                streamlit.json(ss.config_data)


        with tab_results:
            streamlit.header("Dashboard & Results")
            if ss.config_data is None: # Check if configuration data is available.
                streamlit.warning("Please load a configuration and run optimization to see results.")
            else:
                streamlit.write("Route visualizations and results will appear here.")

        with tab_settings:
            streamlit.header("UI Settings")
            streamlit.toggle(
                "Show Streamlit Header",
                value = ss.show_header,
                key = "show_header_toggle_widget",
                on_change = config_logic.handle_show_header_toggle,
                args = (ss,),
                help = "Toggle the visibility of the default Streamlit header bar."
            )

def main():
    streamlit.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Initialise session state variables using the function from config_logic
    # Use an alias for streamlit.session_state for brevity
    ss = streamlit.session_state
    config_logic.initialise_session_state(ss)

    _apply_custom_styling(ss)
    _render_main_layout(ss)

if __name__ == "__main__":
    main()
