import streamlit
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch  # For nice arrows

# Helper function to get coordinates for a stop ID
def _get_stop_coordinates(stop_id, config_data):
    if stop_id == "Warehouse":
        return config_data.get("warehouse_coordinates_x_y", [0, 0])
    for parcel in config_data.get("parcels", []):
        if parcel.get("id") == stop_id:
            return parcel.get("coordinates_x_y", [None, None])
    return [None, None]  # Should not happen if data is consistent

# Renders the Visualisation tab with arrows
def render_visualisation_tab(ss):
    simulated_jade_routes = ss.get("jade_simulated_routes_data")

    # Check if the routes exist
    if simulated_jade_routes is None:
        streamlit.warning("JADE simulated routes data is not available. Please fetch data from JADE first.")
        if ss.get("jade_simulated_routes_message"):
            streamlit.info(f"Details: {ss.jade_simulated_routes_message}")
        return

    # Check if the routes are in the expected format
    if not isinstance(simulated_jade_routes, list):
        streamlit.error(f"JADE simulated routes data is not in the expected list format. Received type: {type(simulated_jade_routes)}. Please check the JADE output or the fetching logic.")
        if ss.get("jade_simulated_routes_message"):
            streamlit.info(f"Details: {ss.jade_simulated_routes_message}")
        return

    config_data = ss.config_data
    if not config_data:
        streamlit.warning("Configuration data is not available. Cannot render visualisation.")
        return

    if not simulated_jade_routes:  # Handles the case of an empty list
        streamlit.info("No simulated routes were received from JADE, or JADE reported no routes to display.")
        if ss.get("jade_simulated_routes_message"):
            streamlit.info(f"Details: {ss.jade_simulated_routes_message}")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot warehouse
    wh_coords = config_data.get("warehouse_coordinates_x_y", [0, 0])
    ax.plot(wh_coords[0], wh_coords[1], 'ks', markersize=10, label='Warehouse (0, 0)')  # Black square

    # Plot all parcels
    parcel_coords_x = []
    parcel_coords_y = []
    parcel_ids = []
    for parcel in config_data.get("parcels", []):
        coords = parcel.get("coordinates_x_y")
        if coords and len(coords) == 2:
            parcel_coords_x.append(coords[0])
            parcel_coords_y.append(coords[1])
            parcel_ids.append(parcel.get("id"))
            ax.text(coords[0] + 0.1, coords[1] + 0.1, parcel.get("id", ""), fontsize=9)

    ax.plot(parcel_coords_x, parcel_coords_y, 'bo', markersize=5, label='Parcels')  # Blue circles

    # Define a list of distinct colors for routes
    route_colors = list(mcolors.TABLEAU_COLORS.values()) 

    # Plot routes for each agent with arrows
    for i, route_info in enumerate(simulated_jade_routes):
        agent_id = route_info.get("agent_id", f"Agent {i+1}")
        route_stop_ids = route_info.get("route_stop_ids", [])
        
        if not route_stop_ids:
            continue

        route_x = []
        route_y = []
        for stop_id in route_stop_ids:
            coords = _get_stop_coordinates(stop_id, config_data)
            if coords[0] is not None and coords[1] is not None:
                route_x.append(coords[0])
                route_y.append(coords[1])
        
        if len(route_x) > 1:
            color = route_colors[i % len(route_colors)]
            
            # Plot the line
            ax.plot(route_x, route_y, linestyle='-', color=color, 
                   label=f"Route: {agent_id}", linewidth=2)
            
            # Add arrows along the route
            for j in range(len(route_x)-1):
                # Calculate arrow position (middle of the segment)
                x_start, x_end = route_x[j], route_x[j+1]
                y_start, y_end = route_y[j], route_y[j+1]
                
                # Create arrow
                arrow = FancyArrowPatch(
                    (x_start, y_start), (x_end, y_end),
                    arrowstyle='->', color=color,
                    mutation_scale=15, linewidth=2
                )
                ax.add_patch(arrow)

    ax.set_xlabel("X coordinate")
    ax.set_ylabel("Y coordinate")
    ax.set_title("Delivery Routes Visualisation")
    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.)  # Legend outside plot
    ax.grid(True)
    plt.tight_layout(rect=[0, 0, 0.85, 1])  # Adjust layout to make space for legend

    streamlit.pyplot(fig)
    plt.close(fig)