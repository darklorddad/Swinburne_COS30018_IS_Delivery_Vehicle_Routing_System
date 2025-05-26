import streamlit
from packages.configuration.backend import config_logic
from packages.configuration.frontend.config_tab_ui import render_config_tab
from packages.optimisation.backend import optimisation_logic
from packages.optimisation.frontend.optimisation_tab_ui import render_optimisation_tab
from packages.execution.backend import execution_logic 
from packages.execution.frontend.execution_tab_ui import render_jade_operations_tab 
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab # New import

# Applies custom CSS to the Streamlit app.
def _apply_custom_styling(ss):
    header_style_properties = "background-color: transparent !important;" 

    if not ss.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /* Set a darker background colour for the app */
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), /* 50% Darkening Overlay */
            url(https://www.transparenttextures.com/patterns/otis-redding.png), 
            radial-gradient(at 55% 17%, hsla(43, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 27% 78%, hsla(187, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 94% 10%, hsla(24, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 21% 1%, hsla(332, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 7% 96%, hsla(183, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 95% 32%, hsla(263, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 53% 81%, hsla(33, 71%, 37%, 1) 0px, transparent 50%);
        }}

        /* Hide step buttons on number inputs */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Ensure text inputs have a visible black border and change colour on focus */
        div[data-testid="stTextInputRootElement"] {{
            border-color: #000000 !important;
            border-radius: 0.5rem !important;
        }}
        div[data-testid="stTextInputRootElement"]:focus-within {{
            border-color: #007BFF !important;
        }}

        /* Style select dropdown child wrapper to match text/number input borders */
        div[data-baseweb="select"] > div {{
            border: 1px solid #000000 !important;
            border-radius: 0.5rem !important;
        }}
        div[data-baseweb="select"]:focus-within > div {{
            border-color: #007BFF !important;
        }}

        /* Style for key content containers (tab panels, expanders) */
        div[data-testid="stTabPanel"],
        div[data-testid="stExpander"] > details {{
            background-color: rgba(0, 0, 0, 0.10);
            backdrop-filter: blur(16px);
            /* Add some padding to make content look better inside these containers */
            padding: 1rem; 
            /* Add rounded corners for a softer look */
            border-radius: 0.5rem; 
        }}
    </style>
    """
    streamlit.markdown(custom_css, unsafe_allow_html = True)

# Renders the main layout and tabs for the application.
def _render_main_layout(ss):
    # Create columns to centre the main content.
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5]) # Adjust ratios to make middle narrower.

    with col2: # This is the main content area, styled as a card.
        streamlit.title("Delivery Vehicle Routing System")

        # JADE tab accessibility will be handled within its own rendering function.
        # Tabs are now created unconditionally.
        tabs_list = [
            "Configuration",
            "Optimisation", 
            "Execution", 
            "Visualisation",
            "Settings"
        ]
        tab_config, tab_optimisation, tab_execution, tab_visualisation, tab_settings = streamlit.tabs(tabs_list)

        with tab_config:
            render_config_tab(ss)

        with tab_optimisation:
            render_optimisation_tab(ss)
            
        with tab_execution: 
            render_jade_operations_tab(ss) 

        with tab_visualisation: # Changed from tab_results
            render_visualisation_tab(ss) # Call the new rendering function

        with tab_settings:
            with streamlit.expander("User Interface", expanded=True):
                streamlit.markdown("---")
                streamlit.toggle(
                "Show Streamlit header",
                value = ss.show_header,
                key = "show_header_toggle_widget",
                on_change = config_logic.handle_show_header_toggle,
                args = (ss,),
            )

def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state variables using the function from config_logic
    # Use an alias for streamlit.session_state for brevity
    ss = streamlit.session_state
    config_logic.initialise_session_state(ss)
    optimisation_logic.initialise_session_state(ss) # Initialise optimisation state
    execution_logic.initialise_session_state(ss) # Initialise execution state

    _apply_custom_styling(ss)
    _render_main_layout(ss)

if __name__ == "__main__":
    main()
