import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    st.title("🚚 Delivery Vehicle Routing System")

    st.sidebar.title("Controls")
    st.sidebar.info(
        "Use the options below to configure the routing problem and view results."
    )

    # Placeholder for future UI elements
    st.header("Dashboard")
    st.write("Route visualizations and results will appear here.")

    st.header("Input Parameters")
    st.write("Configuration options will be available here.")


if __name__ == "__main__":
    main()
