import streamlit
from packages.configuration.backend import config_logic
from packages.configuration.frontend.config_tab_ui import render_config_tab
from packages.optimisation.backend import optimisation_logic
from packages.optimisation.frontend.optimisation_tab_ui import render_optimisation_tab
from packages.execution.backend import execution_logic 
from packages.execution.frontend.execution_tab_ui import render_jade_operations_tab 
from packages.visualisation.frontend.visualisation_tab_ui import render_visualisation_tab # New import

# Video background setup HTML/CSS/JS
VIDEO_BACKGROUND_SETUP_HTML = """
<style>
  /* These styles will be global as they are injected into the main document */
  body {
    margin: 0; /* Reset browser default margin */
  }
  #bgGlobalVideoContainer { /* Renamed for clarity */
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: -2; /* Furthest back, behind Streamlit app */
    overflow: hidden;
  }
  #bgGlobalVideo { /* Renamed for clarity */
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  #bgGlobalVideoOverlay { /* Renamed for clarity */
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: rgba(0, 0, 0, 0.5); /* Darkening overlay */
    z-index: -1; /* Between video and Streamlit app */
  }

  /* Make Streamlit containers transparent so video shows through */
  div[data-testid="stApp"] {
    background: transparent !important;
  }
  div[data-testid="stAppViewContainer"] {
    background: transparent !important;
  }
  div[data-testid="stAppViewContainer"] section.main {
    background: transparent !important;
  }
</style>

<script>
  // Encapsulate in a function to avoid re-declaration if script runs multiple times
  function initGlobalVideoBackground() {
    // Check if already initialized
    if (document.getElementById('bgGlobalVideoContainer')) {
      console.log('Global video background already initialized.');
      return;
    }
    console.log('Initializing global video background...');

    // Create Video Container
    const videoContainer = document.createElement('div');
    videoContainer.id = 'bgGlobalVideoContainer';
    
    // Create Video Element
    const video = document.createElement('video');
    video.id = 'bgGlobalVideo';
    video.autoplay = true;
    video.muted = true;
    video.loop = true;      // Using simple loop for now for debugging
    video.playsInline = true; // For iOS
    video.setAttribute('controls', ''); // Add controls for debugging visibility

    const source = document.createElement('source');
    source.src = "https://static.vecteezy.com/system/resources/previews/027/787/658/mp4/abstract-pattern-animation-background-free-video.mp4";
    source.type = "video/mp4";
    video.appendChild(source);
    video.insertAdjacentText('beforeend', "Your browser does not support the video tag.");

    videoContainer.appendChild(video);
    // Prepend to body to ensure it's "behind" other body elements early
    document.body.prepend(videoContainer);

    // Create Overlay
    const overlay = document.createElement('div');
    overlay.id = 'bgGlobalVideoOverlay';
    // Prepend overlay after video container. CSS z-index will handle layering.
    document.body.prepend(overlay);

    // Simplified Playback Logic for Debugging
    const videoDebug = document.getElementById('bgGlobalVideo');
    if (videoDebug) {
      console.log("Debug: Global video element #bgGlobalVideo created and found.", videoDebug);
      videoDebug.play().then(() => {
        console.log("Debug: videoDebug.play() promise resolved (autoplay likely OK).");
      }).catch(error => {
        console.error("Debug: videoDebug.play() promise rejected (autoplay likely FAILED):", error);
        console.log("Debug: Try manually playing video via controls.");
      });
    } else {
      console.error("Debug: Global video element #bgGlobalVideo NOT found after creation attempt.");
    }
  }

  // Run the setup function after a short delay
  // This gives Streamlit more time to initialize before we modify the DOM.
  setTimeout(initGlobalVideoBackground, 200); // Delay by 200 milliseconds
</script>
"""

# Applies custom CSS to the Streamlit app.
def _apply_custom_styling(ss):
    header_style_properties = "background-color: transparent !important;" 

    if not ss.show_header:
        header_style_properties += " display: none !important; visibility: hidden !important;"

    # Inject the global video setup
    streamlit.markdown(VIDEO_BACKGROUND_SETUP_HTML, unsafe_allow_html=True)

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /* NOTE: .stApp / div[data-testid="stApp"] background styling is now handled 
           by VIDEO_BACKGROUND_SETUP_HTML. */

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
