import streamlit

def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state for header visibility
    if "show_header" not in streamlit.session_state:
        streamlit.session_state.show_header = False # Default is off (header hidden)

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
    </style>
    """

    streamlit.markdown(custom_css, unsafe_allow_html = True)

    # Create columns to center the main content
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        streamlit.title("Delivery Vehicle Routing System")

        tab_setup, tab_run, tab_results, tab_settings = streamlit.tabs([
            "Setup & Inputs", 
            "Run Optimization", 
            "Dashboard & Results",
            "Settings"
        ])

        with tab_setup:
            streamlit.header("Setup & Inputs")
            streamlit.write("Configure parameters, load delivery lists, and specify vehicle capacities here.")

        with tab_run:
            streamlit.header("Run Optimization")
            streamlit.write("Initiate the route optimization process here. Progress and logs may be displayed.")

        with tab_results:
            # Placeholder for future UI elements
            streamlit.header("Dashboard & Results")
            streamlit.write("Route visualizations and results will appear here.")

        with tab_settings:
            streamlit.header("UI settings")
            streamlit.toggle(
                "Show Streamlit Header",
                key="show_header", # Use key to directly bind to streamlit.session_state.show_header
                help="Toggle the visibility of the default Streamlit header bar."
            )
            # streamlit.session_state.show_header is now automatically updated by this toggle.

if __name__ == "__main__":
    main()
