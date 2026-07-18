"""Maps write commands to service methods. The host runs the real service
method (already tested) in one local transaction. Reads are NOT here — they
run client-side against the replica."""

# command name "<service_attr>.<method>" -> (service_attr, method)
WRITE_COMMANDS = {
    "report_service.create_report": ("report_service", "create_report"),
    "report_service.update_report": ("report_service", "update_report"),
    "report_service.delete_report": ("report_service", "delete_report"),
    "report_service.restore_report": ("report_service", "restore_report"),
    "report_service.hard_delete_report": ("report_service", "hard_delete_report"),
    "report_service.acquire_edit_lock": ("report_service", "acquire_edit_lock"),
    "report_service.release_edit_lock": ("report_service", "release_edit_lock"),
    "approval_service.request_approval": ("approval_service", "request_approval"),
    "approval_service.approve_report": ("approval_service", "approve_report"),
    "approval_service.reject_report": ("approval_service", "reject_report"),
    "approval_service.create_notification": ("approval_service", "create_notification"),
    "approval_service.mark_notification_read": ("approval_service", "mark_notification_read"),
    "version_service.create_version_snapshot": ("version_service", "create_version_snapshot"),
    "version_service.restore_version": ("version_service", "restore_version"),
    "version_service.soft_delete_version": ("version_service", "soft_delete_version"),
    "version_service.hard_delete_version": ("version_service", "hard_delete_version"),
    "version_service.restore_deleted_version": ("version_service", "restore_deleted_version"),
    "report_number_service.reserve_block": ("report_number_service", "reserve_block"),
    "report_number_service.transfer_numbers": ("report_number_service", "transfer_numbers"),
    "dropdown_service.add_dropdown_value": ("dropdown_service", "add_dropdown_value"),
    "dropdown_service.update_dropdown_value": ("dropdown_service", "update_dropdown_value"),
    "dropdown_service.delete_dropdown_value": ("dropdown_service", "delete_dropdown_value"),
    "dropdown_service.reorder_dropdown_values": ("dropdown_service", "reorder_dropdown_values"),
    "dropdown_service.restore_dropdown_value": ("dropdown_service", "restore_dropdown_value"),
    "dropdown_service.bulk_import_dropdown_values": ("dropdown_service", "bulk_import_dropdown_values"),
    "validation_service.update_validation_rules": ("validation_service", "update_validation_rules"),
    "validation_service.update_required_status": ("validation_service", "update_required_status"),
    "auth_service.create_user": ("auth_service", "create_user"),
    "auth_service.create_pending_user": ("auth_service", "create_pending_user"),
    "auth_service.reset_onboarding": ("auth_service", "reset_onboarding"),
    "auth_service.update_user": ("auth_service", "update_user"),
    "auth_service.delete_user": ("auth_service", "delete_user"),
    "auth_service.reset_password": ("auth_service", "reset_password"),
    "auth_service.change_password": ("auth_service", "change_password"),
    "auth_service.unlock_account": ("auth_service", "unlock_account"),
    "auth_service.set_user_language": ("auth_service", "set_user_language"),
    "settings_service.save_settings": ("settings_service", "save_settings"),
    "settings_service.save_setting": ("settings_service", "save_setting"),
    # These three write via self.save_setting(s)/DELETE. Self-delegation runs on
    # the real local service, never the proxy, so they must route in their own
    # right or a client silently writes to the read-only replica.
    "settings_service.reset_to_defaults": ("settings_service", "reset_to_defaults"),
    "settings_service.delete_settings": ("settings_service", "delete_settings"),
    "settings_service.set_theme": ("settings_service", "set_theme"),
}


# SECURITY: commands that take the acting user's identity as an ARGUMENT.
# The host authenticates the session but then dispatches the client's raw args,
# so without this a client could simply pass someone else's name: an agent
# transferred another agent's reserved report numbers to itself, and a reporter
# reserved numbers in an agent's name (both proven by tests_warzone).
#
#   command -> (kind, positional index, kwarg name)
#   kind 'username' -> bound to the session username
#   kind 'user_id'  -> bound to the session user_id
IDENTITY_ARGS = {
    "report_number_service.reserve_block": ("username", 0, "username"),
    # transfer_numbers(from_user, to_user, numbers): only the SOURCE is identity.
    # The recipient is a legitimate free choice.
    "report_number_service.transfer_numbers": ("username", 0, "from_user"),
    "settings_service.save_settings": ("user_id", 1, "user_id"),
    "settings_service.save_setting": ("user_id", 2, "user_id"),
    "settings_service.reset_to_defaults": ("user_id", 0, "user_id"),
    "settings_service.delete_settings": ("user_id", 0, "user_id"),
    "settings_service.set_theme": ("user_id", 1, "user_id"),
}


def bind_identity(name: str, args: list, kwargs: dict, session_user: dict):
    """Overwrite any identity argument with the authenticated session's own
    identity. Returns (args, kwargs). Never trust the client for who it is."""
    spec = IDENTITY_ARGS.get(name)
    if not spec or not session_user:
        return args, kwargs
    kind, index, kwname = spec
    value = session_user.get("username") if kind == "username" else session_user.get("user_id")
    if value is None:
        return args, kwargs
    args = list(args or [])
    kwargs = dict(kwargs or {})
    if kwname in kwargs:
        kwargs[kwname] = value
    elif len(args) > index:
        args[index] = value
    else:                      # caller relied on the default -> pin it explicitly
        kwargs[kwname] = value
    return args, kwargs


def is_write_command(name: str) -> bool:
    return name in WRITE_COMMANDS


def dispatch(services: dict, name: str, args: list, kwargs: dict):
    if name not in WRITE_COMMANDS:
        raise KeyError(f"Unknown write command: {name}")
    service_attr, method = WRITE_COMMANDS[name]
    svc = services[service_attr]
    return getattr(svc, method)(*(args or []), **(kwargs or {}))
