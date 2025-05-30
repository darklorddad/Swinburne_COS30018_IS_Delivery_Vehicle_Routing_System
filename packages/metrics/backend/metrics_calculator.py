def calculate_and_store_basic_metrics(ss):
    """Calculates basic performance metrics and stores them in session state."""
    metrics = {}
    config_data = ss.get("config_data")
    optimisation_results = ss.get("optimisation_results")

    if not config_data or not ss.get("optimisation_run_complete") or not optimisation_results:
        ss.performance_metrics = {"error": "Optimisation did not complete or data is missing for metrics calculation."}
        return

    # 1. Input - Total Parcels
    total_parcels = len(config_data.get("parcels", []))
    metrics["total_parcels_configured"] = total_parcels

    # 2. Input - Total Agents
    metrics["total_agents_configured"] = len(config_data.get("delivery_agents", []))

    unassigned_parcels_details = optimisation_results.get("unassigned_parcels_details", [])
    optimised_routes = optimisation_results.get("optimised_routes", [])

    # 3. Optimisation Output - Parcels Assigned
    parcels_assigned = total_parcels - len(unassigned_parcels_details)
    metrics["parcels_assigned_for_delivery"] = parcels_assigned

    # 4. Optimisation Output - Percentage of Parcels Assigned
    metrics["percentage_parcels_assigned"] = round((parcels_assigned / total_parcels) * 100, 2) if total_parcels > 0 else 0.0

    # 5. Optimisation Output - Total Planned Distance
    metrics["total_planned_distance_units"] = round(sum(r.get("total_distance", 0) for r in optimised_routes), 2)

    # 6. Optimisation Output - Average Capacity Utilisation
    utilisations = [(r.get("total_weight", 0) / r.get("capacity_weight", 1)) for r in optimised_routes if r.get("capacity_weight", 0) > 0]
    metrics["average_capacity_utilisation_percentage"] = round((sum(utilisations) / len(utilisations)) * 100, 2) if utilisations else 0.0
        
    # 7. Optimisation Output - Number of Agents Utilised
    metrics["number_of_agents_utilised"] = len(optimised_routes)

    ss.performance_metrics = metrics
