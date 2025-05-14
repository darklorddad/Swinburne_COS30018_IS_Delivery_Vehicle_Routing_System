package jadeagents; // Changed from dld.jadeagents

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

        // The MRA no longer directly receives the full VRPResults via this mechanism.
        // Route dispatch is handled by Py4jGatewayAgent based on Python's instructions.
        // This behaviour can be removed or adapted if MRA has other message-based interactions.
        /*
        addBehaviour(new CyclicBehaviour(this) {
            public void action() {
                // Listen for messages with the "VRPResults" ontology
                MessageTemplate mt = MessageTemplate.MatchOntology("VRPResults");
                ACLMessage msg = myAgent.receive(mt);
                if (msg != null) {
                    System.out.println("MRA " + myAgent.getLocalName() + ": Received message from " + msg.getSender().getName());
                    System.out.println("MRA: Message content (Optimisation Results JSON): " + msg.getContent());
                    
                    // Original MRA logic for parsing and dispatching would have gone here.
                    // For now, this is handled by Python calling dispatchIndividualRoute on Py4jGatewayAgent.

                } else {
                    block(); // Wait for the next message
                }
            }
        });
        */
        System.out.println("MRA " + getAID().getName() + " is set up. It will not actively dispatch routes in this flow.");
    }

    protected void takeDown() {
        System.out.println("MasterRoutingAgent " + getAID().getName() + " terminating.");
    }
}
