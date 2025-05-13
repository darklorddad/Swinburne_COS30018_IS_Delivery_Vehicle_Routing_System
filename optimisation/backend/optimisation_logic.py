
# Available optimisation techniques.
# In a real scenario, these might be discovered dynamically or configured elsewhere.
AVAILABLE_TECHNIQUES = {
    "genetic_algorithm": "Genetic Algorithm",
    "ant_colony": "Ant Colony Optimisation",
    "particle_swarm": "Particle Swarm Optimisation"
}

def initialise_session_state(ss):
    # Initialise optimisation specific variables in the session state.
    if "optimisation_module_initialised" not in ss:
        ss.optimisation_module_initialised = True
        ss.selected_optimisation_technique_id = None
        ss.available_optimisation_techniques = AVAILABLE_TECHNIQUES
        # Placeholder for any parameters specific to the selected technique
        ss.optimisation_params = {} 
        # Placeholder for the state of applying/loading a technique
        ss.optimisation_technique_loaded = False

def handle_optimisation_technique_selection(ss):
    # Logic to handle when a user selects a new optimisation technique.
    # This is called when the selectbox value changes.
    # The actual selected value is already in ss.selected_optimisation_technique_id_widget
    
    # For now, just update the main state variable.
    # More complex logic could go here, like loading default params for the new technique.
    if ss.selected_optimisation_technique_id_widget == "none":
        ss.selected_optimisation_technique_id = None
        ss.optimisation_technique_loaded = False
        ss.optimisation_params = {}
    else:
        ss.selected_optimisation_technique_id = ss.selected_optimisation_technique_id_widget
        # Potentially load default parameters for the selected technique here
        ss.optimisation_params = {} # Reset params for new selection
        ss.optimisation_technique_loaded = False # Require explicit load/apply

def apply_selected_technique(ss):
    # Logic to "load" or "apply" the selected optimisation technique.
    # This could involve setting up specific configurations or validating preconditions.
    if ss.selected_optimisation_technique_id:
        # Perform any actions needed to make the technique active
        ss.optimisation_technique_loaded = True
        # Example: ss.optimisation_params = load_default_params(ss.selected_optimisation_technique_id)
    else:
        # Handle case where no technique is selected but apply is pressed
        ss.optimisation_technique_loaded = False


def clear_selected_technique(ss):
    # Logic to "unload" or "clear" the currently applied optimisation technique.
    ss.selected_optimisation_technique_id = None
    ss.optimisation_params = {}
    ss.optimisation_technique_loaded = False
    # Reset the widget to the "none" option
    ss.selected_optimisation_technique_id_widget = "none"

# Add other backend functions as needed, for example:
# def get_technique_parameters(technique_id):
# def validate_technique_parameters(params):
