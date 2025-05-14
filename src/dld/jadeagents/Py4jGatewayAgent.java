package dld.jadeagents;

import jade.core.Agent;
import jade.core.AID;
import jade.core.ContainerID;
import jade.core.Profile;
import jade.core.ProfileImpl;
import jade.core.Runtime;
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;
import jade.wrapper.StaleProxyException;
import jade.lang.acl.ACLMessage;
import py4j.GatewayServer;

public class Py4jGatewayAgent extends Agent {
    private GatewayServer server;
    public static final int PY4J_PORT = 25333; // Default Py4J port

    protected void setup() {
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " is ready.");
        // Register this agent as the entry point for Py4J
        server = new GatewayServer(this, PY4J_PORT);
        try {
            server.start();
            System.out.println("Py4J GatewayServer started on port " + PY4J_PORT);
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
     * Called by Python to send optimisation results to the MasterRoutingAgent.
     * @param mraName The local name of the MasterRoutingAgent.
     * @param resultsJson A JSON string containing the optimisation results.
     * @return A string message indicating success or failure.
     */
    public String sendOptimisationResultsToMRA(String mraName, String resultsJson) {
        System.out.println("Py4jGatewayAgent: Received request to send optimisation results to MRA: " + mraName);
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.REQUEST); // Or INFORM, depending on your protocol
            AID mraAID = new AID(mraName, AID.ISLOCALNAME);
            msg.addReceiver(mraAID);
            msg.setContent(resultsJson);
            msg.setOntology("VRPResults"); // Example ontology
            msg.setLanguage("JSON"); // Example language

            send(msg);
            return "Optimisation results sent to MRA '" + mraName + "' successfully.";
        } catch (Exception e) {
            System.err.println("Error sending results to MRA " + mraName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error sending results to MRA '" + mraName + "': " + e.getMessage();
        }
    }
}
