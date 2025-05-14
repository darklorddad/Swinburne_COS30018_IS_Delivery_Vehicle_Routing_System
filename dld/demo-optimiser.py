# Example optimisation script for testing the DVRS.

def get_params_schema():
    # Defines the parameters that this script accepts.
    # This schema is used by the main application to dynamically generate UI controls.
    return {
        "parameters": [
            {
                "name": "iterations", 
                "type": "integer", 
                "default": 100, 
                "label": "Number of Iterations", 
                "min": 10,
                "max": 1000,
                "step": 10,
                "help": "The number of iterations the algorithm should run"
            },
            {
                "name": "alpha_value", 
                "type": "float", 
                "default": 0.5, 
                "label": "Alpha Value (Learning Rate)",
                "min": 0.01,
                "max": 1.0,
                "step": 0.01,
                "help": "A learning rate parameter for the algorithm"
            },
            {
                "name": "use_heuristic_crossover", 
                "type": "boolean", 
                "default": True, 
                "label": "Use Heuristic Crossover",
                "help": "Enable or disable a specific heuristic crossover method"
            },
            {
                "name": "selection_strategy",
                "type": "selectbox",
                "default": "roulette_wheel",
                "label": "Parent Selection Strategy",
                "options": ["roulette_wheel", "tournament", "rank_based"],
                "help": "Choose the strategy for selecting parents"
            },
            {
                "name": "solver_mode",
                "type": "string", # Example of a string input, rendered as text_input
                "default": "fast",
                "label": "Solver Mode",
                "help": "Enter a mode for the solver (e.g., 'fast', 'balanced', 'quality')"
            }
        ]
    }

def run_optimisation(config_data, params):
    # This is the main function that performs the optimisation.
    # It receives the main configuration data (parcels, agents, warehouse)
    # and the parameters defined in get_params_schema() with user-set values.

    # For demonstration, this function will just return the inputs
    # and a dummy route. In a real scenario, this is where your
    # complex optimisation logic would reside.

    # Example: Accessing a parameter
    iterations = params.get("iterations", 0)
    alpha = params.get("alpha_value", 0.0)
    use_heuristic = params.get("use_heuristic_crossover", False)
    selection = params.get("selection_strategy", "unknown")

    # Example: Accessing config_data
    warehouse_coords = config_data.get("warehouse_coordinates_x_y", [0,0])
    parcels = config_data.get("parcels", [])
    num_parcels = len(parcels)

    # Simulate some processing or route generation
    simulated_route = {
        "agent_id": "DA01",
        "stops": ["Warehouse"] + [p["id"] for p in parcels[:2]] + ["Warehouse"], # Deliver first two parcels
        "total_distance": 123.45,
        "message": f"Processed {num_parcels} parcels with {iterations} iterations, alpha={alpha}, heuristic_crossover={use_heuristic}, selection={selection}."
    }
    
    # The function should return a dictionary (or any JSON-serializable structure)
    # representing the results of the optimisation.
    return {
        "status": "success",
        "message": "Demo optimisation completed.",
        "received_config": config_data,
        "received_params": params,
        "optimised_routes": [simulated_route], # Example structure for routes
        "unassigned_parcels": [p["id"] for p in parcels[2:]] # Example
    }

# Example of how you might test this script standalone (optional)
if __name__ == "__main__":
    # This part is not used by the DVRS application but can be useful for local testing.
    print("--- Parameter Schema ---")
    schema = get_params_schema()
    print(schema)

    print("\n--- Running with Dummy Data ---")
    dummy_config = {
        "warehouse_coordinates_x_y": [0, 0],
        "parcels": [
            {"id": "P001", "coordinates_x_y": [1, 1], "weight": 5},
            {"id": "P002", "coordinates_x_y": [2, 2], "weight": 8},
            {"id": "P003", "coordinates_x_y": [3, 3], "weight": 3},
        ],
        "delivery_agents": [
            {"id": "DA01", "capacity_weight": 20}
        ]
    }
    # Use default parameters from the schema for this standalone test
    dummy_params = {param["name"]: param["default"] for param in schema["parameters"]}
    
    results = run_optimisation(dummy_config, dummy_params)
    import json
    print(json.dumps(results, indent=2))
