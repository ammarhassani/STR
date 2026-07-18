"""English strings — the source of truth for i18n keys (#3).
Add a key here first, then translate it in catalog_ar.py."""
STRINGS = {
    # app / common
    "app.title": "FIU System",
    "common.cancel": "Cancel",
    "common.save": "Save",
    "common.close": "Close",
    "common.delete": "Delete",
    "common.edit": "Edit",
    "common.add": "Add",
    "common.no_entity": "(no entity)",
    "common.reviewer": "Reviewer",
    "common.loading": "Loading...",

    # My Work
    "mywork.lane.rework": "Returned for Rework",
    "mywork.lane.draft": "Drafts",
    "mywork.lane.pending": "Pending Approval",
    "mywork.lane.approved": "Approved",
    "mywork.nothing": "Nothing here.",

    # login
    "login.title": "Login",
    "login.user_id": "User ID",
    "login.password": "Password",
    "login.button": "Login",
    "login.err.enter_user_id": "Please enter your user ID",
    "login.err.enter_password": "Please enter your password",
    "login.err.invalid": "Invalid username or password",

    # onboarding (two-way handshake)
    "onboard.title": "Welcome — complete your registration",
    "onboard.user_id": "User ID: {username}",
    "onboard.instruction": "Set your name and a password only you know.",
    "onboard.full_name": "Full name",
    "onboard.new_password": "New password",
    "onboard.confirm_password": "Confirm password",
    "onboard.submit": "Complete Registration",
    "onboard.err.name": "Please enter your full name.",
    "onboard.err.pw_len": "Password must be at least 8 characters.",
    "onboard.err.mismatch": "Passwords do not match.",

    # settings
    "settings.language": "Language",
    "settings.language.saved": "Language updated. Some screens apply it after reopening.",

    # navigation
    "nav.dashboard": "Dashboard",
    "nav.reports": "Reports",
    "nav.my_work": "My Work",
    "nav.export": "Export",
    "nav.approvals": "Approvals",
    "nav.users": "Users",
    "nav.logs": "System Logs",
    "nav.settings": "Settings",
    "nav.dropdowns": "Dropdowns",
    "nav.fields": "Fields",
    "nav.widgets": "Dashboard Widgets",
    "nav.activity": "Activity Log",

    # header actions
    "header.new_report": "New Report",
    "header.refresh": "Refresh",
    "header.help": "Help",
    "header.profile": "My Profile",
    "header.backup": "Backup & Restore",
    "header.reservations": "My Numbers",
    "header.logout": "Logout",
    "header.notifications": "Notifications",
    "header.admin_tools": "Admin Tools",
    "header.reservation_mgmt": "Reservation Management",

    # dashboard
    "dash.welcome": "Welcome back, {name}!",
    "dash.refresh": "Refresh",
    "dash.recent_activity": "Recent Activity",
    "dash.view_all": "View All",
    "dash.no_activity": "No recent activity",
    "dash.loading": "Loading dashboard...",
    "dash.loading_activity": "Loading activity...",
    "dash.loading_widgets": "Loading widgets...",
    "dash.no_widgets": "No dashboard widgets configured.",
    "dash.nav_activity_hint": "Navigate to Activity Log in the sidebar",
}
