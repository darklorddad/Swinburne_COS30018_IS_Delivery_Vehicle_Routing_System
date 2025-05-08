import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Initialize session state for header visibility
    if 'show_header' not in st.session_state:
        st.session_state.show_header = False # Default is off (header hidden)

    # Dynamically build CSS based on header visibility state
    header_style_properties = "background-color: #1E1E1E !important;" # Always set background color
    if not st.session_state.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid="stHeader"] {{
            {header_style_properties}
        }}

        /* Set a darker background color for the app */
        .stApp {{
            background-color: #1E1E1E !important;
        }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # Create columns to center the main content
    col1, col2, col3 = st.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        st.title("Delivery Vehicle Routing System")

        tab_setup, tab_run, tab_results, tab_settings = st.tabs([
            "Setup & Inputs", 
            "Run Optimization", 
            "Dashboard & Results",
            "Settings"
        ])

        with tab_setup:
            st.header("Setup & Inputs")
            st.write("Configure parameters, load delivery lists, and specify vehicle capacities here.")

        with tab_run:
            st.header("Run Optimization")
            st.write("Initiate the route optimization process here. Progress and logs may be displayed.")

        with tab_results:
            # Placeholder for future UI elements
            st.header("Dashboard & Results")
            st.write("Route visualizations and results will appear here.")

        with tab_settings:
            st.header("UI Settings")
            st.toggle(
                "Show Streamlit Header",
                key="show_header", # Use key to directly bind to st.session_state.show_header
                help="Toggle the visibility of the default Streamlit header bar."
            )
            # st.session_state.show_header is now automatically updated by this toggle.


if __name__ == "__main__":
    main()
