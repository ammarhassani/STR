# FIU REPORT MANAGEMENT SYSTEM - COMPLETE DEVELOPMENT SPECIFICATION
## Python + Flet Desktop Application
### Version 2.0 - Complete Rewrite

---

## 🎯 PROJECT OVERVIEW

You are building a **PRODUCTION-GRADE** Financial Intelligence Unit (FIU) Report Management System using:
- **Python 3.10+**
- **Flet** (Modern cross-platform GUI framework)
- **SQLite3** (with WAL mode for concurrency)
- **Single executable deployment** (.exe for Windows)

**THIS IS NOT AN MVP. DELIVER COMPLETE, PRODUCTION-READY CODE WITH NO PLACEHOLDERS.**

---

## 🚨 CRITICAL CONSTRAINTS & CORRECTIONS

### Database Management (CRITICAL - Previously Broken)
❌ **WRONG** (Old System): Creating new SQLite DB for every session, making users download databases
✅ **CORRECT** (New System): 
- **ONE fixed database location** set by admin during setup
- **Admin configures path once** - never changes
- **App validates database on startup** - refuses to run if invalid
- **All CRUD operations on THE SAME database** - persistent storage
- **No temporary databases, no downloads, no session-based databases**

### User Roles (CRITICAL - Previously Confused)
**AGENT Role** (Data Entry Worker):
- Enters financial crime case reports
- Adds new reports, updates case information
- Performs CRUD operations on cases
- **Primary data input role**

**REPORTER Role** (Business Intelligence Analyst):
- Views dashboards and analytics ONLY
- Generates reports and analyzes trends
- **READ-ONLY access** to data
- **NO data entry capabilities**
- Business intelligence focus

**ADMIN Role** (System Administrator):
- Full system control
- User management
- Dashboard configuration
- System settings
- Everything

### Admin Control Panel Requirements
Admin must have **COMPLETE CONTROL** over:
1. **Dashboard Management**:
   - Add new metric cards (KPIs)
   - Add new charts (bar, line, pie)
   - Edit existing dashboard widgets
   - Delete dashboard elements
   - Rearrange dashboard layout
   - Change SQL queries for widgets
   - Set colors, icons, refresh intervals
   - Control widget visibility per role

2. **System Configuration**:
   - Set database path (CRITICAL)
   - Configure backup directory
   - Manage user accounts
   - Set system parameters
   - View audit logs

3. **Dynamic Dashboard System**:
   - All dashboard widgets stored in `dashboard_config` table
   - Admin creates/edits widgets through UI
   - SQL queries stored in database
   - Widgets automatically render based on config
   - Role-based visibility control

---

## 📋 TECHNOLOGY STACK

### Required Dependencies
```python
# requirements.txt
flet==0.25.0
```

### Python Standard Library (Built-in)
- sqlite3
- pathlib
- json
- datetime
- hashlib (for file validation)
- threading (for queue processing)
- time
- os
- sys
- re (for validation)
```

**NO external libraries except Flet. Everything else uses Python standard library.**

---

## 🗂️ PROJECT STRUCTURE

```
fiu_system/
├── main.py                    # Application entry point
├── requirements.txt           # Dependencies
├── config.py                  # Configuration management
├── database/
│   ├── __init__.py
│   ├── db_manager.py          # Database operations with WAL mode
│   ├── init_db.py             # Database initialization
│   ├── validation.py          # Database validation
│   └── queue_manager.py       # Concurrent write queue (max 3 users)
├── models/
│   ├── __init__.py
│   ├── user.py                # User model
│   ├── report.py              # Report model
│   ├── dashboard.py           # Dashboard widget model
│   └── system_config.py       # System configuration model
├── ui/
│   ├── __init__.py
│   ├── login.py               # Login screen
│   ├── dashboard.py           # Main dashboard (role-specific)
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── report_list.py     # Reports table with filters
│   │   ├── report_form.py     # Add/Edit report form
│   │   ├── report_detail.py   # Report detail view
│   │   └── report_history.py  # Change history view
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── control_panel.py   # Main admin panel
│   │   ├── user_management.py # User CRUD
│   │   ├── dashboard_config.py # Dashboard widget management
│   │   └── system_settings.py # System configuration
│   └── components/
│       ├── __init__.py
│       ├── kpi_card.py        # KPI card widget
│       ├── charts.py          # Chart components
│       ├── data_table.py      # Reusable data table
│       └── dialogs.py         # Modal dialogs
├── utils/
│   ├── __init__.py
│   ├── validation.py          # Input validation
│   ├── date_utils.py          # Date formatting/parsing
│   ├── export.py              # Excel/CSV export
│   └── logger.py              # Application logging
└── assets/
    └── icons/                 # Application icons
```

---

## 🔧 DATABASE ARCHITECTURE

### Fixed Database Location (CRITICAL)
```python
# config.py
import os
from pathlib import Path

class Config:
    # Admin sets this during first run - NEVER changes
    DATABASE_PATH = None  # Set to: \\\\shared\\.appdata\\fiu_system.db
    BACKUP_PATH = None    # Set to: \\\\shared\\.backups\\
    
    @classmethod
    def validate_paths(cls):
        """Validate database exists and is accessible"""
        if not cls.DATABASE_PATH:
            raise ValueError("Database path not configured!")
        
        db_path = Path(cls.DATABASE_PATH)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {cls.DATABASE_PATH}")
        
        # Validate database structure
        return validate_database_schema(cls.DATABASE_PATH)
```

### Database Manager with WAL Mode
```python
# database/db_manager.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager
import time

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_connection()
    
    def _init_connection(self):
        """Initialize database with WAL mode"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 5):
        """Execute query with retry logic for concurrent writes"""
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    return cursor.fetchall()
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                else:
                    raise
```

### Queue Manager for Concurrent Writes
```python
# database/queue_manager.py
import queue
import threading
import time

class WriteQueue:
    def __init__(self, db_manager):
        self.queue = queue.Queue()
        self.db_manager = db_manager
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
    
    def _process_queue(self):
        """Process write operations sequentially"""
        while self.is_running:
            try:
                operation = self.queue.get(timeout=1)
                query, params, callback = operation
                
                result = self.db_manager.execute_with_retry(query, params)
                
                if callback:
                    callback(result)
                
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Queue processing error: {e}")
    
    def submit(self, query: str, params: tuple = (), callback=None):
        """Submit write operation to queue"""
        self.queue.put((query, params, callback))
    
    def wait_completion(self):
        """Wait for all operations to complete"""
        self.queue.join()
    
    def stop(self):
        """Stop queue processing"""
        self.is_running = False
        self.worker_thread.join()
```

---

## 🎨 USER INTERFACE DESIGN

### Login Screen
```python
# ui/login.py
import flet as ft

class LoginScreen:
    def __init__(self, page: ft.Page, on_login_success):
        self.page = page
        self.on_login_success = on_login_success
        
        # UI Components
        self.username_field = ft.TextField(
            label="Username",
            width=300,
            autofocus=True,
            prefix_icon=ft.icons.PERSON
        )
        
        self.password_field = ft.TextField(
            label="Password",
            width=300,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.icons.LOCK
        )
        
        self.error_text = ft.Text(
            color=ft.colors.ERROR,
            visible=False
        )
        
        self.login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            on_click=self.handle_login
        )
    
    def handle_login(self, e):
        """Process login attempt"""
        username = self.username_field.value
        password = self.password_field.value
        
        # Validate credentials against database
        user = authenticate_user(username, password)
        
        if user:
            # Log session
            log_session(user['user_id'], user['username'])
            
            # Call success callback
            self.on_login_success(user)
        else:
            # Increment failed attempts
            increment_failed_attempts(username)
            
            # Show error
            self.error_text.value = "Invalid credentials"
            self.error_text.visible = True
            self.page.update()
    
    def build(self):
        """Build login UI"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("FIU Report Management System", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Login to continue", size=14, color=ft.colors.GREY_700),
                    ft.Container(height=20),
                    self.username_field,
                    self.password_field,
                    self.error_text,
                    ft.Container(height=10),
                    self.login_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )
```

### Main Dashboard (Role-Specific)
```python
# ui/dashboard.py
import flet as ft
from ui.components.kpi_card import KPICard
from ui.components.charts import PieChart, LineChart

class Dashboard:
    def __init__(self, page: ft.Page, user: dict, db_manager):
        self.page = page
        self.user = user
        self.db_manager = db_manager
        self.widgets = []
    
    def load_widgets(self):
        """Load dashboard widgets from database based on user role"""
        query = """
            SELECT * FROM dashboard_config 
            WHERE is_active = 1 
            AND visible_to_roles LIKE ?
            ORDER BY display_order
        """
        
        role_pattern = f"%{self.user['role']}%"
        widgets = self.db_manager.execute_with_retry(query, (role_pattern,))
        
        return widgets
    
    def render_widget(self, widget_config):
        """Render widget based on type"""
        widget_type = widget_config['widget_type']
        
        if widget_type == 'kpi_card':
            return self.render_kpi_card(widget_config)
        elif widget_type == 'pie_chart':
            return self.render_pie_chart(widget_config)
        elif widget_type == 'line_chart':
            return self.render_line_chart(widget_config)
        elif widget_type == 'bar_chart':
            return self.render_bar_chart(widget_config)
    
    def render_kpi_card(self, config):
        """Render KPI card"""
        # Execute SQL query to get value
        result = self.db_manager.execute_with_retry(config['sql_query'])
        value = result[0][0] if result else 0
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(name=config['icon'], color=config['color']),
                    ft.Text(config['title'], size=16, weight=ft.FontWeight.BOLD)
                ]),
                ft.Text(str(value), size=32, weight=ft.FontWeight.BOLD, color=config['color']),
            ]),
            padding=20,
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            width=250,
            height=150,
        )
    
    def render_pie_chart(self, config):
        """Render pie chart using query results"""
        results = self.db_manager.execute_with_retry(config['sql_query'])
        
        # Convert results to chart data
        chart_data = [
            {"label": row['label'], "value": row['value']} 
            for row in results
        ]
        
        return PieChart(
            title=config['title'],
            data=chart_data,
            width=400,
            height=300
        )
    
    def build(self):
        """Build dashboard UI"""
        widgets_config = self.load_widgets()
        
        # Create grid layout
        widget_rows = []
        current_row = []
        
        for widget_config in widgets_config:
            widget = self.render_widget(widget_config)
            current_row.append(widget)
            
            # Create new row after 4 widgets
            if len(current_row) >= 4:
                widget_rows.append(ft.Row(current_row, spacing=20))
                current_row = []
        
        # Add remaining widgets
        if current_row:
            widget_rows.append(ft.Row(current_row, spacing=20))
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(f"Welcome, {self.user['full_name']}", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Role: {self.user['role'].title()}", size=14, color=ft.colors.GREY_700),
                    ft.Divider(height=20),
                    ft.Column(widget_rows, spacing=20, scroll=ft.ScrollMode.AUTO),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )
```

### Report Form (Agent Role)
```python
# ui/reports/report_form.py
import flet as ft
from datetime import datetime

class ReportForm:
    def __init__(self, page: ft.Page, db_manager, user, report_id=None):
        self.page = page
        self.db_manager = db_manager
        self.user = user
        self.report_id = report_id
        self.fields = {}
        
        # Load column settings from database
        self.column_settings = self.load_column_settings()
    
    def load_column_settings(self):
        """Load form fields configuration from database"""
        query = """
            SELECT * FROM column_settings 
            WHERE is_visible = 1 
            ORDER BY display_order
        """
        return self.db_manager.execute_with_retry(query)
    
    def create_field(self, column_config):
        """Create form field based on column configuration"""
        field_name = column_config['column_name']
        data_type = column_config['data_type']
        
        if data_type == 'DROPDOWN':
            # Load dropdown options
            options = self.get_dropdown_options(field_name)
            field = ft.Dropdown(
                label=column_config['display_name_en'],
                options=[ft.dropdown.Option(opt) for opt in options],
                width=400,
            )
        elif data_type == 'DATE':
            field = ft.TextField(
                label=column_config['display_name_en'],
                hint_text="DD/MM/YYYY",
                width=400,
                prefix_icon=ft.icons.CALENDAR_TODAY,
            )
        elif data_type == 'INTEGER':
            field = ft.TextField(
                label=column_config['display_name_en'],
                keyboard_type=ft.KeyboardType.NUMBER,
                width=400,
            )
        else:  # TEXT
            field = ft.TextField(
                label=column_config['display_name_en'],
                multiline=(field_name in ['first_reason_for_suspicion', 'second_reason_for_suspicion', 'fiu_feedback']),
                width=400,
            )
        
        # Mark required fields
        if column_config['is_required']:
            field.label += " *"
        
        self.fields[field_name] = field
        return field
    
    def get_dropdown_options(self, field_name):
        """Get dropdown options from system_config"""
        query = """
            SELECT config_value FROM system_config 
            WHERE config_type = 'dropdown' 
            AND config_category = ?
            AND is_active = 1
            ORDER BY display_order
        """
        results = self.db_manager.execute_with_retry(query, (field_name,))
        return [row[0] for row in results]
    
    def validate_form(self):
        """Validate all required fields"""
        errors = []
        
        for col_config in self.column_settings:
            field_name = col_config['column_name']
            field = self.fields.get(field_name)
            
            if col_config['is_required'] and not field.value:
                errors.append(f"{col_config['display_name_en']} is required")
        
        return errors
    
    def save_report(self, e):
        """Save report to database"""
        # Validate
        errors = self.validate_form()
        if errors:
            self.show_error_dialog("\n".join(errors))
            return
        
        # Collect data
        data = {name: field.value for name, field in self.fields.items()}
        data['updated_by'] = self.user['username']
        data['updated_at'] = datetime.now().isoformat()
        
        if self.report_id:
            # Update existing report
            self.update_report(data)
        else:
            # Insert new report
            data['created_by'] = self.user['username']
            data['created_at'] = datetime.now().isoformat()
            self.insert_report(data)
    
    def insert_report(self, data):
        """Insert new report"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO reports ({columns}) VALUES ({placeholders})"
        
        self.db_manager.execute_with_retry(query, tuple(data.values()))
        
        # Log change
        self.log_change('INSERT', None, data)
        
        # Show success message
        self.show_success_dialog("Report saved successfully!")
    
    def update_report(self, data):
        """Update existing report"""
        # Get current values for change tracking
        current_data = self.get_report_data()
        
        # Build update query
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE reports SET {set_clause} WHERE report_id = ?"
        params = tuple(data.values()) + (self.report_id,)
        
        self.db_manager.execute_with_retry(query, params)
        
        # Log changes
        self.log_changes(current_data, data)
        
        # Show success message
        self.show_success_dialog("Report updated successfully!")
    
    def build(self):
        """Build form UI"""
        # Create form fields
        form_fields = []
        for col_config in self.column_settings:
            field = self.create_field(col_config)
            form_fields.append(field)
        
        # Add save and cancel buttons
        button_row = ft.Row([
            ft.ElevatedButton(
                text="Save",
                icon=ft.icons.SAVE,
                on_click=self.save_report
            ),
            ft.OutlinedButton(
                text="Cancel",
                icon=ft.icons.CANCEL,
                on_click=self.cancel_form
            ),
        ])
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "New Report" if not self.report_id else "Edit Report",
                        size=24,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Divider(),
                    ft.Column(form_fields, spacing=10, scroll=ft.ScrollMode.AUTO),
                    ft.Divider(),
                    button_row,
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )
```

### Admin Dashboard Configuration
```python
# ui/admin/dashboard_config.py
import flet as ft
import json

class DashboardConfigManager:
    def __init__(self, page: ft.Page, db_manager, user):
        self.page = page
        self.db_manager = db_manager
        self.user = user
    
    def add_widget_dialog(self):
        """Show dialog to add new dashboard widget"""
        widget_type = ft.Dropdown(
            label="Widget Type",
            options=[
                ft.dropdown.Option("kpi_card", "KPI Card"),
                ft.dropdown.Option("pie_chart", "Pie Chart"),
                ft.dropdown.Option("line_chart", "Line Chart"),
                ft.dropdown.Option("bar_chart", "Bar Chart"),
            ],
            width=400,
        )
        
        title_field = ft.TextField(label="Title (English)", width=400)
        title_ar_field = ft.TextField(label="Title (Arabic)", width=400)
        
        sql_query_field = ft.TextField(
            label="SQL Query",
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=400,
            hint_text="SELECT label, value FROM ..."
        )
        
        color_field = ft.TextField(
            label="Color (Hex)",
            value="#3b82f6",
            width=400,
        )
        
        icon_field = ft.TextField(
            label="Icon (Flet icon name)",
            width=400,
            hint_text="e.g., file_text"
        )
        
        roles_field = ft.TextField(
            label="Visible to Roles (comma-separated)",
            value="admin,reporter",
            width=400,
        )
        
        def save_widget(e):
            """Save new widget to database"""
            query = """
                INSERT INTO dashboard_config 
                (widget_type, title, title_ar, sql_query, color, icon, 
                 visible_to_roles, is_active, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, datetime('now'))
            """
            
            params = (
                widget_type.value,
                title_field.value,
                title_ar_field.value,
                sql_query_field.value,
                color_field.value,
                icon_field.value,
                roles_field.value,
                self.user['username'],
            )
            
            self.db_manager.execute_with_retry(query, params)
            
            # Log audit
            self.log_audit_action('DASHBOARD_WIDGET_ADDED', {
                'title': title_field.value,
                'type': widget_type.value
            })
            
            # Close dialog and refresh
            self.page.dialog.open = False
            self.page.update()
            self.load_widgets()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Dashboard Widget"),
            content=ft.Column([
                widget_type,
                title_field,
                title_ar_field,
                sql_query_field,
                color_field,
                icon_field,
                roles_field,
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=500),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False)),
                ft.ElevatedButton("Save", on_click=save_widget),
            ],
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def edit_widget(self, widget_id):
        """Edit existing dashboard widget"""
        # Load widget data
        query = "SELECT * FROM dashboard_config WHERE widget_id = ?"
        result = self.db_manager.execute_with_retry(query, (widget_id,))
        widget = result[0] if result else None
        
        if not widget:
            return
        
        # Create edit dialog (similar to add_widget_dialog but with existing values)
        # Implementation details omitted for brevity
        pass
    
    def delete_widget(self, widget_id):
        """Delete dashboard widget"""
        query = "UPDATE dashboard_config SET is_active = 0 WHERE widget_id = ?"
        self.db_manager.execute_with_retry(query, (widget_id,))
        
        # Log audit
        self.log_audit_action('DASHBOARD_WIDGET_DELETED', {'widget_id': widget_id})
        
        self.load_widgets()
    
    def build(self):
        """Build dashboard configuration UI"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Dashboard Configuration", size=24, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton(
                        text="Add Widget",
                        icon=ft.icons.ADD,
                        on_click=lambda e: self.add_widget_dialog()
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                # Widget list with edit/delete buttons
                self.build_widget_list(),
            ]),
            padding=20,
            expand=True,
        )
```

---

## 🔐 AUTHENTICATION & PERMISSIONS

### Role-Based Access Control
```python
# utils/permissions.py

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

def has_permission(user_role: str, permission: str, resource_owner: str = None, current_user: str = None) -> bool:
    """Check if user has permission"""
    if user_role not in PERMISSIONS:
        return False
    
    has_perm = PERMISSIONS[user_role].get(permission, False)
    
    # Special case: agents can only edit their own reports
    if permission == 'edit_report' and user_role == 'agent':
        return has_perm and (resource_owner == current_user)
    
    return has_perm
```

---

## 📊 EXPORT FUNCTIONALITY

### Excel Export
```python
# utils/export.py
import sqlite3
import csv
from datetime import datetime
from pathlib import Path

def export_to_csv(data: list, headers: list, filename: str):
    """Export data to CSV with UTF-8 BOM for Arabic support"""
    filepath = Path(filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)
    
    return filepath

def export_reports(db_manager, filters: dict = None, include_history: bool = False):
    """Export reports with optional filters"""
    # Build query
    query = "SELECT * FROM reports WHERE is_deleted = 0"
    params = []
    
    if filters:
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        
        if filters.get('date_from'):
            query += " AND report_date >= ?"
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            query += " AND report_date <= ?"
            params.append(filters['date_to'])
    
    # Execute query
    results = db_manager.execute_with_retry(query, tuple(params))
    
    # Get column names
    headers = [desc[0] for desc in results[0].keys()] if results else []
    
    # Convert to list of lists
    data = [list(row) for row in results]
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fiu_reports_{timestamp}.csv"
    
    # Export
    return export_to_csv(data, headers, filename)
```

---

## 🚀 APPLICATION ENTRY POINT

### Main Application
```python
# main.py
import flet as ft
from pathlib import Path
from config import Config
from database.db_manager import DatabaseManager
from database.validation import validate_database
from ui.login import LoginScreen
from ui.dashboard import Dashboard
from ui.reports.report_list import ReportList
from ui.admin.control_panel import AdminControlPanel

def main(page: ft.Page):
    page.title = "FIU Report Management System"
    page.window_width = 1280
    page.window_height = 720
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Initialize configuration
    try:
        Config.validate_paths()
    except Exception as e:
        # Show setup dialog if database not configured
        show_setup_dialog(page)
        return
    
    # Initialize database manager
    db_manager = DatabaseManager(Config.DATABASE_PATH)
    
    # Validate database schema
    is_valid, message = validate_database(Config.DATABASE_PATH)
    if not is_valid:
        show_error_dialog(page, f"Database validation failed: {message}")
        return
    
    # Application state
    current_user = None
    
    def on_login_success(user):
        """Handle successful login"""
        nonlocal current_user
        current_user = user
        
        # Show appropriate dashboard based on role
        if user['role'] == 'admin':
            show_admin_dashboard()
        elif user['role'] == 'agent':
            show_agent_dashboard()
        elif user['role'] == 'reporter':
            show_reporter_dashboard()
    
    def show_admin_dashboard():
        """Show admin dashboard with full controls"""
        page.clean()
        
        # Create navigation rail
        nav_rail = ft.NavigationRail(
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Dashboard"),
                ft.NavigationRailDestination(icon=ft.icons.TABLE_CHART, label="Reports"),
                ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label="Admin Panel"),
                ft.NavigationRailDestination(icon=ft.icons.LOGOUT, label="Logout"),
            ],
            on_change=handle_nav_change,
        )
        
        # Create main content area
        content = ft.Container(expand=True)
        
        # Build layout
        page.add(
            ft.Row([
                nav_rail,
                ft.VerticalDivider(width=1),
                content,
            ], expand=True)
        )
        
        # Load dashboard by default
        load_dashboard(content)
    
    def show_agent_dashboard():
        """Show agent dashboard (data entry focus)"""
        page.clean()
        
        nav_rail = ft.NavigationRail(
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Dashboard"),
                ft.NavigationRailDestination(icon=ft.icons.TABLE_CHART, label="Reports"),
                ft.NavigationRailDestination(icon=ft.icons.ADD, label="Add Report"),
                ft.NavigationRailDestination(icon=ft.icons.LOGOUT, label="Logout"),
            ],
            on_change=handle_nav_change,
        )
        
        content = ft.Container(expand=True)
        
        page.add(ft.Row([nav_rail, ft.VerticalDivider(width=1), content], expand=True))
        load_dashboard(content)
    
    def show_reporter_dashboard():
        """Show reporter dashboard (BI only, read-only)"""
        page.clean()
        
        nav_rail = ft.NavigationRail(
            destinations=[
                ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Dashboard"),
                ft.NavigationRailDestination(icon=ft.icons.TABLE_CHART, label="View Reports"),
                ft.NavigationRailDestination(icon=ft.icons.DOWNLOAD, label="Export"),
                ft.NavigationRailDestination(icon=ft.icons.LOGOUT, label="Logout"),
            ],
            on_change=handle_nav_change,
        )
        
        content = ft.Container(expand=True)
        
        page.add(ft.Row([nav_rail, ft.VerticalDivider(width=1), content], expand=True))
        load_dashboard(content)
    
    def load_dashboard(content_container):
        """Load dashboard into content container"""
        dashboard = Dashboard(page, current_user, db_manager)
        content_container.content = dashboard.build()
        page.update()
    
    # Show login screen
    login_screen = LoginScreen(page, on_login_success)
    page.add(login_screen.build())

if __name__ == "__main__":
    ft.app(target=main)
```

---

## 📦 DEPLOYMENT

### Building Single Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --windowed --name FIU_System main.py

# Output: dist/FIU_System.exe
```

### Deployment Structure
```
\\shared\apps\
├── FIU_System.exe          # Single executable
│
\\shared\.appdata\
├── fiu_system.db           # SQLite database (ONE location)
├── fiu_system.db-wal       # WAL file
├── fiu_system.db-shm       # Shared memory file
│
\\shared\.backups\
├── fiu_backup_20251104_020000.db
├── fiu_backup_20251105_020000.db
└── ...
```

---

## ✅ VALIDATION & ERROR HANDLING

### Input Validation
```python
# utils/validation.py
import re
from datetime import datetime

def validate_report_number(value: str) -> tuple[bool, str]:
    """Validate report number format: YYYY/MM/XXX"""
    pattern = r'^\d{4}/\d{2}/\d{3}$'
    if not re.match(pattern, value):
        return False, "Invalid format. Expected: YYYY/MM/XXX (e.g., 2025/11/001)"
    return True, ""

def validate_date(value: str) -> tuple[bool, str]:
    """Validate date format: DD/MM/YYYY"""
    try:
        datetime.strptime(value, "%d/%m/%Y")
        return True, ""
    except ValueError:
        return False, "Invalid date format. Expected: DD/MM/YYYY"

def validate_required(value: str, field_name: str) -> tuple[bool, str]:
    """Validate required field"""
    if not value or value.strip() == "":
        return False, f"{field_name} is required"
    return True, ""

def validate_total_transaction(value: str) -> tuple[bool, str]:
    """Validate total transaction format"""
    pattern = r'^\d+\s*SAR$'
    if not re.match(pattern, value):
        return False, "Invalid format. Expected: XXXXX SAR (e.g., 605040 SAR)"
    return True, ""
```

---

## 🎯 DELIVERABLES CHECKLIST

### Code Deliverables
- ✅ Complete database schema with all tables, indexes, triggers
- ✅ Database manager with WAL mode and retry logic
- ✅ Queue manager for concurrent write operations
- ✅ Login screen with authentication
- ✅ Role-specific dashboards (admin, agent, reporter)
- ✅ Report list with filters and search
- ✅ Report form with validation
- ✅ Admin control panel (user management, dashboard config, system settings)
- ✅ Dashboard widget system (dynamic, stored in database)
- ✅ Change history tracking and display
- ✅ Export functionality (CSV)
- ✅ Permission system (RBAC)
- ✅ Error handling and validation
- ✅ Logging and audit trail

### Documentation
- ✅ Database schema documentation
- ✅ API documentation for all modules
- ✅ Deployment instructions
- ✅ User guide (README)

### Testing Requirements
- Test with 3 concurrent users
- Test all CRUD operations
- Test all validation rules
- Test role-based permissions
- Test dashboard widget creation/editing
- Test export with 1000+ records
- Test database validation on startup
- Test error scenarios

---

## 🔒 CRITICAL RULES - NO EXCEPTIONS

1. **ONE DATABASE LOCATION** - Admin sets path, never changes
2. **APP VALIDATES DATABASE ON STARTUP** - Refuses to run if invalid
3. **NO SESSION DATABASES** - All operations on the fixed database
4. **NO PLACEHOLDERS** - Every function must be fully implemented
5. **AGENT ROLE = DATA ENTRY** - Adds reports
6. **REPORTER ROLE = BI ONLY** - Views dashboards, read-only
7. **ADMIN CONTROLS EVERYTHING** - Including dynamic dashboard configuration
8. **WAL MODE ALWAYS** - For concurrent access
9. **RETRY LOGIC FOR WRITES** - Handle database locks gracefully
10. **AUDIT ALL ADMIN ACTIONS** - Log everything to audit_log table

---

## 🚀 BEGIN DEVELOPMENT

Build a complete, production-ready FIU Report Management System following this specification exactly.

**REMEMBER: NO PLACEHOLDERS, NO MVPS, NO EMPTY FUNCTIONS. DELIVER COMPLETE CODE.**
