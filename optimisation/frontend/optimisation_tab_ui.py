import streamlit

from optimisation.backend import optimisation_logic

def render_optimisation_tab(ss):
    # Renders the UI components for the Optimisation Technique Selection Tab.
    streamlit.header("Select Optimisation Technique")

    if not ss.config_data:
        streamlit.warning("Please load a configuration in the 'Configuration' tab first before selecting an optimisation technique.")
        return

    # Prepare options for the selectbox
    # Adding a "None" option to allow deselecting
    technique_options = {"none": "--- Select a Technique ---"}
    technique_options.update(ss.available_optimisation_techniques)

    # Selectbox for choosing an optimisation technique
    streamlit.selectbox(
        "Available Optimisation Techniques:",
        options = list(technique_options.keys()),
        format_func = lambda x: technique_options[x],
        key = "selected_optimisation_technique_id_widget", # Widget key
        # Use current state (ss.selected_optimisation_technique_id) if available, else default to "none"
        index = list(technique_options.keys()).index(ss.selected_optimisation_technique_id if ss.selected_optimisation_technique_id else "none"),
        on_change = optimisation_logic.handle_optimisation_technique_selection,
        args = (ss,)
    )

    if ss.selected_optimisation_technique_id:
        selected_technique_name = ss.available_optimisation_techniques.get(ss.selected_optimisation_technique_id, "Unknown")
        streamlit.info(f"Selected technique: **{selected_technique_name}**")

        # Placeholder for technique-specific parameters
        # streamlit.subheader("Technique Parameters")
        # if ss.selected_optimisation_technique_id == "genetic_algorithm":
        #     ss.optimisation_params["population_size"] = streamlit.number_input("Population Size", min_value=10, value=ss.optimisation_params.get("population_size", 50))
        # Add more parameter inputs as needed based on the selected technique

        col1, col2, _ = streamlit.columns([1, 1, 3]) # Adjust column ratios as needed
        with col1:
            if streamlit.button("Apply Technique", key="apply_technique_button", disabled=ss.optimisation_technique_loaded, use_container_width=True):
                optimisation_logic.apply_selected_technique(ss)
                # Force a rerun to update UI state if necessary, e.g. to disable button
                streamlit.rerun()

        with col2:
            if streamlit.button("Clear Technique", key="clear_technique_button", disabled=not ss.optimisation_technique_loaded and not ss.selected_optimisation_technique_id, use_container_width=True):
                optimisation_logic.clear_selected_technique(ss)
                # Force a rerun to update UI state
                streamlit.rerun()
        
        if ss.optimisation_technique_loaded:
            streamlit.success(f"**{selected_technique_name}** is loaded and ready for the 'Run Optimisation' tab.")
        else:
            streamlit.warning(f"**{selected_technique_name}** is selected. Press 'Apply Technique' to load it.")

    else:
        streamlit.write("No optimisation technique selected or applied.")

    # Display current state for debugging or information (optional)
    # with streamlit.expander("Current Optimisation State (Debug)"):
    #     streamlit.json({
    #         "selected_technique_id": ss.selected_optimisation_technique_id,
    #         "technique_loaded": ss.optimisation_technique_loaded,
    #         "params": ss.optimisation_params
    #     })
