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

    # This string will contain all CSS and the JavaScript for video logic
    styling_and_video_logic_html = f"""
    <style>
      /* Style for the video injected by embed_video() */
      #bgGlobalVideo {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        object-fit: cover; /* Cover the entire viewport */
        z-index: -2;       /* Place it furthest back */
      }}

      /* Style for the overlay (created by JavaScript) */
      #bgGlobalVideoOverlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0.5); /* 50% darkening */
        z-index: -1;       /* Place it on top of video, behind Streamlit app */
      }}

      /* Make Streamlit containers transparent */
      body {{ margin: 0; }} /* Ensure no body margin */
      
      div[data-testid="stApp"],
      div[data-testid="stAppViewContainer"],
      div[data-testid="stAppViewContainer"] section.main,
      header[data-testid="stHeader"] {{ /* Header transparency */
        background: transparent !important;
      }}

      /* Your other existing UI tweaks can be consolidated here */
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
          border-color: #007BFF !important;
      }}
      div[data-baseweb="select"] > div {{
          border: 1px solid #000000 !important;
          border-radius: 0.5rem !important;
      }}
      div[data-baseweb="select"]:focus-within > div {{
          border-color: #007BFF !important;
      }}
      div[data-testid="stTabPanel"],
      div[data-testid="stExpander"] > details {{
          background-color: rgba(0, 0, 0, 0.10); /* Frosted glass */
          backdrop-filter: blur(16px);
          padding: 1rem; 
          border-radius: 0.5rem; 
      }}
      
      /* Ensure Streamlit header visibility is controlled */
      header[data-testid="stHeader"] {{
          {header_style_properties}
      }}
    </style>

    <script>
      function initYoYoVideoPlayback() {{
        const video = document.getElementById('bgGlobalVideo');
        if (!video) {{
          console.error("#bgGlobalVideo not found. Ensure embed_video() has run and uses this ID.");
          return;
        }}
        console.log('YoYo: initYoYoVideoPlayback called. Video element:', video);

        video.removeAttribute('loop');
        video.removeAttribute('controls');

        let direction = 1; // 1 for forward, -1 for reverse
        let internalStateChange = false; // Flag to prevent event re-entry during state changes

        const attemptPlay = () => {{
          if (video.paused) {{
            console.log(`YoYo: Attempting to play. Current time: ${{video.currentTime.toFixed(2)}}, Rate: ${{video.playbackRate}}, Direction: ${{direction}}`);
            video.play().then(() => {{
              console.log(`YoYo: Play promise resolved. Video should be playing. Current time: ${{video.currentTime.toFixed(2)}}`);
            }}).catch(error => {{
              console.warn(`YoYo: Play attempt failed. Current time: ${{video.currentTime.toFixed(2)}}, Rate: ${{video.playbackRate}}. Error:`, error);
            }});
          }} else {{
            console.log(`YoYo: Play attempt skipped (video not paused). Current time: ${{video.currentTime.toFixed(2)}}, Rate: ${{video.playbackRate}}`);
          }}
        }};

        video.addEventListener('loadedmetadata', function() {{
          console.log(`YoYo: Event 'loadedmetadata'. Duration: ${{video.duration.toFixed(2)}}. Setting rate to 1 and playing.`);
          internalStateChange = true;
          video.playbackRate = 1;
          direction = 1;
          attemptPlay();
          setTimeout(() => {{ internalStateChange = false; }}, 50);
        }});
        
        video.addEventListener('ended', function() {{
          if (internalStateChange) return;

          console.log(`YoYo: Event 'ended'. Current time: ${{video.currentTime.toFixed(2)}}, Duration: ${{video.duration.toFixed(2)}}, Direction: ${{direction}}, Rate: ${{video.playbackRate}}`);
          
          if (direction === 1 && video.playbackRate === 1) {{
            internalStateChange = true;
            console.log('YoYo: Video ended (forward). Attempting to switch to reverse.');
            
            direction = -1;
            video.playbackRate = -1;
            
            attemptPlay();
            
            setTimeout(() => {{ internalStateChange = false; }}, 50);
          }} else {{
            console.warn("YoYo: 'ended' event fired but not in expected forward play state. Current state may be unusual.");
          }}
        }});

        video.addEventListener('timeupdate', function() {{
          if (internalStateChange) return;

          if (direction === -1 && video.playbackRate === -1) {{
            if (video.currentTime <= 0.2 && !video.paused) {{
              internalStateChange = true;
              console.log('YoYo: Video reached beginning (reverse). Attempting to switch to forward.');
              
              video.pause();
              direction = 1; 
              video.playbackRate = 1;
              video.currentTime = 0;
              attemptPlay();
              
              setTimeout(() => {{ internalStateChange = false; }}, 50);
            }}
          }}
        }});

        if (!document.getElementById('bgGlobalVideoOverlay')) {{
          const overlay = document.createElement('div');
          overlay.id = 'bgGlobalVideoOverlay';
          document.body.prepend(overlay);
          console.log('YoYo: Video overlay created.');
        }}
        
        if (video.paused && video.readyState >= 1) {{
            console.log(`YoYo: Video initially paused (readyState: ${{video.readyState}}), attempting initial play.`);
            internalStateChange = true;
            video.playbackRate = 1;
            direction = 1;
            attemptPlay();
            setTimeout(() => {{ internalStateChange = false; }}, 50);
        }} else if (video.paused) {{
            console.log('YoYo: Video initially paused, waiting for metadata via event listener.');
        }}
      }}

      // Run the video logic setup after a short delay
      setTimeout(initYoYoVideoPlayback, 300); // Delay to ensure video tag is in DOM
    </script>
    """
    streamlit.markdown(styling_and_video_logic_html, unsafe_allow_html=True)

def embed_video():
    video_link = "https://static.vecteezy.com/system/resources/previews/023/481/750/mp4/4k-damascus-steel-shine-background-free-video.mp4"
    streamlit.markdown(f"""
        <video autoplay muted playsinline loop id="bgGlobalVideo">
            <source src="{video_link}" type="video/mp4">
            Your browser does not support HTML5 video.
        </video>
    """, unsafe_allow_html=True)

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

    embed_video()

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
