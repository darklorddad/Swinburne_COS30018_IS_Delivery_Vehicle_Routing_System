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

                    JSONObject compiledDataResponse = new JSONObject();
                    JSONArray liveDAStatuses = new JSONArray(); // Declare here
                    deliveryAgentStatuses.clear(); // Clear old cache if any

                    try {
                        System.out.println("MRA (" + mraName + "): Searching DF for agents with service 'delivery-service'.");
                        DFAgentDescription template = new DFAgentDescription();
                        ServiceDescription sd = new ServiceDescription();
                        sd.setType("delivery-service");
                        template.addServices(sd);
                        DFAgentDescription[] result = DFService.search(myAgent, template);

                        if (result == null || result.length == 0) {
                            System.out.println("MRA (" + mraName + "): No DAs found via DF offering 'delivery-service'.");
                        } else {
                            System.out.println("MRA (" + mraName + "): Found " + result.length + " DAs via DF that offer 'delivery-service'.");
                            for (DFAgentDescription dfad : result) {
                                AID daAID = dfad.getName();
                                String daName = daAID.getLocalName();

                                ACLMessage queryToDA = new ACLMessage(ACLMessage.REQUEST);
                                queryToDA.addReceiver(daAID);
                                queryToDA.setOntology("QueryDAStatus");
                                String convId_daQuery = "status-query-" + daName + "-" + System.currentTimeMillis();
                                queryToDA.setConversationId(convId_daQuery);
                                queryToDA.setReplyWith(convId_daQuery + "-reply");
                                myAgent.send(queryToDA);
                                System.out.println("MRA (" + mraName + "): Sent QueryDAStatus to DF-discovered DA: " + daName + " (ConvID: " + convId_daQuery + ")");

                                MessageTemplate mtReplyFromDA = MessageTemplate.and(
                                    MessageTemplate.MatchOntology("DAStatusReport"),
                                    MessageTemplate.MatchInReplyTo(queryToDA.getReplyWith())
                                );
                                ACLMessage daReply = myAgent.blockingReceive(mtReplyFromDA, 3000);

                                if (daReply != null) {
                                    try {
                                        JSONObject daStatusJson = new JSONObject(daReply.getContent());
                                        if (!daStatusJson.has("id")) {
                                            daStatusJson.put("id", daName);
                                        }
                                        liveDAStatuses.put(daStatusJson);
                                        deliveryAgentStatuses.put(daReply.getSender(), daStatusJson);
                                        System.out.println("MRA (" + mraName + "): Received status from " + daName + " (ConvID: " + daReply.getConversationId() + "): " + daStatusJson.toString());
                                    } catch (Exception e_parse) {
                                        System.err.println("MRA (" + mraName + "): Error parsing DAStatusReport JSON from " + daName + ": " + e_parse.getMessage());
                                    }
                                } else {
                                    System.err.println("MRA (" + mraName + "): No status reply from DA " + daName + " within timeout for status query (ConvID: " + convId_daQuery + ").");
                                    JSONObject errorStatus = new JSONObject();
                                    errorStatus.put("id", daName);
                                    errorStatus.put("capacity_weight", -1); 
                                    errorStatus.put("operational_status", "unknown_timeout_mra_query");
                                    liveDAStatuses.put(errorStatus);
                                }
                            }
                        }
                        compiledDataResponse.put("delivery_agent_statuses", liveDAStatuses);
                        System.out.println("MRA " + mraName + ": Successfully processed " + liveDAStatuses.length() + " DA statuses. Preparing to send reply.");

                    } catch (FIPAException fe) {
                        System.err.println("MRA (" + mraName + "): FIPAException during DF search for DA statuses: " + fe.getMessage());
                        fe.printStackTrace();
                        reply.setPerformative(ACLMessage.FAILURE);
                        compiledDataResponse.put("error_mra", "MRA FIPAException during DF search: " + fe.getMessage());
                    } catch (Exception e) {
                        System.err.println("MRA " + mraName + ": General Exception while getting/sending DA statuses: " + e.getMessage());
                        e.printStackTrace();
                        reply.setPerformative(ACLMessage.FAILURE); 
                        compiledDataResponse.put("error_mra", "MRA internal error fetching DA statuses: " + e.getMessage());
                    }
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
