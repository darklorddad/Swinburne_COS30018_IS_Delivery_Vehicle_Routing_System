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
import java.util.ArrayList;
import java.util.List;
import java.util.Collections;

public class DeliveryAgent extends Agent {
    private String agentInitialConfigJsonString;
    private static final long SIMULATION_TIME_SCALE_DIVISOR = 3000L; // 1 simulated minute = 20ms real time

    private String formatTime(long minutesFromMidnight) {
        long hours = minutesFromMidnight / 60;
        long minutes = minutesFromMidnight % 60;
        return String.format("%02d:%02d", hours, minutes);
    }

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
        public PerformDeliveryBehaviour(Agent a, String routeJson) {
            super(a);
            try {
                JSONObject route = new JSONObject(routeJson);
                JSONArray stopIds = route.getJSONArray("route_stop_ids");
                JSONArray stopCoords = route.getJSONArray("route_stop_coordinates");
                JSONArray arrivalTimes = route.getJSONArray("arrival_times");
                JSONArray departureTimes = route.getJSONArray("departure_times");

                List<double[]> coordinates = new ArrayList<>();
                for (int i = 0; i < stopCoords.length(); i++) {
                    JSONArray coord = stopCoords.getJSONArray(i);
                    coordinates.add(new double[]{coord.getDouble(0), coord.getDouble(1)});
                }
                
                // Initial stop (usually Warehouse departure)
                addSubBehaviour(new OneShotBehaviour(myAgent) {
                    public void action() {
                        System.out.println("DA " + myAgent.getLocalName() + ": Starting delivery for route. Stops: " + stopIds.toString());
                        String firstStopId = stopIds.getString(0);
                        long firstStopArrivalMinutes = arrivalTimes.getLong(0);
                        long firstStopDepartureMinutes = departureTimes.getLong(0);
                        System.out.println("DA " + myAgent.getLocalName() + ": Starting at " + firstStopId +
                                           ". Scheduled Arrival: " + formatTime(firstStopArrivalMinutes) +
                                           ", Scheduled Departure: " + formatTime(firstStopDepartureMinutes));
                    }
                });

                // Iterate through each stop in the route to schedule travel TO it, and service AT it
                for (int i = 0; i < stopIds.length(); i++) {
                    final int currentStopIndex = i;
                    final String currentStopId = stopIds.getString(currentStopIndex);

                    // Travel Waker (for all stops except the first one)
                    if (currentStopIndex > 0) {
                        long departureTimeFromPrevious = departureTimes.getLong(currentStopIndex - 1);
                        long arrivalTimeAtCurrent = arrivalTimes.getLong(currentStopIndex);
                        long travelDurationMinutes = arrivalTimeAtCurrent - departureTimeFromPrevious;
                        long travelDurationMs = (travelDurationMinutes * 60L * 1000L) / SIMULATION_TIME_SCALE_DIVISOR;

                        addSubBehaviour(new WakerBehaviour(myAgent, travelDurationMs) {
                            protected void onWake() {
                                System.out.println("DA " + myAgent.getLocalName() + ": Arrived at stop " + (currentStopIndex + 1) + "/" + stopIds.length() +
                                                   ": " + currentStopId + " at (simulated) " + formatTime(arrivalTimes.getLong(currentStopIndex)));
                            }
                        });
                    }

                    // Service/Waiting Waker for current stop
                    long arrivalTimeAtCurrentStop = arrivalTimes.getLong(currentStopIndex);
                    long departureTimeFromCurrentStop = departureTimes.getLong(currentStopIndex);
                    long serviceAndWaitingDurationMinutes = departureTimeFromCurrentStop - arrivalTimeAtCurrentStop;
                    long serviceAndWaitingDurationMs = (serviceAndWaitingDurationMinutes * 60L * 1000L) / SIMULATION_TIME_SCALE_DIVISOR;

                    if (serviceAndWaitingDurationMs > 0) {
                        addSubBehaviour(new WakerBehaviour(myAgent, serviceAndWaitingDurationMs) {
                            protected void onWake() {
                                if (!currentStopId.equalsIgnoreCase("Warehouse")) {
                                    System.out.println("DA " + myAgent.getLocalName() + ": Finished service at " + currentStopId +
                                                       " at (simulated) " + formatTime(departureTimes.getLong(currentStopIndex)));
                                }
                            }
                        });
                    }
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
                        routeConfirmationPayload.put("agent_id", myAgent.getLocalName());
                        JSONObject originalRoute = new JSONObject(routeJson);
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
