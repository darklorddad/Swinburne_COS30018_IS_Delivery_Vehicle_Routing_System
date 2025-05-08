import streamlit as st

def main():
    st.set_page_config(layout="wide", page_title="Delivery Vehicle Routing System")

    # Custom CSS to style the app and hide the top decoration bar
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

        /* Hide Streamlit's default top decoration bar */
        [data-testid="stDecoration"] {
            display: none !important;
        }

        /* Main app background */
        .stApp {
            background-color: #131314; /* Dark background */
        }

        /* General text color and font */
        body, .stMarkdown, .stTextInput, .stTextArea, .stSelectbox, .stRadio > label > div {
            color: #e8eaed !important; /* Light gray text */
            font-family: 'Roboto', sans-serif !important;
        }

        /* Titles and Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #e8eaed !important; /* Light gray text for headers */
            font-family: 'Roboto', sans-serif !important;
        }
        
        /* Style for the horizontal line */
        hr {
            border-top: 1px solid #3c4043; /* A slightly lighter gray for dividers */
        }

        /* Input widgets styling */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {
            background-color: #202124 !important; /* Darker input background */
            color: #e8eaed !important; /* Light text in input */
            border: 1px solid #3c4043 !important;
            border-radius: 4px;
        }
        /* Placeholder text color for inputs */
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: #969ba1 !important;
        }

        /* Button styling */
        .stButton > button {
            background-color: #8ab4f8; /* Blue for buttons */
            color: #202124 !important; /* Dark text on blue buttons */
            border: none !important;
            padding: 0.6em 1.2em !important;
            border-radius: 4px !important;
            font-weight: bold !important;
            font-family: 'Roboto', sans-serif !important;
        }
        .stButton > button:hover {
            background-color: #aecbfa !important; /* Lighter blue on hover */
        }
        .stButton > button:focus {
            outline: none !important;
            box-shadow: 0 0 0 2px #131314, 0 0 0 4px #8ab4f8 !important; /* Focus ring */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # Create columns to center the main content
    col1, col2, col3 = st.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower

    with col2: # This will be our "card" area
        st.title("🚚 Delivery Vehicle Routing System")
        with st.container():
            # Placeholder for future UI elements
            st.header("Dashboard")
            st.write("Route visualizations and results will appear here.")

            st.markdown("---") # Adds a horizontal line for separation

            st.header("Input Parameters")
            st.write("Configuration options will be available here.")


if __name__ == "__main__":
    main()
