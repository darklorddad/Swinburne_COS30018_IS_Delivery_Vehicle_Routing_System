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

    # Video background HTML/CSS/JS
    video_background_html = """
    <style>
      body {
        margin: 0; /* Ensure no default body margin */
      }
      #bgVideoContainer {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw; /* Viewport width */
        height: 100vh; /* Viewport height */
        z-index: -2; /* Furthest back */
        overflow: hidden; /* Hide anything that might spill out */
      }
      #bgVideo {
        width: 100%;
        height: 100%;
        object-fit: cover; /* Cover the entire area, cropping if necessary */
      }
      #bgVideoOverlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0.5); /* 50% darkening overlay */
        z-index: -1; /* Between video and Streamlit content */
      }
      /* Make Streamlit app background transparent to see the video */
      .stApp {
        background: transparent !important;
        position: relative; /* Establish stacking context for content */
        z-index: 0; /* Ensure content is above overlay */
      }
    </style>

    <div id="bgVideoContainer">
      <video id="bgVideo" autoplay muted playsinline>
        <source src="https://static.vecteezy.com/system/resources/previews/027/787/658/mp4/abstract-pattern-animation-background-free-video.mp4" type="video/mp4">
        Your browser does not support the video tag.
      </video>
    </div>
    <div id="bgVideoOverlay"></div>

    <script>
      const video = document.getElementById('bgVideo');
      if (video) {
        let direction = 1; // 1 for forward, -1 for reverse

        // Function to attempt playing the video, handling potential errors
        const attemptPlay = () => {
          video.play().catch(error => {
            console.warn("Video play attempt failed:", error);
            // Autoplay can be restricted by browsers. 
          });
        };

        video.addEventListener('loadedmetadata', function() {
          // Ensure playbackRate is set once metadata is loaded, before first play
          video.playbackRate = 1;
          attemptPlay(); // Start initial playback
        });
        
        video.addEventListener('ended', function() {
          // This event fires when video finishes playing in the FORWARD direction
          if (direction === 1) {
            console.log('Video ended (forward). Switching to reverse.');
            direction = -1;
            video.playbackRate = -1; // Set to play in reverse
            attemptPlay();
          }
        });

        video.addEventListener('timeupdate', function() {
          // When playing in reverse and reaching (or going past) the beginning
          if (direction === -1 && video.playbackRate === -1 && video.currentTime <= 0.1) { // 0.1s threshold
            console.log('Video reached beginning (reverse). Switching to forward.');
            direction = 1;
            video.playbackRate = 1;
            video.currentTime = 0; // Ensure it starts precisely from the beginning
            attemptPlay();
          }
        });

        // Fallback if autoplay is initially prevented
        if (video.paused) {
             attemptPlay();
        }

      } else {
        console.error("Video element #bgVideo not found.");
      }
    </script>
    """
    streamlit.components.v1.html(video_background_html, height=0, width=0)

    custom_css = f"""
    <style>
        /* Style for Streamlit's default header */
        header[data-testid = "stHeader"] {{
            {header_style_properties}
        }}

        /*
        NOTE: .stApp background styling is now handled by the HTML component
              injected above for the video background.
        
        .stApp {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)),
            url(https://www.transparenttextures.com/patterns/otis-redding.png), 
            radial-gradient(at 55% 17%, hsla(43, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 27% 78%, hsla(187, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 94% 10%, hsla(24, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 21% 1%, hsla(332, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 7% 96%, hsla(183, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 95% 32%, hsla(263, 71%, 37%, 1) 0px, transparent 50%), 
            radial-gradient(at 53% 81%, hsla(33, 71%, 37%, 1) 0px, transparent 50%);
        }}
        */

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
