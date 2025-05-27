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

    private JSONObject initialConfigData; // Stores warehouse, parcels. Populated by ReceiveWarehouseParcelData
    private Map<AID, JSONObject> deliveryAgentStatusesCache = new HashMap<>(); // Cache for DA statuses
    private String mraName;

    protected void setup() {
        mraName = getAID().getName(); // Useful for logging
        System.out.println("MasterRoutingAgent " + mraName + " is ready.");
        System.out.println("MRA " + mraName + ": setup() started at " + System.currentTimeMillis());
        
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            // If MRA is created with arguments for other purposes, handle them here
            System.out.println("MRA " + mraName + " created with arguments. First arg: " + args[0].toString());
            if (args[0] instanceof String && !((String)args[0]).isEmpty()) {
                System.out.println("MRA " + mraName + " received a non-empty string argument, but will wait for explicit config subset.");
                initialConfigData = null;
                System.out.println("MRA " + mraName + ": setup() - initialConfigData explicitly set to NULL.");
                System.out.println("MRA " + mraName + ": setup() - initialConfigData explicitly set to NULL.");
            }
        } else {
            System.out.println("MRA: No arguments provided for initial setup.");
            // Consider doDelete() or error handling
        }

        // Behaviour to handle data requests from Py4jGatewayAgent
        System.out.println("MRA " + mraName + ": Adding RequestCompiledData behavior at " + System.currentTimeMillis());
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.and(
                    MessageTemplate.MatchPerformative(ACLMessage.REQUEST),
                    MessageTemplate.MatchOntology("RequestCompiledData")
                );
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": TriggerOptimisationCycle BEHAVIOR - Action Started. Checking initialConfigData...");
                    if (initialConfigData == null) {
                        System.err.println("MRA " + mraName + ": TriggerOptimisationCycle - Current initialConfigData is NULL at behavior start!");
                    } else {
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - Current initialConfigData (at behavior start): " + initialConfigData.toString().substring(0, Math.min(initialConfigData.toString().length(), 100)) +"...");
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - initialConfigData.has('warehouse_coordinates_x_y'): " + initialConfigData.has("warehouse_coordinates_x_y"));
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - initialConfigData.has('parcels'): " + initialConfigData.has("parcels"));
                    }
                    System.out.println("MRA " + mraName + ": Received RequestCompiledData from " + msg.getSender().getName() + 
                                     ", ConvID: " + msg.getConversationId());
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM);
                    reply.setOntology("CompiledDataResponse");
                    
                    // Ensure conversation ID is set correctly
                    if (reply.getConversationId() == null && msg.getConversationId() != null) {
                        System.out.println("MRA " + mraName + ": RequestCompiledData - Manually setting ConvID on reply to: " + msg.getConversationId());
                        reply.setConversationId(msg.getConversationId());
                    } else if (reply.getConversationId() != null) {
                        System.out.println("MRA " + mraName + ": RequestCompiledData - Reply ConvID already set by createReply() to: " + reply.getConversationId());
                    } else {
                        System.out.println("MRA " + mraName + ": RequestCompiledData - Msg ConvID is null, reply ConvID is also null.");
                    }

                    JSONObject compiledDataResponse = new JSONObject();
                    JSONArray liveDAStatuses = new JSONArray();

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
                                        deliveryAgentStatusesCache.put(daReply.getSender(), daStatusJson);
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
                    reply.setContent(compiledDataResponse.toString());
                    myAgent.send(reply);
                    System.out.println("MRA: Sent CompiledDataResponse to " + msg.getSender().getName() + " with ConvID " + reply.getConversationId() + ". Performative: " + ACLMessage.getPerformative(reply.getPerformative()) + ". Content: " + compiledDataResponse.toString().substring(0, Math.min(compiledDataResponse.toString().length(),100))+"...");
                } else {
                    block();
                }
            }
        });

        // Behaviour to receive and store warehouse and parcel data
        System.out.println("MRA " + mraName + ": Adding ReceiveWarehouseParcelData behavior at " + System.currentTimeMillis());
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.and(
                    MessageTemplate.MatchPerformative(ACLMessage.INFORM), 
                    MessageTemplate.MatchOntology("ReceiveWarehouseParcelData") 
                );
                ACLMessage msg = myAgent.receive(mt); 
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": ===== Received 'ReceiveWarehouseParcelData' INFORM message from " + msg.getSender().getName() + " =====");
                    String warehouseParcelJson = msg.getContent();
                    System.out.println("MRA " + mraName + ": Warehouse/Parcel Data JSON received: " + warehouseParcelJson.substring(0, Math.min(warehouseParcelJson.length(),100)) + "...");
                    try {
                        System.out.println("MRA " + mraName + ": ReceiveWarehouseParcelData - Before processing, this.initialConfigData is: " + (initialConfigData == null ? "NULL" : initialConfigData.toString().substring(0, Math.min(initialConfigData.toString().length(),100))+"..."));
                        JSONObject receivedData = new JSONObject(warehouseParcelJson);
                        
                        if (initialConfigData == null) { 
                            initialConfigData = new JSONObject();
                            System.out.println("MRA " + mraName + ": ReceiveWarehouseParcelData - Initialized new initialConfigData JSONObject.");
                        }
                        if (receivedData.has("warehouse_coordinates_x_y")) {
                            initialConfigData.put("warehouse_coordinates_x_y", receivedData.getJSONArray("warehouse_coordinates_x_y"));
                            System.out.println("MRA " + mraName + ": Stored warehouse: " + initialConfigData.optJSONArray("warehouse_coordinates_x_y"));
                        }
                        if (receivedData.has("parcels")) {
                             initialConfigData.put("parcels", receivedData.getJSONArray("parcels")); 
                             System.out.println("MRA " + mraName + ": Stored parcels count: " + initialConfigData.optJSONArray("parcels").length());
                        }
                        System.out.println("MRA " + mraName + ": ReceiveWarehouseParcelData - After processing, this.initialConfigData is: " + initialConfigData.toString().substring(0, Math.min(initialConfigData.toString().length(),100))+"...");
                    } catch (Exception e) {
                        System.err.println("MRA " + mraName + ": Error parsing received warehouse/parcel data JSON: " + e.getMessage());
                    }
                } else {
                    block();
                }
            }
        });

        // Behaviour to listen for full optimisation results from Py4jGatewayAgent
        System.out.println("MRA " + mraName + ": Adding FullVRPResults behavior at " + System.currentTimeMillis());
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

        // Behaviour to handle TriggerOptimisationCycle requests
        System.out.println("MRA " + mraName + ": Adding TriggerOptimisationCycle behavior at " + System.currentTimeMillis());
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.and(
                    MessageTemplate.MatchPerformative(ACLMessage.REQUEST),
                    MessageTemplate.MatchOntology("TriggerOptimisationCycle")
                );
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + mraName + ": TriggerOptimisationCycle BEHAVIOR - Action Started. Checking initialConfigData...");
                    if (initialConfigData == null) {
                        System.err.println("MRA " + mraName + ": TriggerOptimisationCycle - Current initialConfigData is NULL at behavior start!");
                    } else {
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - Current initialConfigData (at behavior start): " + initialConfigData.toString().substring(0, Math.min(initialConfigData.toString().length(), 100)) +"...");
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - initialConfigData.has('warehouse_coordinates_x_y'): " + initialConfigData.has("warehouse_coordinates_x_y"));
                        System.out.println("MRA " + mraName + ": TriggerOptimisationCycle - initialConfigData.has('parcels'): " + initialConfigData.has("parcels"));
                    }
                    System.out.println("MRA " + mraName + ": Received TriggerOptimisationCycle from " + msg.getSender().getName() + ", ConvID: " + msg.getConversationId());
                    ACLMessage reply = msg.createReply();
                    reply.setPerformative(ACLMessage.INFORM); // Default to INFORM
                    reply.setOntology("OptimisationDataBundle"); 
                    if (reply.getConversationId() == null && msg.getConversationId() != null) {
                         reply.setConversationId(msg.getConversationId());
                    }

                    JSONObject optimisationBundle = new JSONObject();
                    
                    if (initialConfigData != null && initialConfigData.has("warehouse_coordinates_x_y") && initialConfigData.has("parcels")) {
                        optimisationBundle.put("warehouse_coordinates_x_y", initialConfigData.optJSONArray("warehouse_coordinates_x_y"));
                        optimisationBundle.put("parcels", initialConfigData.optJSONArray("parcels"));
                        
                        // Use the cached DA statuses if available
                        JSONArray daStatusesForBundle = new JSONArray();
                        if (deliveryAgentStatusesCache != null && !deliveryAgentStatusesCache.isEmpty()) {
                            System.out.println("MRA (" + mraName + "): OptimisationCycle - Using cached DA statuses. Count: " + deliveryAgentStatusesCache.size());
                            for (JSONObject status : deliveryAgentStatusesCache.values()) {
                                daStatusesForBundle.put(status);
                            }
                        } else {
                            // Fallback if DA statuses haven't been fetched yet
                            System.err.println("MRA (" + mraName + "): OptimisationCycle - deliveryAgentStatusesCache is empty or null. DA information will be missing in bundle.");
                            reply.setPerformative(ACLMessage.FAILURE);
                            optimisationBundle.put("error_mra", "DA statuses not fetched/available in MRA cache.");
                        }
                        optimisationBundle.put("delivery_agents", daStatusesForBundle);
                    } else {
                        System.err.println("MRA " + mraName + ": initialConfigData (warehouse/parcels) is null or incomplete. Cannot prepare full optimisation bundle.");
                        optimisationBundle.put("error_mra", "MRA initialConfigData (warehouse/parcels) is null or incomplete.");
                        reply.setPerformative(ACLMessage.FAILURE);
                    }
                    reply.setContent(optimisationBundle.toString());
                    myAgent.send(reply);
                    System.out.println("MRA: Sent OptimisationDataBundle to " + msg.getSender().getName() + " with ConvID " + reply.getConversationId() + ". Performative: " + ACLMessage.getPerformative(reply.getPerformative()) + ". Content: " + optimisationBundle.toString().substring(0, Math.min(optimisationBundle.toString().length(), 100)) + "...");
                } else {
                    block();
                }
            }
        });

        // Behaviour to listen for delivery confirmations from DAs
        System.out.println("MRA " + mraName + ": Adding DeliveryConfirmation behavior at " + System.currentTimeMillis());
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
