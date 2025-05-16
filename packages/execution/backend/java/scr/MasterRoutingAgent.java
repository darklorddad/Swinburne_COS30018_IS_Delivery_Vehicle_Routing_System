import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
// Simple JSON parsing - for robust parsing, consider libraries like Gson or Jackson
import org.json.JSONObject;
import org.json.JSONArray;

public class MasterRoutingAgent extends Agent {

    protected void setup() {
        System.out.println("MasterRoutingAgent " + getAID().getName() + " is ready.");
        
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            if (args[0] instanceof String) {
                System.out.println("MRA Configuration (JSON): " + args[0]);
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
