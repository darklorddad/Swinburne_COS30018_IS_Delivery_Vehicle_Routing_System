import jade.core.Agent;
import jade.core.AID;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
// Simple JSON parsing - for robust parsing, consider libraries like Gson or Jackson
import java.util.HashMap;
import java.util.Map;
import org.json.JSONObject;
import org.json.JSONArray;

public class MasterRoutingAgent extends Agent {

    private JSONObject initialConfigData; // Will store full config: parcels, warehouse_coordinates_x_y, delivery_agents
    private JSONArray deliveryAgentIdList; // Store just the IDs of DAs MRA is aware of
    private Map<AID, JSONObject> deliveryAgentStatuses = new HashMap<>(); // Stores status from DAs
    private String mraName;

    protected void setup() {
        mraName = getAID().getName(); // Useful for logging
        System.out.println("MasterRoutingAgent " + mraName + " is ready.");
        
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            // If MRA is created with arguments for other purposes, handle them here
            System.out.println("MRA " + mraName + " created with arguments. First arg: " + args[0].toString());
            if (args[0] instanceof String && !((String)args[0]).isEmpty()) {
                System.out.println("MRA " + mraName + " received a non-empty string argument, but will wait for explicit config subset.");
                initialConfigData = null; 
            }
        } else {
            System.out.println("MRA: No arguments provided for initial setup.");
            // Consider doDelete() or error handling
        }

        // Behaviour to handle data requests from Py4jGatewayAgent
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.and(
                    MessageTemplate.MatchPerformative(ACLMessage.REQUEST),
                    MessageTemplate.MatchOntology("RequestCompiledData")
                );
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": Received RequestCompiledData from " + msg.getSender().getName() + 
                                     ", ConvID: " + msg.getConversationId());
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setOntology("CompiledDataResponse");
                    
                    // Ensure conversation ID is set correctly
                    if (reply.getConversationId() == null) {
                        reply.setConversationId(msg.getConversationId());
                    }

                    JSONObject compiledData = new JSONObject();
                    try {
                        System.out.println("MRA " + mraName + ": Querying DA statuses via DF...");
                        JSONArray liveDAStatuses = getCurrentDAStatuses();
                        compiledData.put("delivery_agent_statuses", liveDAStatuses);
                        System.out.println("MRA " + mraName + ": Got " + liveDAStatuses.length() + " DA statuses");
                    } catch (Exception e) {
                        System.err.println("MRA " + mraName + ": Error getting DA statuses: " + e.getMessage());
                        e.printStackTrace();
                        reply.setPerformative(ACLMessage.FAILURE);
                        compiledData.put("error", "MRA failed to get DA statuses: " + e.getMessage());
                    }
                    // The duplicated block that started with:
                    // JSONArray deliveryAgentsFromConfig = initialConfigData.optJSONArray("delivery_agents");
                    // has been removed from here to fix the re-declaration error.
                    // The liveDAStatuses are correctly populated by the preceding block.

                    compiledData.put("delivery_agent_statuses", liveDAStatuses); // Add DA statuses to the response
                    reply.setContent(compiledData.toString());
                    myAgent.send(reply);
                    System.out.println("MRA: Sent delivery agent statuses to " + msg.getSender().getName());
                } else {
                    block();
                }
            }
        });

        // Behaviour to listen for full optimisation results from Py4jGatewayAgent
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.MatchOntology("FullVRPResults");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + myAgent.getLocalName() + ": Received FullVRPResults from " + msg.getSender().getName());
                    String fullResultsJson = msg.getContent();
                    System.out.println("MRA: Full Results JSON: " + fullResultsJson);

                    try {
                        JSONObject resultsObject = new JSONObject(fullResultsJson);
                        JSONArray optimisedRoutes = resultsObject.getJSONArray("optimised_routes");

                        for (int i = 0; i < optimisedRoutes.length(); i++) {
                            JSONObject routeDetail = optimisedRoutes.getJSONObject(i);
                            String daName = routeDetail.getString("agent_id");
                            String individualRouteJson = routeDetail.toString(); // Send the whole route object for this DA

                            ACLMessage routeMsgToDA = new ACLMessage(ACLMessage.INFORM);
                            routeMsgToDA.addReceiver(new AID(daName, AID.ISLOCALNAME));
                            routeMsgToDA.setContent(individualRouteJson);
                            routeMsgToDA.setOntology("VRPAssignment");
                            routeMsgToDA.setLanguage("JSON");
                            myAgent.send(routeMsgToDA);
                            System.out.println("MRA: Dispatched route to DA '" + daName + "'.");
                        }
                        // Optionally, send a confirmation back to Py4jGatewayAgent or log completion
                    } catch (Exception e) {
                        System.err.println("MRA: Error parsing FullVRPResults JSON or dispatching to DAs: " + e.getMessage());
                        e.printStackTrace();
                    }
                } else {
                    block(); 
                }
            }
        });

        // Behaviour to listen for delivery confirmations from DAs
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.MatchOntology("DeliveryConfirmation");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    String daName = msg.getSender().getLocalName();
                    String content = msg.getContent();
                    System.out.println("MRA: Received Delivery Confirmation from " + daName + ". Content: " + content);

                    // Relay this confirmation to Py4jGatewayAgent
                    ACLMessage relayMsg = new ACLMessage(ACLMessage.INFORM);
                    relayMsg.addReceiver(new AID("py4jgw", AID.ISLOCALNAME));
                    relayMsg.setOntology("DeliveryRelay"); // New ontology for PGA
                    relayMsg.setLanguage("STRING"); // Or JSON if more structure is needed
                    relayMsg.setContent("MRA relayed: DA " + daName + " reported: " + content);
                    myAgent.send(relayMsg);
                    System.out.println("MRA: Relayed DA ("+ daName + ") confirmation to py4jgw.");
                } else {
                    block();
                }
            }
        });
    }

    protected void takeDown() {
        System.out.println("MasterRoutingAgent " + getAID().getName() + " terminating.");
    }
}
