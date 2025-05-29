import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.CyclicBehaviour; 
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;
import jade.wrapper.StaleProxyException;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import py4j.GatewayServer;
import java.util.ArrayList;
import java.util.List;
import java.util.Collections;
import org.json.JSONObject; // For parsing/validating
import org.json.JSONArray;  // For constructing the response

public class Py4jGatewayAgent extends Agent {
    private GatewayServer server;
    public static final int PY4J_PORT = 25333; // Default Py4J port
    private List<String> completedRoutesLog = Collections.synchronizedList(new ArrayList<String>());

    protected void setup() {
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " setup() method called.");
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

        addBehaviour(new CyclicBehaviour(this) { 
            public void action() {
                jade.lang.acl.MessageTemplate mt = jade.lang.acl.MessageTemplate.MatchOntology("DeliveryRelay");
                ACLMessage msg = receive(mt); 
                if (msg != null) {
                    String relayedJsonContent = msg.getContent();
                    System.out.println("Py4jGatewayAgent: Received Relayed Delivery Status from " + msg.getSender().getName() + ". Content: " + msg.getContent());
                    try {
                        // Basic validation that it's a JSON object
                        new JSONObject(relayedJsonContent); 
                        completedRoutesLog.add(relayedJsonContent);
                        System.out.println("Py4jGatewayAgent: Added completed route to log. Log size: " + completedRoutesLog.size());
                    } catch (Exception e) {
                        System.err.println("Py4jGatewayAgent: Error processing relayed JSON content: " + e.getMessage() + ". Content: " + relayedJsonContent);
                    }
                } else {
                    block(); 
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

    public String getAndClearJadeSimulatedRoutes() {
        System.out.println("Py4jGatewayAgent: Python requested JADE simulated routes log.");
        JSONArray routesArray = new JSONArray();
        synchronized (completedRoutesLog) {
            if (completedRoutesLog.isEmpty()) {
                System.out.println("Py4jGatewayAgent: Completed routes log is empty.");
                return "[]";
            }
            for (String routeJsonString : completedRoutesLog) {
                try {
                    routesArray.put(new JSONObject(routeJsonString)); // Add each route object to the array
                } catch (Exception e) {
                     System.err.println("Py4jGatewayAgent: Could not parse stored route string to JSON: " + routeJsonString + " Error: " + e.getMessage());
                }
            }
            completedRoutesLog.clear();
            System.out.println("Py4jGatewayAgent: Returned " + routesArray.length() + " simulated routes and cleared log.");
        }
        return routesArray.toString(); // Return as a JSON array string
    }

    public String createAgentByController(String agentName, String agentClass, String[] agentArgs) {
        System.out.println("Py4jGatewayAgent: Received request to create agent: " + agentName + " of class " + agentClass);
        ContainerController cc = getContainerController();
        if (cc == null) {
            return "Error: Could not get container controller.";
        }
        try {
            Object[] argsForJADE = agentArgs; 
            AgentController ac = cc.createNewAgent(agentName, agentClass, argsForJADE);
            ac.start(); 
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

    public String forwardOptimisationResultsToMRA(String mraName, String fullResultsJson) {
        System.out.println("Py4jGatewayAgent: Received request to forward optimisation results to MRA: " + mraName);
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.REQUEST); 
            AID mraAID = new AID(mraName, AID.ISLOCALNAME);
            msg.addReceiver(mraAID);
            msg.setContent(fullResultsJson);
            msg.setOntology("FullVRPResults"); 
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

    public String getCompiledOptimizationDataFromMRA(String mraName) {
        System.out.println("Py4jGatewayAgent: Received request from Python to get DA statuses (via RequestCompiledData) from MRA: " + mraName);
        try {
            ACLMessage requestToMRA = new ACLMessage(ACLMessage.REQUEST);
            requestToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            requestToMRA.setOntology("RequestCompiledData"); 
            requestToMRA.setLanguage("JSON"); 
            String conversationId = "get-data-" + System.currentTimeMillis();
            requestToMRA.setConversationId(conversationId);
            requestToMRA.setReplyWith(conversationId + "-reply"); 
            
            send(requestToMRA);
            System.out.println("Py4jGatewayAgent: Sent 'RequestCompiledData' (for DA statuses) to MRA '" + mraName + "'. Waiting for reply...");

            MessageTemplate mtReply = MessageTemplate.and(
                MessageTemplate.MatchOntology("CompiledDataResponse"), 
                MessageTemplate.MatchConversationId(conversationId)
            );
            ACLMessage replyFromMRA = blockingReceive(mtReply, 10000); 

            if (replyFromMRA != null) {
                System.out.println("Py4jGatewayAgent: Received compiled data reply from MRA: " + replyFromMRA.getContent());
                return replyFromMRA.getContent(); 
            } else {
                System.err.println("Py4jGatewayAgent: No reply from MRA '" + mraName + "' for compiled data request within timeout.");
                return "{\"error\": \"Timeout: MRA ("+mraName+") did not reply to DA status request (RequestCompiledData)\"}";
            }
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error requesting/receiving compiled data from MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent during DA status request: " + e.getMessage() + "\"}";
        }
    }

    public String triggerMRAOptimisationCycleAndGetData(String mraName) {
        System.out.println("Py4jGatewayAgent: Received request from Python to trigger MRA optimisation cycle and get data from MRA: " + mraName);
        try {
            ACLMessage requestToMRA = new ACLMessage(ACLMessage.REQUEST);
            requestToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            requestToMRA.setOntology("TriggerOptimisationCycle"); 
            requestToMRA.setLanguage("JSON"); 
            String conversationId = "trigger-opt-" + System.currentTimeMillis();
            requestToMRA.setConversationId(conversationId);
            requestToMRA.setReplyWith(conversationId + "-reply");
            
            send(requestToMRA);
            System.out.println("Py4jGatewayAgent: Sent 'TriggerOptimisationCycle' to MRA '" + mraName + "'. Waiting for optimisation data reply...");

            MessageTemplate mtReply = MessageTemplate.and(
                MessageTemplate.MatchOntology("OptimisationDataBundle"), 
                MessageTemplate.MatchConversationId(conversationId)
            );
            ACLMessage replyFromMRA = blockingReceive(mtReply, 15000); 

            if (replyFromMRA != null) {
                System.out.println("Py4jGatewayAgent: Received optimisation data bundle from MRA: " + replyFromMRA.getContent().substring(0, Math.min(replyFromMRA.getContent().length(), 200)) + "...");
                return replyFromMRA.getContent();
            } else {
                System.err.println("Py4jGatewayAgent: No reply from MRA '" + mraName + "' for optimisation data bundle within timeout.");
                return "{\"error\": \"Timeout: MRA ("+mraName+") did not reply to TriggerOptimisationCycle request\"}";
            }
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error triggering/receiving optimisation data from MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent during triggerMRAOptimisationCycleAndGetData: " + e.getMessage() + "\"}";
        }
    }

    public String receiveWarehouseParcelDataAndForwardToMRA(String mraName, String warehouseParcelJson) {
        System.out.println("Py4jGatewayAgent: Received warehouse/parcel data from Python for MRA: " + mraName);
        System.out.println("Py4jGatewayAgent: Warehouse/Parcel JSON (first 100 chars): " + warehouseParcelJson.substring(0, Math.min(warehouseParcelJson.length(), 100)) + "...");
        try {
            ACLMessage msgToMRA = new ACLMessage(ACLMessage.INFORM);
            msgToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            msgToMRA.setOntology("ReceiveWarehouseParcelData");
            msgToMRA.setLanguage("JSON");
            msgToMRA.setContent(warehouseParcelJson);
            
            String convId = "send-wh-parcel-data-" + System.currentTimeMillis();
            msgToMRA.setConversationId(convId);
            msgToMRA.setReplyWith(convId + "-reply");

            send(msgToMRA);
            System.out.println("Py4jGatewayAgent: Sent warehouse/parcel data to MRA '" + mraName + "'.");
            
            return "Warehouse/parcel data sent to MRA " + mraName + " successfully by Py4jGatewayAgent.";

        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error sending warehouse/parcel data to MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent while sending warehouse/parcel data to MRA: " + e.getMessage() + "\"}";
        }
    }
}
