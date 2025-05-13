import streamlit
from configuration.backend import config_logic
from configuration.frontend.config_tab_ui import render_config_tab
from optimisation.backend import optimisation_logic
from optimisation.frontend.optimisation_tab_ui import render_optimisation_tab

# Applies custom CSS to the Streamlit app.
def _apply_custom_styling(ss):
    header_style_properties = "background-color: transparent !important;" # Set background to transparent

    if not ss.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /* Set a darker background color for the app */
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), /* 50% Darkening Overlay */
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

        /* Style for key content containers (tab panels, expanders) */
        div[data-testid="stTabPanel"],
        div[data-testid="stExpander"] {{
            background-color: rgba(0, 0, 0, .10);
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

        tab_config, tab_optimisation, tab_run, tab_results, tab_settings = streamlit.tabs([
            "Configuration",
            "Optimisation Technique",
            "Run Optimisation",
            "Dashboard & Results",
            "Settings"
        ])

        with tab_config:
            render_config_tab(ss)

        with tab_optimisation:
            render_optimisation_tab(ss)
            
        with tab_run:
            streamlit.header("Run Optimisation")
            if ss.config_data is None:
                streamlit.warning("Please load a configuration in the 'Configuration' tab first.")
            elif not ss.selected_optimisation_technique_id or not ss.optimisation_technique_loaded:
                streamlit.warning("Please select and apply an optimisation technique in the 'Optimisation Technique' tab first.")
            else:
                selected_technique_name = ss.available_optimisation_techniques.get(ss.selected_optimisation_technique_id, "Unknown")
                streamlit.write(f"Ready to run optimisation using **{selected_technique_name}**.")
                streamlit.write("Using configuration:")
                streamlit.json(ss.config_data)
                streamlit.write("With parameters (example):")
                streamlit.json(ss.optimisation_params if ss.optimisation_params else {"note": "No specific parameters set for this technique yet."})
                # Add button to start optimisation process
                if streamlit.button("Start Optimisation Process", key="start_optimisation_button"):
                    streamlit.write("Optimisation process started... (placeholder)")
                    # Here you would call the actual MRA logic with config_data and optimisation_params

        with tab_results:
            streamlit.header("Dashboard & Results")
            if ss.config_data is None: # Check if configuration data is available.
                streamlit.warning("Please load a configuration and run optimization to see results.")
            else:
                streamlit.write("Route visualizations and results will appear here.")

        with tab_settings:
            streamlit.header("UI Settings")
            streamlit.toggle(
                "Show Streamlit Header",
                value = ss.show_header,
                key = "show_header_toggle_widget",
                on_change = config_logic.handle_show_header_toggle,
                args = (ss,),
                help = "Toggle the visibility of the default Streamlit header bar."
            )

def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    # Initialise session state variables using the function from config_logic
    # Use an alias for streamlit.session_state for brevity
    ss = streamlit.session_state
    config_logic.initialise_session_state(ss)
    optimisation_logic.initialise_session_state(ss) # Initialise optimisation state

    _apply_custom_styling(ss)
    _render_main_layout(ss)

if __name__ == "__main__":
    main()
