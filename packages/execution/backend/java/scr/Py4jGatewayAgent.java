import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.CyclicBehaviour; 
import jade.wrapper.AgentController;
import jade.wrapper.ContainerController;
import jade.wrapper.StaleProxyException;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import py4j.GatewayServer;

public class Py4jGatewayAgent extends Agent {
    private GatewayServer server;
    public static final int PY4J_PORT = 25333; // Default Py4J port

    protected void setup() {
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " setup() method called.");
        System.out.println("Py4jGatewayAgent: Attempting to initialize GatewayServer on port " + PY4J_PORT);
        server = new GatewayServer(this, PY4J_PORT);
        System.out.println("Py4jGatewayAgent: GatewayServer object created. Attempting to start...");
        try {
            server.start();
            System.out.println("Py4J GatewayServer started successfully on port " + PY4J_PORT);
        } catch (Exception e) {
            System.err.println("Py4J GatewayServer failed to start: " + e.getMessage());
            e.printStackTrace();
            doDelete(); // Self-terminate if server fails
        }

        addBehaviour(new CyclicBehaviour(this) { 
            public void action() {
                jade.lang.acl.MessageTemplate mt = jade.lang.acl.MessageTemplate.MatchOntology("DeliveryRelay");
                ACLMessage msg = receive(mt); 
                if (msg != null) {
                    System.out.println("Py4jGatewayAgent: Received Relayed Delivery Status from " + msg.getSender().getName() + ". Content: " + msg.getContent());
                } else {
                    block(); 
                }
            }
        });
    }

    protected void takeDown() {
        if (server != null) {
            server.shutdown();
            System.out.println("Py4J GatewayServer shut down.");
        }
        System.out.println("Py4jGatewayAgent " + getAID().getName() + " terminating.");
    }

    public String createAgentByController(String agentName, String agentClass, String[] agentArgs) {
        System.out.println("Py4jGatewayAgent: Received request to create agent: " + agentName + " of class " + agentClass);
        ContainerController cc = getContainerController();
        if (cc == null) {
            return "Error: Could not get container controller.";
        }
        try {
            Object[] argsForJADE = agentArgs; 
            AgentController ac = cc.createNewAgent(agentName, agentClass, argsForJADE);
            ac.start(); 
            return "Agent '" + agentName + "' created and started successfully by Py4jGatewayAgent.";
        } catch (StaleProxyException e) {
            System.err.println("Error creating agent " + agentName + ": StaleProxyException - " + e.getMessage());
            e.printStackTrace();
            return "Error creating agent '" + agentName + "': StaleProxyException - " + e.getMessage();
        } catch (Exception e) {
            System.err.println("Error creating agent " + agentName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error creating agent '" + agentName + "': " + e.getMessage();
        }
    }

    public String forwardOptimisationResultsToMRA(String mraName, String fullResultsJson) {
        System.out.println("Py4jGatewayAgent: Received request to forward optimisation results to MRA: " + mraName);
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.REQUEST); 
            AID mraAID = new AID(mraName, AID.ISLOCALNAME);
            msg.addReceiver(mraAID);
            msg.setContent(fullResultsJson);
            msg.setOntology("FullVRPResults"); 
            msg.setLanguage("JSON");

            send(msg);
            System.out.println("Py4jGatewayAgent: Full optimisation results forwarded to MRA '" + mraName + "' successfully.");
            return "Full optimisation results forwarded to MRA '" + mraName + "' successfully.";
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error forwarding results to MRA " + mraName + ": " + e.getMessage());
            e.printStackTrace();
            return "Error forwarding results to MRA '" + mraName + "': " + e.getMessage();
        }
    }

    public String getCompiledOptimizationDataFromMRA(String mraName) {
        System.out.println("Py4jGatewayAgent: Received request from Python to get DA statuses (via RequestCompiledData) from MRA: " + mraName);
        try {
            ACLMessage requestToMRA = new ACLMessage(ACLMessage.REQUEST);
            requestToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            requestToMRA.setOntology("RequestCompiledData"); 
            requestToMRA.setLanguage("JSON"); 
            String conversationId = "get-data-" + System.currentTimeMillis();
            requestToMRA.setConversationId(conversationId);
            requestToMRA.setReplyWith(conversationId + "-reply"); 
            
            send(requestToMRA);
            System.out.println("Py4jGatewayAgent: Sent 'RequestCompiledData' (for DA statuses) to MRA '" + mraName + "'. Waiting for reply...");

            MessageTemplate mtReply = MessageTemplate.and(
                MessageTemplate.MatchOntology("CompiledDataResponse"), 
                MessageTemplate.MatchConversationId(conversationId)
            );
            ACLMessage replyFromMRA = blockingReceive(mtReply, 10000); 

            if (replyFromMRA != null) {
                System.out.println("Py4jGatewayAgent: Received compiled data reply from MRA: " + replyFromMRA.getContent());
                return replyFromMRA.getContent(); 
            } else {
                System.err.println("Py4jGatewayAgent: No reply from MRA '" + mraName + "' for compiled data request within timeout.");
                return "{\"error\": \"Timeout: MRA ("+mraName+") did not reply to DA status request (RequestCompiledData)\"}";
            }
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error requesting/receiving compiled data from MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent during DA status request: " + e.getMessage() + "\"}";
        }
    }

    public String triggerMRAOptimisationCycleAndGetData(String mraName) {
        System.out.println("Py4jGatewayAgent: Received request from Python to trigger MRA optimisation cycle and get data from MRA: " + mraName);
        try {
            ACLMessage requestToMRA = new ACLMessage(ACLMessage.REQUEST);
            requestToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            requestToMRA.setOntology("TriggerOptimisationCycle"); 
            requestToMRA.setLanguage("JSON"); 
            String conversationId = "trigger-opt-" + System.currentTimeMillis();
            requestToMRA.setConversationId(conversationId);
            requestToMRA.setReplyWith(conversationId + "-reply");
            
            send(requestToMRA);
            System.out.println("Py4jGatewayAgent: Sent 'TriggerOptimisationCycle' to MRA '" + mraName + "'. Waiting for optimisation data reply...");

            MessageTemplate mtReply = MessageTemplate.and(
                MessageTemplate.MatchOntology("OptimisationDataBundle"), 
                MessageTemplate.MatchConversationId(conversationId)
            );
            ACLMessage replyFromMRA = blockingReceive(mtReply, 15000); 

            if (replyFromMRA != null) {
                System.out.println("Py4jGatewayAgent: Received optimisation data bundle from MRA: " + replyFromMRA.getContent().substring(0, Math.min(replyFromMRA.getContent().length(), 200)) + "...");
                return replyFromMRA.getContent();
            } else {
                System.err.println("Py4jGatewayAgent: No reply from MRA '" + mraName + "' for optimisation data bundle within timeout.");
                return "{\"error\": \"Timeout: MRA ("+mraName+") did not reply to TriggerOptimisationCycle request\"}";
            }
        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error triggering/receiving optimisation data from MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent during triggerMRAOptimisationCycleAndGetData: " + e.getMessage() + "\"}";
        }
    }

    public String receiveConfigSubsetAndForwardToMRA(String mraName, String configSubsetJson) {
        System.out.println("Py4jGatewayAgent: Received config subset from Python for MRA: " + mraName);
        System.out.println("Py4jGatewayAgent: Config subset JSON: " + configSubsetJson);
        try {
            ACLMessage msgToMRA = new ACLMessage(ACLMessage.INFORM);
            msgToMRA.addReceiver(new AID(mraName, AID.ISLOCALNAME));
            msgToMRA.setOntology("ReceiveConfigSubset");
            msgToMRA.setLanguage("JSON");
            msgToMRA.setContent(configSubsetJson);
            
            String convId = "send-config-subset-" + System.currentTimeMillis();
            msgToMRA.setConversationId(convId);
            msgToMRA.setReplyWith(convId + "-reply");

            send(msgToMRA);
            System.out.println("Py4jGatewayAgent: Sent config subset to MRA '" + mraName + "'.");
            
            return "Config subset sent to MRA " + mraName + " successfully by Py4jGatewayAgent.";

        } catch (Exception e) {
            System.err.println("Py4jGatewayAgent: Error sending config subset to MRA '" + mraName + "': " + e.getMessage());
            e.printStackTrace();
            return "{\"error\": \"Exception in Py4jGatewayAgent while sending config subset to MRA: " + e.getMessage() + "\"}";
        }
    }
}
