import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Custom CSS to hide the top decoration bar
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

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

        /* Apply custom font and text color */
        body, .stMarkdown, .stTextInput, .stTextArea, .stSelectbox, .stRadio > label > div,
        h1, h2, h3, h4, h5, h6, .stButton > button {
            font-family: 'Roboto', sans-serif !important;
            color: #e8eaed !important; /* Light gray text for readability on dark background */
        }

        /* Specific styling for headers if needed, though covered by the above */
        h1, h2, h3 {
            color: #e8eaed !important;
        }

        /* Ensure input fields also use the font and have appropriate contrast */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {
            background-color: #2a2a2e !important; /* Slightly lighter than main bg for inputs */
            color: #e8eaed !important;
            border: 1px solid #3c4043 !important;
        }
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #969ba1 !important;
        }

        /* Button text color (background is often set by theme or other CSS) */
        /* If you want to style buttons further, add rules here */
        .stButton > button {
            /* Example: background-color: #007bff; border: none; */
            /* For now, just ensuring font and text color from above are applied */
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
