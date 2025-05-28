# Facade for configuration logic, importing from specialised modules.

from .state_management import (
    DEFAULT_CONFIG_TEMPLATE,
    initialise_session_state,
    handle_new_config_action,
    confirm_load_configuration,
    clear_config_from_memory,
    enter_edit_mode,
    handle_cancel_edit,
    handle_save_edits,
    # handle_save_and_download and finalize_download are now imported from download_logic
    handle_file_uploader_change,
    handle_cancel_load_action,
    handle_load_config_action,
    handle_edit_config_action,
    reset_simple_config_action,
    handle_show_header_toggle,
    validate_edit_mode_preconditions,
)

from .entity_management import (
    add_parcel,
    remove_parcel,
    add_delivery_agent,
    remove_delivery_agent,
    handle_filename_update,
    handle_warehouse_coordinates_update
)

from .file_operations import (
    load_config_from_uploaded_file,
    config_to_json_string,
    json_string_to_config
)

from .download_logic import (
    handle_save_and_download,
    finalize_download
)

# Defines the public API of this module when using "from .config_logic import *"
__all__ = [
    # Functions from state_management
    "DEFAULT_CONFIG_TEMPLATE",
    "initialise_session_state",
    "handle_new_config_action",
    "confirm_load_configuration",
    "clear_config_from_memory",
    "enter_edit_mode",
    "handle_cancel_edit",
    "handle_save_edits",
    # handle_save_and_download and finalize_download are now imported from download_logic
    "handle_file_uploader_change",
    "handle_cancel_load_action",
    "handle_load_config_action",
    "handle_show_header_toggle",
    "validate_edit_mode_preconditions",
    # Functions from entity_management
    "add_parcel",
    "remove_parcel",
    "add_delivery_agent",
    "remove_delivery_agent",
    "handle_filename_update",
    "handle_warehouse_coordinates_update",
    # Functions from file_operations
    "load_config_from_uploaded_file",
    "config_to_json_string",
    "json_string_to_config",
    # Functions from download_logic
    "handle_save_and_download",
    "finalize_download",
]
