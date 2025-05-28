import streamlit
from packages.configuration.backend import config_logic
from packages.configuration.frontend.config_tab_ui import render_config_tab
from packages.optimisation.backend import optimisation_logic
from packages.optimisation.frontend.optimisation_tab_ui import render_optimisation_tab
from packages.execution.backend import execution_logic 
from packages.execution.frontend.execution_tab_ui import render_jade_operations_tab 
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab # New import
from packages.simple.frontend.simple_mode_tab_ui import render_simple_mode_tab


# Applies custom CSS to the Streamlit app.
def _render_settings_content(ss):
    """Renders the content for the 'Settings' tab."""
    with streamlit.expander("User Interface", expanded=True):
        streamlit.markdown("---")
        streamlit.toggle(
            "Show Streamlit header",
            value = ss.show_header,
            key = "show_header_toggle_widget",
            on_change = config_logic.handle_show_header_toggle,
            args = (ss,),
        )
        # Define the callback for the simple mode toggle
        def simple_toggle_callback():
            ss.simple_mode = not ss.simple_mode
            # Clear all relevant session state to simulate a fresh start

            # 1. Configuration module state reset
            # The `clear_all=True` flag tells `initialise_session_state` in config_logic
            # to reset all its managed keys to their default values.
            config_logic.initialise_session_state(ss, clear_all=True)

            # 2. Optimisation module state reset
            # Delete the initialisation flag for the optimisation module.
            # Then, calling its initialise_session_state will force it to reset all its keys.
            if "optimisation_module_initialised_v2" in ss:
                del ss.optimisation_module_initialised_v2
            optimisation_logic.initialise_session_state(ss)

            # 3. Execution module state reset
            # Similar to the optimisation module.
            if "execution_module_initialised_v1" in ss:
                del ss.execution_module_initialised_v1
            execution_logic.initialise_session_state(ss)
            streamlit.rerun() # Force a full script rerun
        
        streamlit.toggle(
            "Simple Mode",
            value=ss.simple_mode,
            key="simple_mode_toggle_widget",
            on_change=simple_toggle_callback,
            help="Switch to a streamlined user interface with fewer tabs and guided steps."
        )

def _apply_custom_styling(ss):
    header_style_properties = "background-color: transparent !important;" 
    if not ss.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    # This string will contain all CSS for background, overlay, transparency
    styling_and_overlay_html = f"""
    <style>
      /* Style for the video element injected by embed_video() */
      #bgGlobalVideo {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        object-fit: cover; /* Cover the entire viewport */
        z-index: -2;       /* Place it furthest back */
        filter: blur(16px); /* Added blur effect - adjust px as needed */
      }}

      /* Style for the overlay div */
      #bgGlobalVideoOverlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0); /* 50% darkening */
        z-index: -1;       /* On top of video, behind Streamlit app */
      }}

      /* Make Streamlit containers transparent */
      body {{ 
        margin: 0; /* Ensure no body margin */
      }}
      
      div[data-testid="stApp"],
      div[data-testid="stAppViewContainer"],
      div[data-testid="stAppViewContainer"] section.main, /* Targets main content area */
      header[data-testid="stHeader"] {{ /* For header transparency */
        background: transparent !important;
      }}

      /* Your other existing UI tweak CSS rules */
      button[data-testid="stNumberInputStepDown"],
      button[data-testid="stNumberInputStepUp"] {{
          display: none !important;
          visibility: hidden !important;
      }}
      div[data-testid="stTextInputRootElement"] {{
          border-color: #000000 !important;
          border-radius: 0.5rem !important;
      }}
      div[data-testid="stTextInputRootElement"]:focus-within {{
          border-color: #0059BB !important;
      }}
      div[data-baseweb="select"] > div {{
          border: 1px solid #000000 !important;
          border-radius: 0.5rem !important;
      }}
      div[data-baseweb="select"]:focus-within {{
          border-color: #0059BB !important;
      }}
      div[data-testid="stTabPanel"],
      div[data-testid="stExpander"] > details {{
          background-color: rgba(0, 0, 0, 0.10); /* Frosted glass */
          backdrop-filter: blur(64px);
          border-radius: 0.5rem; 
      }}
      
      /* Handles Streamlit header visibility based on ss.show_header */
      header[data-testid="stHeader"] {{
          {header_style_properties}
      }}
    </style>

    <div id="bgGlobalVideoOverlay"></div>
    """
    streamlit.markdown(styling_and_overlay_html, unsafe_allow_html=True)

def embed_video():
    video_link = "https://static.vecteezy.com/system/resources/previews/026/592/030/mp4/minimalist-dark-motion-background-with-a-gently-flowing-green-blue-digital-fractal-light-wave-this-abstract-technology-concept-background-is-full-hd-and-a-seamless-loop-free-video.mp4"
    streamlit.markdown(f"""
        <video autoplay muted loop playsinline id="bgGlobalVideo">
            <source src="{video_link}" type="video/mp4">
            Your browser does not support HTML5 video.
        </video>
    """, unsafe_allow_html=True)

# Renders the tab structure and content for the standard (non-simple) UI mode.
def _render_standard_mode_tabs(ss):
    """Renders the tab structure and content for the standard (non-simple) UI mode."""
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
        if ss.get("jade_platform_running", False):
            streamlit.warning("Configuration cannot be changed while the JADE platform is running")
        else:
            render_config_tab(ss)

    with tab_optimisation:
        if ss.get("jade_platform_running", False):
            streamlit.warning("Optimisation script and parameters cannot be changed while the JADE platform is running")
        else:
            render_optimisation_tab(ss)
        
    with tab_execution: 
        render_jade_operations_tab(ss) 

    with tab_visualisation: # Changed from tab_results
        render_visualisation_tab(ss) # Call the new rendering function

    with tab_settings:
        _render_settings_content(ss)

def main():
    streamlit.set_page_config(layout = "wide", page_title = "Delivery Vehicle Routing System")

    embed_video()

    # Initialise session state variables using the function from config_logic
    # Use an alias for streamlit.session_state for brevity
    ss = streamlit.session_state
    config_logic.initialise_session_state(ss)
    optimisation_logic.initialise_session_state(ss) # Initialise optimisation state
    execution_logic.initialise_session_state(ss) # Initialise execution state

    _apply_custom_styling(ss)

    # Create columns to centre the main content.
    # This is now done in main() so the title is always within this structure.
    col1, col2, col3 = streamlit.columns([2.5, 5, 2.5])

    with col2: # This is the main content area
        streamlit.title("Delivery Vehicle Routing System") # Title is now here

        if ss.get("simple_mode", False):
            # Simple UI Mode: Two tabs - "Simplified Workflow" and "Settings"
            tab_simple_workflow, tab_settings_simple = streamlit.tabs(["Simplified Workflow", "Settings"])
            with tab_simple_workflow:
                render_simple_mode_tab(ss)
            with tab_settings_simple:
                _render_settings_content(ss) # Render only settings content
        else:
            # Standard UI Mode
            _render_standard_mode_tabs(ss) # Render the standard tabs layout

if __name__ == "__main__":
    main()
