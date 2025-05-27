import jade.core.Agent;
import jade.core.AID;
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
    private Map<AID, JSONObject> deliveryAgentStatuses = new HashMap<>(); // Stores status from DAs
    private String mraName;

    protected void setup() {
        mraName = getAID().getName(); // Useful for logging
        System.out.println("MasterRoutingAgent " + mraName + " is ready.");
        
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            if (args[0] instanceof String) {
                String configJsonString = (String) args[0];
                System.out.println("MRA Configuration (JSON): " + configJsonString);
                try {
                    initialConfigData = new JSONObject(configJsonString);
                    // You can optionally parse and log parts of the config here, e.g.:
                    // JSONArray parcels = initialConfigData.optJSONArray("parcels");
                    // if (parcels != null) System.out.println("MRA: Parsed " + parcels.length() + " parcels.");
                } catch (Exception e) {
                    System.err.println("MRA: Error parsing initial configuration JSON: " + e.getMessage());
                    // Consider doDelete() or other error handling if config is crucial
                }
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
                    System.out.println("MRA " + mraName + ": Received data request from " + msg.getSender().getName());
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setOntology("CompiledDataResponse"); // Py4jGatewayAgent expects this ontology for the reply

                    JSONObject compiledData = new JSONObject();

                    // Actively query DAs for their current status
                    JSONArray liveDAStatuses = new JSONArray();
                    deliveryAgentStatuses.clear(); // Clear old statuses before querying

                    JSONArray deliveryAgentsFromConfig = initialConfigData.optJSONArray("delivery_agents");
                    if (deliveryAgentsFromConfig != null) {
                        System.out.println("MRA: Querying " + deliveryAgentsFromConfig.length() + " DAs for status...");
                        for (int i = 0; i < deliveryAgentsFromConfig.length(); i++) {
                            JSONObject daConfig = deliveryAgentsFromConfig.getJSONObject(i);
                            String daName = daConfig.getString("id");
                            AID daAID = new AID(daName, AID.ISLOCALNAME);

                            ACLMessage queryToDA = new ACLMessage(ACLMessage.REQUEST);
                            queryToDA.addReceiver(daAID);
                            queryToDA.setOntology("QueryDAStatus");
                            String convId = "status-query-" + daName + "-" + System.currentTimeMillis();
                            queryToDA.setConversationId(convId);
                            queryToDA.setReplyWith(convId + "-reply");
                            myAgent.send(queryToDA);
                            System.out.println("MRA: Sent QueryDAStatus to " + daName);

                            MessageTemplate mtReplyFromDA = MessageTemplate.and(
                                MessageTemplate.MatchOntology("DAStatusReport"),
                                MessageTemplate.MatchInReplyTo(queryToDA.getReplyWith())
                            );
                            ACLMessage daReply = myAgent.blockingReceive(mtReplyFromDA, 3000);

                            if (daReply != null) {
                                try {
                                    JSONObject daStatusJson = new JSONObject(daReply.getContent());
                                    liveDAStatuses.put(daStatusJson);
                                    deliveryAgentStatuses.put(daReply.getSender(), daStatusJson);
                                    System.out.println("MRA: Received status from " + daName + ": " + daStatusJson.toString());
                                } catch (Exception e_parse) {
                                    System.err.println("MRA: Error parsing DAStatusReport JSON from " + daName + ": " + e_parse.getMessage());
                                }
                            } else {
                                System.err.println("MRA: No status reply from DA " + daName + " within timeout.");
                            }
                        }
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
