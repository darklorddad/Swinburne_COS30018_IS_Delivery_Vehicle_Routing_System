import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Custom CSS for app styling (hides decoration/header, sets dark background)
    custom_css = """
    <style>
        /* Hide Streamlit's default header */
        header[data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important; /* Extra measure to ensure it's hidden */
        }

        /* Set a darker background color for the app */
        .stApp {
            background-color: #1E1E1E !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # Create columns to center the main content
    col1, col2, col3 = st.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        st.title("Delivery Vehicle Routing System")

        tab_setup, tab_run, tab_results = st.tabs(["Setup & Inputs", "Run Optimization", "Dashboard & Results"])

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


if __name__ == "__main__":
    main()
