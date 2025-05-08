import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Custom CSS to hide the top decoration bar
    custom_css = """
    <style>
        /* Hide Streamlit's default top decoration bar */
        [data-testid="stDecoration"] {
            display: none !important;
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
        with st.container():
            # Placeholder for future UI elements
            st.header("Dashboard")
            st.write("Route visualizations and results will appear here.")

            st.markdown("---") # Adds a horizontal line for separation

            st.header("Input Parameters")
            st.write("Configuration options will be available here.")


if __name__ == "__main__":
    main()
