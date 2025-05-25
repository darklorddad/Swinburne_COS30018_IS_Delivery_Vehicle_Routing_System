# Delivery Vehicle Routing System (DVRS)

The Delivery Vehicle Routing System (DVRS) is a Streamlit-based application designed to manage, optimise, execute, and visualise delivery routes using a multi-agent system built with JADE (Java Agent DEvelopment Framework). It allows users to define delivery scenarios, apply custom optimisation algorithms, simulate the delivery process with JADE agents, and view the resulting routes graphically.

## Features

* **Configuration Management:**
    * Create, load, edit, and save delivery configurations (warehouse location, parcels, delivery agents) in JSON format.
    * Intuitive UI for managing entities (parcels, agents) and their properties.
* **Pluggable Optimisation:**
    * Upload custom Python scripts to define optimisation logic.
    * Dynamically extracts and presents script parameters for user configuration.
    * Execute optimisation scripts to generate delivery routes based on the current configuration and parameters.
* **JADE Agent-Based Execution:**
    * Automatically compiles Java-based JADE agents.
    * Manages the JADE platform lifecycle (start/stop).
    * Creates and manages a `MasterRoutingAgent` (MRA) and multiple `DeliveryAgent` (DA) instances based on the configuration.
    * Communicates optimisation results from Python to the MRA in JADE via Py4J.
    * MRA dispatches individual routes to respective DAs.
    * DAs simulate route execution and send completion confirmations.
* **Real-time Logging:**
    * Displays logs from the JADE platform and agent communications within the UI.
* **Route Visualisation:**
    * Presents the optimised routes graphically, showing the warehouse, parcel locations, and agent paths.
* **Customisable UI:**
    * Built with Streamlit, providing an interactive web interface.
    * Includes options to toggle UI elements like the Streamlit header.

## 🛠Core Technologies

* **Python:**
    * **Streamlit:** For the web application user interface.
    * **Py4J:** To integrate Python with the Java-based JADE platform.
* **Java:**
    * **JADE (Java Agent DEvelopment Framework):** For creating the multi-agent system that simulates deliveries.
* **JSON:** For configuration files and data exchange between Python and JADE.
* **Matplotlib:** For generating route visualisations.

## Getting Started

### Prerequisites

* **Python 3.x:** With `pip` for package management.
* **Java Development Kit (JDK):** Required for compiling JADE agents (`javac`) and running the JADE platform (`java`). Ensure `java` and `javac` are in your system's PATH.
* The necessary Python packages can be installed from a `requirements.txt` file (not provided, but typically includes `streamlit`, `py4j`, `matplotlib`).

### Running the Application

1.  **Clone the repository (if applicable).**
2.  **Ensure Dependencies are in Place:**
    * The JADE library (`jade.jar`) is expected at `dependencies/java/JADE-all-4.6.0/jade/lib/jade.jar`.
    * The Py4J Java library (`py4jX.X.X.jar`) is expected at `dependencies/python/py4j-0.10.9.9/py4j-java/py4j0.10.9.9.jar`.
    * The `org.json.jar` library is expected at `dependencies/java/libs/json-20250107.jar`.
    * Custom JADE agent source files (`.java`) are located in `packages/execution/backend/java/scr/`. These are compiled automatically by the application.
3.  **Navigate to the root directory of the project.**
4.  **Run the Streamlit application:**
    ```bash
    streamlit run dvrs.py
    ```
    The application should open in your default web browser.

## How it Works (High-Level Flow)

1.  **Configuration:** The user starts by either creating a new configuration or loading an existing `demo-config.json` (or other custom JSON) file. This defines the warehouse, parcels (with locations and weights), and delivery agents (with capacities).
2.  **Optimisation Script:** The user uploads a Python-based optimisation script (e.g., `demo-optimiser.py`). The script must define:
    * `get_params_schema()`: Returns a schema for configurable parameters.
    * `run_optimisation(config_data, params)`: Takes the current configuration and user-set parameters, and returns the optimised routes.
3.  **Parameter Setup:** The application displays the parameters defined in the script's schema, allowing the user to adjust them.
4.  **Run Optimisation:** The user triggers the optimisation. The Python backend executes the `run_optimisation` function from the uploaded script.
5.  **JADE Platform Startup:**
    * The user navigates to the "Execution" tab.
    * Before starting JADE, the system compiles the Java agent source files (e.g., `MasterRoutingAgent.java`, `DeliveryAgent.java`) located in `packages/execution/backend/java/scr/` into `packages/execution/backend/java/classes/`.
    * The user starts the JADE platform. This launches a new Java process running `jade.Boot` and includes the `Py4jGatewayAgent`.
    * The `Py4jGatewayAgent` starts a Py4J GatewayServer, allowing Python to call its methods.
6.  **Agent Creation:**
    * The user clicks "Create Agents".
    * The Python backend, via the Py4J gateway, instructs `Py4jGatewayAgent` to create:
        * One `MasterRoutingAgent` (MRA).
        * Multiple `DeliveryAgent` (DA) instances, one for each agent defined in the configuration.
    * Agent configurations (like DA capacity or MRA's overall view) are passed as JSON strings during creation.
7.  **Dispatching Routes:**
    * The user clicks "Send to MRA".
    * The Python backend sends the complete set of optimised routes (as a JSON string) to the `Py4jGatewayAgent` via Py4J.
    * `Py4jGatewayAgent` forwards this JSON to the `MasterRoutingAgent` using a JADE ACL message with the "FullVRPResults" ontology.
    * The MRA parses the results and sends individual route assignments (as JSON strings) to the respective `DeliveryAgent`s using JADE ACL messages with the "VRPAssignment" ontology.
8.  **Route Simulation:**
    * Each `DeliveryAgent` receives its route and simulates the delivery process (e.g., visiting stops, respecting travel times).
    * Upon completing its route, each DA sends a confirmation message back to the MRA ("DeliveryConfirmation" ontology).
9.  **Feedback and Logging:**
    * The MRA receives confirmations from DAs and can relay this information (e.g., to `Py4jGatewayAgent` using a "DeliveryRelay" ontology) for logging or display in the Streamlit UI.
    * JADE STDOUT and STDERR are captured and displayed in the application, providing insights into agent activities.
10. **Visualisation:**
    * The "Visualisation" tab uses the `optimisation_results` (stored in session state after step 4) and the `config_data` to plot the warehouse, parcel locations, and the calculated routes for each agent on a 2D plane using Matplotlib.

## Key Components

* **`dvrs.py`:** The main entry point for the Streamlit application. Orchestrates UI tabs and initializes session state.
* **Configuration Package (`packages/configuration/`)**
    * `config_logic.py`: Backend logic for loading, saving, editing, and managing configuration state.
    * `file_operations.py`: Handles JSON file reading/writing.
    * `edit_view_ui.py`, `load_view_ui.py`, etc.: Frontend UI components for configuration.
* **Optimisation Package (`packages/optimisation/`)**
    * `optimisation_logic.py`: Backend logic for handling script uploads, parameter editing, and script execution.
    * `script_lifecycle.py`: Manages loading, schema extraction, and running of user-uploaded optimisation scripts.
    * `script_utils.py`: Utilities for dynamic Python module loading from strings.
    * Frontend UI files for script loading and parameter editing.
* **Execution Package (`packages/execution/`)**
    * `execution_logic.py`: Backend logic for managing the JADE lifecycle and agent interactions.
    * `jade_controller.py`: Facade for interacting with JADE processes and Py4J.
    * `jade_process_manager.py`: Handles starting and stopping the JADE Java process.
    * `java_compiler.py`: Compiles the JADE agent Java source files.
    * `py4j_gateway.py`: Python-side functions to communicate with the JADE `Py4jGatewayAgent`.
    * `java/scr/Py4jGatewayAgent.java`: JADE agent that hosts the Py4J server, enabling Python-Java communication.
    * `java/scr/MasterRoutingAgent.java`: JADE agent responsible for receiving full route plans and dispatching them to Delivery Agents.
    * `java/scr/DeliveryAgent.java`: JADE agent that simulates the execution of a delivery route.
    * `execution_tab_ui.py`: Frontend UI for JADE operations.
* **Visualisation Package (`packages/visualisation/`)**
    * `visualisation_tab_ui.py`: Renders the Matplotlib plot of delivery routes.
* **Demo Files (`pnp/`)**
    * `demo-config.json`: An example JSON configuration file defining a warehouse, parcels, and delivery agents.
    * `demo-optimiser.py`: An example Python optimisation script implementing a greedy nearest-neighbour algorithm.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

GPLv3

```
