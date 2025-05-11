# This file acts as a facade for configuration logic, importing from specialized modules.

# Import functions from state_management.py
from .state_management import (
    DEFAULT_CONFIG_TEMPLATE,
    initialize_session_state,
    handle_new_config_action,
    confirm_load_configuration,
    clear_config_from_memory,
    enter_edit_mode,
    handle_cancel_edit,
    handle_save_edits,
    handle_save_and_download,
    finalize_download,
    handle_file_uploader_change,
    handle_cancel_load_action,
    handle_load_config_action,
    handle_show_header_toggle,
    validate_edit_mode_preconditions
)

# Import functions from entity_management.py
from .entity_management import (
    add_parcel,
    remove_parcel,
    add_delivery_agent,
    remove_delivery_agent,
    handle_filename_update,
    handle_warehouse_coordinates_update
)

# Import functions from file_operations.py
from .file_operations import (
    load_config_from_uploaded_file,
    config_to_json_string,
    json_string_to_config
)

# Optionally, define __all__ to specify what gets imported with "from .config_logic import *"
# This is good practice for modules designed as facades.
__all__ = [
    # from state_management
    "DEFAULT_CONFIG_TEMPLATE",
    "initialize_session_state",
    "handle_new_config_action",
    "confirm_load_configuration",
    "clear_config_from_memory",
    "enter_edit_mode",
    "handle_cancel_edit",
    "handle_save_edits",
    "handle_save_and_download",
    "finalize_download",
    "handle_file_uploader_change",
    "handle_cancel_load_action",
    "handle_load_config_action",
    "handle_show_header_toggle",
    "validate_edit_mode_preconditions",
    # from entity_management
    "add_parcel",
    "remove_parcel",
    "add_delivery_agent",
    "remove_delivery_agent",
    "handle_filename_update",
    "handle_warehouse_coordinates_update",
    # from file_operations
    "load_config_from_uploaded_file",
    "config_to_json_string",
    "json_string_to_config",
]
