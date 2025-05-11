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
