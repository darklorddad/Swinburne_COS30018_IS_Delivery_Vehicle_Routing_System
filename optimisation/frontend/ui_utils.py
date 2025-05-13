# This file is for UI utility functions specific to the Optimisation tab.
# For now, it is a placeholder. Functions can be added here as needed.
# If common UI utilities are required that are already in configuration.frontend.ui_utils,
# they can be imported into this file and re-exported, or this module can provide
# its own versions tailored for the optimisation section.
import streamlit

# Example of how a utility function might look if needed in the future:
# def display_optimisation_message(result):
#     if not result or not isinstance(result, dict) or not result.get('message') or not result.get('type'):
#         return False
# 
#     message_type = result['type']
#     message = result['message']
#     displayed = False
# 
#     if message_type == 'success':
#         streamlit.success(message)
#         displayed = True
#     elif message_type == 'error':
#         streamlit.error(message)
#         displayed = True
#     # ... etc.
#     return displayed
