package jadeagents; // Changed from dld.jadeagents

import jade.core.Agent;
import jade.core.AID;
// Unused imports ContainerID, Profile, ProfileImpl, Runtime were removed for cleanliness
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;
import jade.wrapper.StaleProxyException;
import jade.lang.acl.ACLMessage;
import py4j.GatewayServer;

public class Py4jGatewayAgent extends Agent {
    private GatewayServer server;
    public static final int PY4J_PORT = 25333; // Default Py4J port

    protected void setup() {
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " setup() method called.");
        // Register this agent as the entry point for Py4J
        System.out.println("Py4jGatewayAgent: Attempting to initialize GatewayServer on port " + PY4J_PORT);
        server = new GatewayServer(this, PY4J_PORT);
        System.out.println("Py4jGatewayAgent: GatewayServer object created. Attempting to start...");
        try {
            server.start();
            System.out.println("Py4J GatewayServer started successfully on port " + PY4J_PORT);
        } catch (Exception e) {
            System.err.println("Py4J GatewayServer failed to start: " + e.getMessage());
            e.printStackTrace();
            doDelete(); // Self-terminate if server fails
        }
    }

    protected void takeDown() {
        if (server != null) {
            server.shutdown();
            System.out.println("Py4J GatewayServer shut down.");
        }
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " terminating.");
    }

    /**
     * Called by Python to create a new agent in JADE.
     * @param agentName The local name of the agent to create.
     * @param agentClass The fully qualified class name of the agent.
     * @param agentArgs An array of string arguments for the new agent.
     * @return A string message indicating success or failure.
     */
    public String createAgentByController(String agentName, String agentClass, String[] agentArgs) {
        System.out.println("Py4jGatewayAgent: Received request to create agent: " + agentName + " of class " + agentClass);
        ContainerController cc = getContainerController();
        if (cc == null) {
            return "Error: Could not get container controller.";
        }
        try {
            Object[] argsForJADE = agentArgs; // JADE expects Object[]
            AgentController ac = cc.createNewAgent(agentName, agentClass, argsForJADE);
            ac.start(); // Start the newly created agent
            return "Agent '" + agentName + "' created and started successfully by Py4jGatewayAgent.";
        } catch (StaleProxyException e) {
            System.err.println("Error creating agent " + agentName + ": StaleProxyException - " + e.getMessage());
            e.printStackTrace();
            return "Error creating agent '" + agentName + "': StaleProxyException - " + e.getMessage();
        } catch (Exception e) {
            System.err.println("Error creating agent " + agentName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error creating agent '" + agentName + "': " + e.getMessage();
        }
    }

    /**
     * Called by Python to dispatch an individual route to a specific agent.
     * @param agentName The local name of the target Delivery Agent.
     * @param routeJsonString A JSON string containing the route details for the agent.
     * @return A string message indicating success or failure.
     */
    public String dispatchIndividualRoute(String agentName, String routeJsonString) {
        System.out.println("Py4jGatewayAgent: Received request to dispatch route to agent: " + agentName);
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.INFORM); // Using INFORM for route assignment
            AID targetAgentAID = new AID(agentName, AID.ISLOCALNAME);
            msg.addReceiver(targetAgentAID);
            msg.setContent(routeJsonString);
            msg.setOntology("VRPAssignment"); // Ontology DAs will listen for
            msg.setLanguage("JSON");

            send(msg);
            System.out.println("Py4jGatewayAgent: Route dispatched to " + agentName + " successfully.");
            return "Route dispatched to agent '" + agentName + "' successfully.";
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error dispatching route to agent " + agentName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error dispatching route to agent '" + agentName + "': " + e.getMessage();
        }
    }

    // The sendOptimisationResultsToMRA method is removed as route dispatch is now per DA.
    // If MRA needs a general "start" signal, a separate method could be added for that.
}
