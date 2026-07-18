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
}


def is_write_command(name: str) -> bool:
    return name in WRITE_COMMANDS


def dispatch(services: dict, name: str, args: list, kwargs: dict):
    if name not in WRITE_COMMANDS:
        raise KeyError(f"Unknown write command: {name}")
    service_attr, method = WRITE_COMMANDS[name]
    svc = services[service_attr]
    return getattr(svc, method)(*(args or []), **(kwargs or {}))
