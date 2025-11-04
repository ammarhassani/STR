"""Role-Based Access Control (RBAC) System"""
from typing import Optional


# Permission definitions for each role
PERMISSIONS = {
    'admin': {
        'view_dashboard': True,
        'view_reports': True,
        'add_report': True,
        'edit_report': True,
        'delete_report': True,
        'view_history': True,
        'rollback': True,
        'export': True,
        'access_admin_panel': True,
        'manage_users': True,
        'configure_dashboard': True,
        'configure_system': True,
    },
    'agent': {
        'view_dashboard': True,
        'view_reports': True,
        'add_report': True,
        'edit_report': True,  # Own reports only
        'delete_report': False,
        'view_history': True,
        'rollback': False,
        'export': True,
        'access_admin_panel': False,
        'manage_users': False,
        'configure_dashboard': False,
        'configure_system': False,
    },
    'reporter': {
        'view_dashboard': True,
        'view_reports': True,
        'add_report': False,  # NO data entry
        'edit_report': False,
        'delete_report': False,
        'view_history': True,
        'rollback': False,
        'export': True,
        'access_admin_panel': False,
        'manage_users': False,
        'configure_dashboard': False,
        'configure_system': False,
    },
}


def has_permission(
    user_role: str,
    permission: str,
    resource_owner: Optional[str] = None,
    current_user: Optional[str] = None
) -> bool:
    """
    Check if user has specific permission
    
    Args:
        user_role: User's role (admin, agent, reporter)
        permission: Permission to check
        resource_owner: Owner of the resource (for ownership checks)
        current_user: Current user's username
        
    Returns:
        True if user has permission, False otherwise
    """
    if user_role not in PERMISSIONS:
        return False
    
    has_perm = PERMISSIONS[user_role].get(permission, False)
    
    # Special case: agents can only edit their own reports
    if permission == 'edit_report' and user_role == 'agent':
        return has_perm and (resource_owner == current_user or resource_owner is None)
    
    return has_perm


def get_user_permissions(user_role: str) -> dict:
    """
    Get all permissions for a role
    
    Args:
        user_role: User's role
        
    Returns:
        Dictionary of permissions
    """
    return PERMISSIONS.get(user_role, {})


def can_access_route(user_role: str, route: str) -> bool:
    """
    Check if user can access a specific route
    
    Args:
        user_role: User's role
        route: Route name
        
    Returns:
        True if user can access route
    """
    route_permissions = {
        'dashboard': 'view_dashboard',
        'reports': 'view_reports',
        'add_report': 'add_report',
        'admin_panel': 'access_admin_panel',
        'export': 'export',
    }
    
    required_permission = route_permissions.get(route)
    if not required_permission:
        return False
    
    return has_permission(user_role, required_permission)
