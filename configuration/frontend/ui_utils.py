import streamlit

# Displays a Streamlit success, error, info, or warning message.
# Args:
#   result (dict): A dictionary with 'type' and 'message' keys.
#                  'type' can be 'success', 'error', 'info', 'warning'.
# Returns:
#   bool: True if a message was displayed, False otherwise.
def display_operation_result(result):
    if not result or not isinstance(result, dict) or not result.get('message') or not result.get('type'):
        return False

    message_type = result['type']
    message = result['message']
    displayed = False

    if message_type == 'success':
        streamlit.success(message)
        displayed = True
    elif message_type == 'error':
        streamlit.error(message)
        displayed = True
    elif message_type == 'info':
        streamlit.info(message)
        displayed = True
    elif message_type == 'warning':
        streamlit.warning(message)
        displayed = True
    
    return displayed

# Handles a generic UI action that returns a result dictionary.
# It displays the result message and reruns the Streamlit app
# unless the result was specifically a 'warning' type message.
# Args:
#   action_function (callable): The backend function to call.
#   *args: Arguments to pass to the action_function.
def handle_ui_action_with_conditional_rerun(action_function, *args):
    result = action_function(*args)
    
    message_was_displayed = display_operation_result(result)
    
    # Determine if a rerun is needed.
    # Rerun if no message was displayed (implies an issue or state change not messaged),
    # or if a message was displayed that was NOT a 'warning'.
    should_rerun = True
    if message_was_displayed and result and result.get('type') == 'warning':
        should_rerun = False
        
    if should_rerun:
        streamlit.rerun()
