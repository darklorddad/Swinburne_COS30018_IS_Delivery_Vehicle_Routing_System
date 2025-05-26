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

    private JSONObject initialConfigData; // Will store parcels, warehouse_coordinates_x_y
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
                } catch (Exception e) {
                    System.err.println("MRA: Error parsing initial configuration JSON: " + e.getMessage());
                }
            }
        } else {
            System.out.println("MRA: No arguments provided for initial setup.");
        }

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
                            String individualRouteJson = routeDetail.toString();

                            ACLMessage routeMsgToDA = new ACLMessage(ACLMessage.INFORM);
                            routeMsgToDA.addReceiver(new AID(daName, AID.ISLOCALNAME));
                            routeMsgToDA.setContent(individualRouteJson);
                            routeMsgToDA.setOntology("VRPAssignment");
                            routeMsgToDA.setLanguage("JSON");
                            myAgent.send(routeMsgToDA);
                            System.out.println("MRA: Dispatched route to DA '" + daName + "'.");
                        }
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

                    ACLMessage relayMsg = new ACLMessage(ACLMessage.INFORM);
                    relayMsg.addReceiver(new AID("py4jgw", AID.ISLOCALNAME));
                    relayMsg.setOntology("DeliveryRelay");
                    relayMsg.setLanguage("STRING");
                    relayMsg.setContent("MRA relayed: DA " + daName + " reported: " + content);
                    myAgent.send(relayMsg);
                    System.out.println("MRA: Relayed DA ("+ daName + ") confirmation to py4jgw.");
                } else {
                    block();
                }
            }
        });

        // Behaviour to listen for DA Status/Capacity Reports
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mtStatus = MessageTemplate.and(
                    MessageTemplate.MatchPerformative(ACLMessage.INFORM),
                    MessageTemplate.MatchOntology("DAStatusReport")
                );
                ACLMessage msg = myAgent.receive(mtStatus);
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": Received DAStatusReport from " + msg.getSender().getName());
                    String statusJson = msg.getContent();
                    try {
                        JSONObject daStatus = new JSONObject(statusJson);
                        deliveryAgentStatuses.put(msg.getSender(), daStatus);
                        System.out.println("MRA: Updated status for DA " + msg.getSender().getLocalName() + ". New status: " + statusJson);
                    } catch (Exception e) {
                        System.err.println("MRA: Error parsing DAStatusReport JSON from " + msg.getSender().getLocalName() + ": " + e.getMessage());
                    }
                } else {
                    block();
                }
            }
        });

        // Behaviour to respond to requests for compiled optimization data from Py4jGatewayAgent
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mtRequest = MessageTemplate.and(
                        MessageTemplate.MatchPerformative(ACLMessage.REQUEST),
                        MessageTemplate.MatchOntology("RequestCompiledData")
                );
                ACLMessage msg = myAgent.receive(mtRequest);
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": Received data request from " + msg.getSender().getName());
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setOntology("CompiledDataResponse");
                    
                    JSONObject compiledData = new JSONObject();
                    if (initialConfigData != null) {
                        compiledData.put("parcels", initialConfigData.optJSONArray("parcels"));
                        compiledData.put("warehouse_coordinates_x_y", initialConfigData.optJSONArray("warehouse_coordinates_x_y"));
                    }
                    JSONArray daStatusesArray = new JSONArray();
                    for (JSONObject status : deliveryAgentStatuses.values()) {
                        daStatusesArray.put(status);
                    }
                    compiledData.put("delivery_agent_statuses", daStatusesArray);
                    reply.setContent(compiledData.toString());
                    myAgent.send(reply);
                    System.out.println("MRA: Sent compiled data to " + msg.getSender().getName() + ". Data: " + compiledData.toString());
                } else {
                    block();
                }
            }
        });
    }
}
