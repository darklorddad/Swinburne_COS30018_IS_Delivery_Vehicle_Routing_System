import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.CyclicBehaviour; // Added import for CyclicBehaviour
// Unused imports ContainerID, Profile, ProfileImpl, Runtime were removed for cleanliness
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;
import jade.wrapper.StaleProxyException;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
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

        // Add behaviour to listen for relayed status updates from MRA
        addBehaviour(new CyclicBehaviour(this) { // 'this' refers to the Py4jGatewayAgent instance
            public void action() {
                // Correctly import MessageTemplate
                jade.lang.acl.MessageTemplate mt = jade.lang.acl.MessageTemplate.MatchOntology("DeliveryRelay");
                ACLMessage msg = receive(mt); // 'receive' is a method of Agent class, 'myAgent' is not needed here
                if (msg != null) {
                    System.out.println("Py4jGatewayAgent: Received Relayed Delivery Status from " + msg.getSender().getName() + ". Content: " + msg.getContent());
                } else {
                    block(); // block() is a method of Behaviour, so it's correctly called here on the CyclicBehaviour instance
                }
            }
        });
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
     * Called by Python to forward the complete optimisation results to the MasterRoutingAgent.
     * @param mraName The local name of the MasterRoutingAgent.
     * @param fullResultsJson A JSON string containing all optimisation results and routes.
     * @return A string message indicating success or failure of forwarding.
     */
    public String forwardOptimisationResultsToMRA(String mraName, String fullResultsJson) {
        System.out.println("Py4jGatewayAgent: Received request to forward optimisation results to MRA: " + mraName);
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.REQUEST); // MRA will process this request
            AID mraAID = new AID(mraName, AID.ISLOCALNAME);
            msg.addReceiver(mraAID);
            msg.setContent(fullResultsJson);
            msg.setOntology("FullVRPResults"); // MRA listens for this
            msg.setLanguage("JSON");

            send(msg);
            System.out.println("Py4jGatewayAgent: Full optimisation results forwarded to MRA '" + mraName + "' successfully.");
            return "Full optimisation results forwarded to MRA '" + mraName + "' successfully.";
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error forwarding results to MRA " + mraName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error forwarding results to MRA '" + mraName + "': " + e.getMessage();
        }
    }

    /**
     * Called by Python to get compiled optimization data from the MasterRoutingAgent.
     * This method will send a request to the MRA and wait for its response.
     * @param mraName The local name of the MasterRoutingAgent (e.g., "MRA").
     * @return A JSON string containing the compiled data from MRA, 
     * or a JSON string with an error field if something goes wrong.
     */
    public String getCompiledOptimizationDataFromMRA(String mraName) {
        System.out.println("Py4jGatewayAgent: Received request from Python to get compiled data from MRA: " + mraName);
        try {
            ACLMessage requestToMRA = new ACLMessage(ACLMessage.REQUEST);
            requestToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            requestToMRA.setOntology("RequestCompiledData"); // MRA listens for this
            requestToMRA.setLanguage("JSON"); // Though content is empty for this request type
            String conversationId = "get-data-" + System.currentTimeMillis();
            requestToMRA.setConversationId(conversationId);
            requestToMRA.setReplyWith(conversationId + "-reply"); // Helps MRA to set inReplyTo
            
            send(requestToMRA);
            System.out.println("Py4jGatewayAgent: Sent 'RequestCompiledData' to MRA '" + mraName + "'. Waiting for reply...");

            // Wait for the MRA's reply
            // Match based on ontology and conversation ID for robustness
            MessageTemplate mtReply = MessageTemplate.and(
                MessageTemplate.MatchOntology("CompiledDataResponse"), // MRA replies with this ontology
                MessageTemplate.MatchConversationId(conversationId)
            );
            ACLMessage replyFromMRA = blockingReceive(mtReply, 10000); // Wait for 10 seconds (adjust timeout as needed)

            if (replyFromMRA != null) {
                System.out.println("Py4jGatewayAgent: Received compiled data reply from MRA: " + replyFromMRA.getContent());
                return replyFromMRA.getContent(); // This is the JSON string from MRA
            } else {
                System.err.println("Py4jGatewayAgent: No reply from MRA '" + mraName + "' for compiled data request within timeout.");
                return "{\"error\": \"Timeout: MRA did not reply to data request\"}";
            }
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error requesting/receiving compiled data from MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent: " + e.getMessage() + "\"}";
        }
    }
    // dispatchIndividualRoute method is removed. MRA now handles individual dispatch.
}
