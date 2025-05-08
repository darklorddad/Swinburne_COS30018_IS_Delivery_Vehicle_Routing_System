import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    st.title("🚚 Delivery Vehicle Routing System")

    # Create columns to center the main content
    col1, col2, col3 = st.columns([1, 6, 1]) # Adjust ratios as needed for centering

    with col2: # This will be our "card" area
        with st.container():
            # Placeholder for future UI elements
            st.header("Dashboard")
            st.write("Route visualizations and results will appear here.")

            st.markdown("---") # Adds a horizontal line for separation

            st.header("Input Parameters")
            st.write("Configuration options will be available here.")


if __name__ == "__main__":
    main()
