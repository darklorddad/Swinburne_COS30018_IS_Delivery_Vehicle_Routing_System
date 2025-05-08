import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Custom CSS for app styling (hides decoration/header, sets dark background)
    custom_css = """
    <style>
        /* Hide Streamlit's default top decoration bar */
        [data-testid="stDecoration"] {
            display: none !important;
        }

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

        tab1, tab2 = st.tabs(["Dashboard", "Input Parameters"])

        with tab1:
            # Placeholder for future UI elements
            st.header("Dashboard")
            st.write("Route visualizations and results will appear here.")

        with tab2:
            st.header("Input Parameters")
            st.write("Configuration options will be available here.")


if __name__ == "__main__":
    main()
