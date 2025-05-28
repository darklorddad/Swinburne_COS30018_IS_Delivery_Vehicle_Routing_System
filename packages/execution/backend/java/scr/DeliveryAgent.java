import jade.core.Agent;
import jade.core.AID;
import jade.domain.DFService;
import jade.domain.FIPAException;
import jade.domain.FIPAAgentManagement.DFAgentDescription;
import jade.domain.FIPAAgentManagement.ServiceDescription;
import jade.core.behaviours.CyclicBehaviour;
import jade.core.behaviours.SequentialBehaviour;
import jade.core.behaviours.OneShotBehaviour;
import jade.core.behaviours.WakerBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import org.json.JSONObject;
import org.json.JSONArray;

public class DeliveryAgent extends Agent {
    private static final long TRAVEL_TIME_PER_STOP_MS = 2000; // Simulate 2 seconds travel/stop time
    private String agentInitialConfigJsonString; // Field to store config

    protected void setup() {
        System.out.println("DeliveryAgent " + getAID().getName() + " is ready and waiting for routes.");
        Object[] args = getArguments();
        if (args != null && args.length > 0 && args[0] instanceof String) {
            this.agentInitialConfigJsonString = (String) args[0]; // Initialize the field
            System.out.println("DA " + getLocalName() + " initialised with Configuration (JSON): " + this.agentInitialConfigJsonString);

            // Register the delivery-service service with the DF
            DFAgentDescription dfd = new DFAgentDescription();
            dfd.setName(getAID());
            ServiceDescription sd = new ServiceDescription();
            sd.setType("delivery-service"); // MRA will search for this type
            sd.setName(getLocalName() + "-delivery-service");
            dfd.addServices(sd);
            try {
                DFService.register(this, dfd);
                System.out.println("DA " + getLocalName() + ": Registered 'delivery-service' with DF.");
            } catch (FIPAException fe) {
                System.err.println("DA " + getLocalName() + ": Error registering with DF: " + fe.getMessage());
                fe.printStackTrace();
            }

            // Behaviour to listen for status queries from MRA
            addBehaviour(new CyclicBehaviour(this) {
                public void action() {
                    MessageTemplate mtQuery = MessageTemplate.and(
                        MessageTemplate.MatchPerformative(ACLMessage.REQUEST),
                        MessageTemplate.MatchOntology("QueryDAStatus")
                    );
                    ACLMessage queryMsg = myAgent.receive(mtQuery);
                    if (queryMsg != null) {
                        System.out.println("DA " + getLocalName() + ": Received status query from " + queryMsg.getSender().getName());
                        ACLMessage reply = queryMsg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setOntology("DAStatusReport"); // Reply with this ontology

                        JSONObject statusPayload = new JSONObject();
                        statusPayload.put("agent_id", getLocalName());
                        // Capacity is from its initial config
                        statusPayload.put("capacity_weight", new JSONObject(agentInitialConfigJsonString).optInt("capacity_weight", 0));
                        statusPayload.put("operational_status", "available"); // Could be dynamic based on current DA state
                        reply.setContent(statusPayload.toString());
                        myAgent.send(reply);
                        System.out.println("DA " + getLocalName() + ": Sent status report to " + queryMsg.getSender().getName());
                    } else {
                        block();
                    }
                }
            });
        }

        // The second identical CyclicBehaviour for QueryDAStatus has been removed.

        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                MessageTemplate mt = MessageTemplate.MatchOntology("VRPAssignment");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("DA " + myAgent.getLocalName() + ": Received route assignment from " + msg.getSender().getName());
                    String routeJson = msg.getContent();
                    System.out.println("DA " + myAgent.getLocalName() + ": Route details (JSON): " + routeJson);
                    
                    // Add a new sequential behaviour to perform the delivery
                    addBehaviour(new PerformDeliveryBehaviour(myAgent, routeJson));
                } else {
                    block();
                }
            }
        });
    }

    private class PerformDeliveryBehaviour extends SequentialBehaviour {
        private String routeJsonString;
        public PerformDeliveryBehaviour(Agent a, String routeJson) {
            super(a);
            this.routeJsonString = routeJson;
            try {
                JSONObject route = new JSONObject(routeJsonString);
                JSONArray stopIds = route.getJSONArray("route_stop_ids"); // e.g., ["Warehouse", "P001", "P002", "Warehouse"]

                addSubBehaviour(new OneShotBehaviour(myAgent) {
                    public void action() {
                        System.out.println("DA " + myAgent.getLocalName() + ": Starting delivery for route. Stops: " + stopIds.toString());
                    }
                });

                for (int i = 0; i < stopIds.length(); i++) {
                    String stopId = stopIds.getString(i);
                    final int stopIndex = i; // For use in inner class

                    // Simulate travel to the stop
                    addSubBehaviour(new WakerBehaviour(myAgent, TRAVEL_TIME_PER_STOP_MS) {
                        protected void onWake() {
                            System.out.println("DA " + myAgent.getLocalName() + ": Arrived at stop " + (stopIndex + 1) + "/" + stopIds.length() + ": " + stopId);
                            if (!stopId.equals("Warehouse")) {
                                System.out.println("DA " + myAgent.getLocalName() + ": Servicing stop " + stopId + ".");
                            } else if (stopIndex > 0 && stopIndex == stopIds.length() -1) { // Last stop is warehouse
                                System.out.println("DA " + myAgent.getLocalName() + ": Returned to Warehouse.");
                            }
                        }
                    });
                }

                addSubBehaviour(new OneShotBehaviour(myAgent) {
                    public void action() {
                        System.out.println("DA " + myAgent.getLocalName() + ": Delivery route complete. Returning to idle state.");
                        
                        // Send confirmation message to MasterRoutingAgent
                        ACLMessage confirmationMsg = new ACLMessage(ACLMessage.INFORM);
                        confirmationMsg.addReceiver(new AID("MRA", AID.ISLOCALNAME)); // Send to MasterRoutingAgent
                        confirmationMsg.setOntology("DeliveryConfirmation");
                        confirmationMsg.setLanguage("JSON");

                        JSONObject routeConfirmationPayload = new JSONObject();
                        routeConfirmationPayload.put("agent_id ", myAgent.getLocalName());
                        JSONObject originalRoute = new JSONObject(routeJsonString);
                        JSONArray originalStopIds = originalRoute.getJSONArray("route_stop_ids");
                        routeConfirmationPayload.put("route_stop_ids", originalStopIds);
                        confirmationMsg.setContent(routeConfirmationPayload.toString());
                        myAgent.send(confirmationMsg);
                        System.out.println("DA " + myAgent.getLocalName() + ": Sent delivery confirmation to MRA.");
                    }
                });

            } catch (Exception e) {
                System.err.println("DA " + myAgent.getLocalName() + ": Error parsing route JSON or creating delivery behaviours: " + e.getMessage());
                e.printStackTrace();
                // Add a simple error state behaviour if parsing fails
                 addSubBehaviour(new OneShotBehaviour(myAgent) {
                    public void action() {
                        System.out.println("DA " + myAgent.getLocalName() + ": Failed to process route. Returning to idle state.");
                    }
                });
            }
        }
    }

    protected void takeDown() {
        System.out.println("DeliveryAgent " + getAID().getName() + " terminating.");
        // Deregister from the DF
        try {
            DFService.deregister(this);
            System.out.println("DA " + getLocalName() + ": Deregistered from DF.");
        } catch (FIPAException fe) {
            System.err.println("DA " + getLocalName() + ": Error deregistering from DF: " + fe.getMessage());
            fe.printStackTrace();
        }
    }
}
