package dld.jadeagents;

import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;

public class DeliveryAgent extends Agent {

    protected void setup() {
        System.out.println("DeliveryAgent " + getAID().getName() + " is ready.");

        // Print arguments (expected to be a JSON string with this DA's config)
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            for (int i = 0; i < args.length; i++) {
                System.out.println("DA " + getLocalName() + " Argument " + i + ": " + args[i]);
            }
            // You would typically parse this JSON string here
            if (args[0] instanceof String) {
                System.out.println("DA " + getLocalName() + " Configuration (JSON): " + args[0]);
            }
        } else {
            System.out.println("DA " + getLocalName() + ": No arguments provided.");
        }

        // Add behaviour to listen for its route from MRA (example)
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                // Listen for messages with an ontology like "VRPAssignment"
                MessageTemplate mt = MessageTemplate.MatchOntology("VRPAssignment");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("DA " + myAgent.getLocalName() + ": Received route assignment from " + msg.getSender().getName());
                    System.out.println("DA " + myAgent.getLocalName() + ": Route details: " + msg.getContent());
                    // Here, the DA would parse its route and simulate delivery.
                } else {
                    block();
                }
            }
        });
    }

    protected void takeDown() {
        System.out.println("DeliveryAgent " + getAID().getName() + " terminating.");
    }
}
