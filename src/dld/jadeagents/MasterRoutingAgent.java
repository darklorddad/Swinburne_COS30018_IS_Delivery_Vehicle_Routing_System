package dld.jadeagents;

import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;

public class MasterRoutingAgent extends Agent {

    protected void setup() {
        System.out.println("MasterRoutingAgent " + getAID().getName() + " is ready.");
        
        // Print arguments (expected to be a JSON string with config)
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            for (int i = 0; i < args.length; i++) {
                System.out.println("MRA Argument " + i + ": " + args[i]);
            }
            // You would typically parse this JSON string here (e.g., using Gson or Jackson)
            // For now, just printing it.
            if (args[0] instanceof String) {
                System.out.println("MRA Configuration (JSON): " + args[0]);
            }
        } else {
            System.out.println("MRA: No arguments provided.");
        }

        // Add behaviour to listen for optimisation results
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                // Listen for messages with the "VRPResults" ontology
                MessageTemplate mt = MessageTemplate.MatchOntology("VRPResults");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + myAgent.getLocalName() + ": Received message from " + msg.getSender().getName());
                    System.out.println("MRA: Message content (Optimisation Results JSON): " + msg.getContent());
                    
                    // Here, the MRA would:
                    // 1. Parse the resultsJson.
                    // 2. Determine routes for each DA.
                    // 3. Send individual route messages to DAs.
                    // For now, we just print the received content.

                    // Example: Send a reply (optional)
                    // ACLMessage reply = msg.createReply();
                    // reply.setPerformative(ACLMessage.INFORM);
                    // reply.setContent("MRA received results.");
                    // myAgent.send(reply);

                } else {
                    block(); // Wait for the next message
                }
            }
        });
    }

    protected void takeDown() {
        System.out.println("MasterRoutingAgent " + getAID().getName() + " terminating.");
    }
}
