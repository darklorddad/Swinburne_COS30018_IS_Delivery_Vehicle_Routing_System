import jade.core.Agent;
import jade.core.AID; // Added import for AID
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

    protected void setup() {
        System.out.println("DeliveryAgent " + getAID().getName() + " is ready and waiting for routes.");
        Object[] args = getArguments();
        if (args != null && args.length > 0 && args[0] instanceof String) {
            System.out.println("DA " + getLocalName() + " Configuration (JSON): " + args[0]);
        }

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
        public PerformDeliveryBehaviour(Agent a, String routeJson) {
            super(a);
            try {
                JSONObject route = new JSONObject(routeJson);
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
                        confirmationMsg.setContent("DA " + myAgent.getLocalName() + " completed route.");
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
    }
}
