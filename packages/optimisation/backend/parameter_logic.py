import copy # For deepcopy

# Takes a snapshot of the current optimisation script parameter values.
# This is used to allow cancellation of edits.
# Args:
#   ss (streamlit.SessionState): The current session state.
def take_parameter_snapshot(ss):
    ss.optimisation_script_user_values_snapshot = copy.deepcopy(ss.optimisation_script_user_values)

# Commits the edited optimisation script parameters.
# This involves clearing the snapshot as the current values are now considered saved.
# Args:
#   ss (streamlit.SessionState): The current session state.
# Returns:
#   dict: A result dictionary indicating success.
def commit_parameter_changes(ss):
    ss.optimisation_script_user_values_snapshot = {} 
    return {'type': 'success', 'message': "Parameters updated successfully."}

# Reverts optimisation script parameter values to their state before editing began.
# This uses the snapshot taken when editing was initiated.
# Args:
#   ss (streamlit.SessionState): The current session state.
def revert_parameter_changes(ss):
    ss.optimisation_script_user_values = copy.deepcopy(ss.optimisation_script_user_values_snapshot)
    ss.optimisation_script_user_values_snapshot = {}
