# TECHNICAL ARCHITECTURE SPECIFICATION
## FIU Report Management System v2.0
### Python + Flet + SQLite3 with WAL Mode

---

## 📐 SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                     User Workstation                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           FIU_System.exe (Flet Application)           │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │   UI Layer  │  │ Business Logic│  │   DB Layer  │  │  │
│  │  │   (Flet)    │◄─┤   (Python)    │◄─┤  (SQLite3)  │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ File System Access
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Shared Windows Network Directory               │
│                                                             │
│  \\shared\.appdata\                                         │
│    ├── fiu_system.db          ◄─ SINGLE DATABASE (WAL)     │
│    ├── fiu_system.db-wal      ◄─ Write-Ahead Log           │
│    └── fiu_system.db-shm      ◄─ Shared Memory             │
│                                                             │
│  \\shared\.backups\                                         │
│    ├── fiu_backup_20251104_020000.db                       │
│    └── fiu_backup_20251105_020000.db                       │
│                                                             │
│  \\shared\apps\                                             │
│    └── FIU_System.exe         ◄─ Application Binary        │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────┐
│      Max 3 Concurrent Users            │
│  ┌──────────┐  ┌──────────┐  ┌──────┐ │
│  │ Agent 1  │  │ Agent 2  │  │Reporter│ │
│  └────┬─────┘  └────┬─────┘  └───┬───┘ │
│       │             │             │     │
│       └─────────────┴─────────────┘     │
│              Queue Manager              │
│       (Sequential Write Processing)     │
└────────────────────────────────────────┘
```

---

## 🗄️ DATABASE ARCHITECTURE

### SQLite3 with WAL Mode

**WAL (Write-Ahead Logging) Benefits:**
- Multiple readers can access database while one writer is active
- Better concurrency for our 3-user scenario
- No database locking for reads
- Atomic commits with rollback support

**Configuration:**
```python
# Applied on every database connection
PRAGMA journal_mode=WAL;        # Enable WAL mode
PRAGMA synchronous=NORMAL;      # Balance between safety and speed
PRAGMA cache_size=10000;        # 10MB cache
PRAGMA temp_store=MEMORY;       # Store temp tables in memory
PRAGMA foreign_keys=ON;         # Enable foreign key constraints
```

### Connection Management

```python
class DatabaseManager:
    """
    Manages database connections with WAL mode and retry logic
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_timeout = 10.0  # 10 seconds
        self._initialize_wal()
    
    def _initialize_wal(self):
        """Set up WAL mode (one-time operation)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.close()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Automatically handles commit/rollback
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.connection_timeout,
            isolation_level='DEFERRED'  # Optimal for WAL mode
        )
        conn.row_factory = sqlite3.Row  # Access columns by name
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_with_retry(self, query: str, params: tuple = (), max_retries: int = 5):
        """
        Execute query with exponential backoff retry
        Handles SQLITE_BUSY errors gracefully
        """
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    return cursor.rowcount
                    
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff: 0.5s, 1s, 1.5s, 2s, 2.5s
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise
            except Exception:
                raise
```

### Write Queue for Concurrency

```python
class WriteQueue:
    """
    Manages sequential write operations to prevent conflicts
    Processes max 3 concurrent users' write requests
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.queue = queue.Queue()
        self.db_manager = db_manager
        self.is_running = True
        
        # Start background worker thread
        self.worker = threading.Thread(target=self._process_queue, daemon=True)
        self.worker.start()
    
    def _process_queue(self):
        """Process write operations sequentially"""
        while self.is_running:
            try:
                # Get operation from queue (blocks with timeout)
                operation = self.queue.get(timeout=1.0)
                
                # Unpack operation
                query, params, callback, error_callback = operation
                
                try:
                    # Execute with retry logic
                    result = self.db_manager.execute_with_retry(query, params)
                    
                    # Call success callback if provided
                    if callback:
                        callback(result)
                        
                except Exception as e:
                    # Call error callback if provided
                    if error_callback:
                        error_callback(e)
                    else:
                        print(f"Queue processing error: {e}")
                
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue  # No operations in queue
    
    def submit(self, query: str, params: tuple = (), 
               callback=None, error_callback=None):
        """
        Submit write operation to queue
        
        Args:
            query: SQL query (INSERT, UPDATE, DELETE)
            params: Query parameters
            callback: Function to call on success (receives result)
            error_callback: Function to call on error (receives exception)
        """
        self.queue.put((query, params, callback, error_callback))
    
    def wait_completion(self):
        """Block until all queued operations are complete"""
        self.queue.join()
    
    def stop(self):
        """Stop queue processing (on app shutdown)"""
        self.is_running = False
        self.worker.join(timeout=5.0)
```

---

## 🔐 AUTHENTICATION FLOW

```
┌─────────────────────────────────────────────────────────────┐
│                    LOGIN PROCESS                            │
└─────────────────────────────────────────────────────────────┘

1. User enters credentials
   ↓
2. Query database:
   SELECT * FROM users 
   WHERE username = ? AND is_active = 1
   ↓
3. Check password (plain text comparison)
   ↓
4. If valid:
   ├─ Reset failed_login_attempts = 0
   ├─ Update last_login timestamp
   ├─ Create session object (in-memory)
   ├─ Log to session_log table
   └─ Redirect to role-specific dashboard
   
5. If invalid:
   ├─ Increment failed_login_attempts
   ├─ If attempts >= 5: Set is_active = 0 (lock account)
   └─ Show error message

┌─────────────────────────────────────────────────────────────┐
│                  SESSION MANAGEMENT                         │
└─────────────────────────────────────────────────────────────┘

Session Object (in-memory, not persistent):
{
    "user_id": 1,
    "username": "john.doe",
    "full_name": "John Doe",
    "role": "agent",
    "login_time": "2025-11-04T10:30:00",
    "last_activity": "2025-11-04T10:35:00"
}

Session Validation (on every page/action):
- Check if session exists
- Check if session timeout exceeded (30 minutes default)
- Update last_activity timestamp
- If expired: Redirect to login

Session Timeout Check:
if (current_time - last_activity) > timeout_minutes:
    logout_user()
    show_message("Session expired")
    redirect_to_login()
```

---

## 📊 DATA FLOW DIAGRAMS

### Read Operation Flow
```
User Action
    ↓
View Reports Page
    ↓
Database Manager
    ↓
SQLite Query (SELECT)
    ├─ Multiple concurrent reads OK (WAL mode)
    ├─ No locking
    └─ Fast response
    ↓
Return Results
    ↓
Render in Flet DataTable
```

### Write Operation Flow
```
User Action (Add/Edit Report)
    ↓
Form Validation
    ├─ Required fields check
    ├─ Format validation
    └─ Business rules validation
    ↓
Submit to Write Queue
    ↓
Queue Manager
    ├─ Sequential processing
    ├─ One write at a time
    └─ Prevents conflicts
    ↓
Database Manager
    ↓
Execute with Retry Logic
    ├─ Attempt 1 (immediate)
    ├─ Attempt 2 (0.5s delay)
    ├─ Attempt 3 (1.0s delay)
    ├─ Attempt 4 (1.5s delay)
    └─ Attempt 5 (2.0s delay)
    ↓
Change History Tracking
    ├─ Log to change_history table
    └─ Log to status_history (if status changed)
    ↓
Success Callback
    ↓
Update UI
    └─ Show success message
```

### Dashboard Rendering Flow
```
User Loads Dashboard
    ↓
Load Widget Configuration
    ├─ Query dashboard_config table
    ├─ Filter by user role
    └─ Order by display_order
    ↓
For Each Widget:
    ├─ Get widget type (kpi_card, chart, etc.)
    ├─ Execute SQL query from config
    ├─ Get data
    └─ Render widget with data
    ↓
Build Grid Layout
    ├─ Position widgets based on config
    └─ Apply responsive sizing
    ↓
Display Dashboard
```

---

## 🎨 UI ARCHITECTURE

### Flet Component Hierarchy

```
FletApp (main.py)
├── LoginScreen (ui/login.py)
│   ├── TextField (username)
│   ├── TextField (password)
│   └── ElevatedButton (login)
│
├── MainLayout (after login)
│   ├── NavigationRail (sidebar)
│   │   ├── Dashboard
│   │   ├── Reports
│   │   ├── Add Report (agent only)
│   │   ├── Admin Panel (admin only)
│   │   └── Logout
│   │
│   └── ContentArea (main view)
│       │
│       ├── Dashboard (ui/dashboard.py)
│       │   ├── KPICard (component)
│       │   │   ├── Icon
│       │   │   ├── Title
│       │   │   └── Value
│       │   │
│       │   ├── PieChart (component)
│       │   ├── LineChart (component)
│       │   └── BarChart (component)
│       │
│       ├── ReportList (ui/reports/report_list.py)
│       │   ├── SearchBar
│       │   ├── FilterDropdowns
│       │   ├── DataTable
│       │   │   ├── Column Headers
│       │   │   └── Data Rows
│       │   └── Pagination Controls
│       │
│       ├── ReportForm (ui/reports/report_form.py)
│       │   ├── Tab Navigation
│       │   ├── Form Fields (dynamic from column_settings)
│       │   │   ├── TextField
│       │   │   ├── Dropdown
│       │   │   └── DateField
│       │   └── Action Buttons
│       │
│       └── AdminPanel (ui/admin/control_panel.py)
│           ├── UserManagement
│           ├── DashboardConfig
│           │   ├── Widget List
│           │   └── Add/Edit Widget Dialog
│           └── SystemSettings
```

### State Management

```python
class AppState:
    """
    Global application state
    Shared across all views
    """
    def __init__(self):
        self.current_user = None
        self.db_manager = None
        self.write_queue = None
        self.config = None
    
    def set_current_user(self, user: dict):
        """Set logged in user"""
        self.current_user = user
    
    def get_current_user(self) -> dict:
        """Get logged in user"""
        return self.current_user
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return self.current_user is not None
    
    def logout(self):
        """Clear user session"""
        if self.current_user:
            # Log logout to session_log
            self.log_logout()
        
        self.current_user = None

# Global state instance
app_state = AppState()
```

---

## 🔄 CHANGE TRACKING SYSTEM

### Automatic Change Tracking

```python
def update_report(report_id: int, new_data: dict, change_reason: str, username: str):
    """
    Update report with automatic change tracking
    """
    # 1. Get current data
    current_data = get_report(report_id)
    
    # 2. Start transaction
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # 3. For each changed field
        for field_name, new_value in new_data.items():
            old_value = current_data.get(field_name)
            
            if old_value != new_value:
                # 4. Log change to change_history
                cursor.execute("""
                    INSERT INTO change_history 
                    (table_name, record_id, field_name, old_value, new_value, 
                     change_type, change_reason, changed_by, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, ('reports', report_id, field_name, old_value, new_value, 
                      'UPDATE', change_reason, username))
        
        # 5. Update report
        update_fields = ', '.join([f"{k} = ?" for k in new_data.keys()])
        update_values = list(new_data.values())
        
        cursor.execute(f"""
            UPDATE reports 
            SET {update_fields}, updated_by = ?, updated_at = datetime('now')
            WHERE report_id = ?
        """, update_values + [username, report_id])
        
        # 6. If status changed, log to status_history
        if 'status' in new_data and current_data['status'] != new_data['status']:
            cursor.execute("""
                INSERT INTO status_history 
                (report_id, from_status, to_status, comment, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (report_id, current_data['status'], new_data['status'], 
                  change_reason, username))
```

### Rollback Functionality

```python
def rollback_report(report_id: int, change_id: int, rollback_reason: str, username: str):
    """
    Rollback report to a previous state
    """
    # 1. Get the change record
    change = get_change_history_record(change_id)
    
    if not change or change['table_name'] != 'reports' or change['record_id'] != report_id:
        raise ValueError("Invalid rollback target")
    
    # 2. Get all changes from that point
    changes_to_rollback = get_changes_since(report_id, change['changed_at'])
    
    # 3. Build rollback data (restore old values)
    rollback_data = {}
    for ch in reversed(changes_to_rollback):
        if ch['field_name'] not in rollback_data:
            rollback_data[ch['field_name']] = ch['old_value']
    
    # 4. Apply rollback
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        # Update report
        for field_name, old_value in rollback_data.items():
            cursor.execute("""
                UPDATE reports 
                SET {} = ?, updated_by = ?, updated_at = datetime('now')
                WHERE report_id = ?
            """.format(field_name), (old_value, username, report_id))
            
            # Log rollback action
            cursor.execute("""
                INSERT INTO change_history 
                (table_name, record_id, field_name, old_value, new_value, 
                 change_type, change_reason, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, 'ROLLBACK', ?, ?, datetime('now'))
            """, ('reports', report_id, field_name, 
                  get_current_value(report_id, field_name), old_value, 
                  rollback_reason, username))
```

---

## 📤 EXPORT SYSTEM

### CSV Export Implementation

```python
def export_reports_to_csv(filters: dict = None, filename: str = None):
    """
    Export reports to CSV with UTF-8 BOM for Arabic support
    """
    import csv
    from datetime import datetime
    
    # 1. Build query
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
        
        if filters.get('search_term'):
            query += """ AND (
                report_number LIKE ? OR 
                reported_entity_name LIKE ? OR 
                cic LIKE ?
            )"""
            search_pattern = f"%{filters['search_term']}%"
            params.extend([search_pattern] * 3)
    
    # 2. Execute query
    results = db_manager.execute_with_retry(query, tuple(params))
    
    # 3. Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fiu_reports_{timestamp}.csv"
    
    # 4. Write to CSV with UTF-8 BOM
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        if results:
            # Get column names from first row
            headers = list(results[0].keys())
            
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for row in results:
                writer.writerow(dict(row))
    
    return filename
```

---

## 🛡️ VALIDATION SYSTEM

### Multi-Level Validation

```
┌─────────────────────────────────────────────────────────────┐
│                   VALIDATION LAYERS                         │
└─────────────────────────────────────────────────────────────┘

Layer 1: UI Validation (Immediate Feedback)
├─ Required field indicators (red asterisk)
├─ Input masks (date format, report number format)
├─ Character limits
└─ Type validation (numbers only, etc.)

Layer 2: Form Validation (On Submit)
├─ Required field completeness
├─ Format validation (regex patterns)
├─ Date logic (not future dates)
├─ Cross-field validation
└─ Business rule validation

Layer 3: Database Validation (Before Write)
├─ Uniqueness constraints (report_number, sn)
├─ Foreign key constraints
├─ Check constraints (gender, status enums)
└─ Trigger validation

Layer 4: Application Logic Validation
├─ Permission checks
├─ State transition validation
└─ Concurrent modification detection
```

### Validation Implementation

```python
class ReportValidator:
    """Comprehensive report validation"""
    
    @staticmethod
    def validate_required_fields(data: dict, column_settings: list) -> list:
        """Validate required fields"""
        errors = []
        
        for col in column_settings:
            if col['is_required']:
                field_name = col['column_name']
                if field_name not in data or not data[field_name]:
                    errors.append(f"{col['display_name_en']} is required")
        
        return errors
    
    @staticmethod
    def validate_report_number(report_number: str) -> tuple[bool, str]:
        """Validate report number format: YYYY/MM/XXX"""
        import re
        pattern = r'^\d{4}/\d{2}/\d{3}$'
        
        if not re.match(pattern, report_number):
            return False, "Invalid format. Expected: YYYY/MM/XXX (e.g., 2025/11/001)"
        
        # Check year is reasonable
        year = int(report_number[:4])
        current_year = datetime.now().year
        
        if year < 2000 or year > current_year + 1:
            return False, f"Year must be between 2000 and {current_year + 1}"
        
        return True, ""
    
    @staticmethod
    def validate_date(date_str: str) -> tuple[bool, str]:
        """Validate date format DD/MM/YYYY and not future"""
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            
            # Check not future date
            if date_obj > datetime.now():
                return False, "Date cannot be in the future"
            
            return True, ""
        except ValueError:
            return False, "Invalid date format. Expected: DD/MM/YYYY"
    
    @staticmethod
    def validate_total_transaction(value: str) -> tuple[bool, str]:
        """Validate total transaction format: XXXXX SAR"""
        import re
        pattern = r'^\d+\s*SAR$'
        
        if not re.match(pattern, value):
            return False, "Invalid format. Expected: XXXXX SAR (e.g., 605040 SAR)"
        
        return True, ""
    
    @staticmethod
    def validate_reporter_initials(value: str) -> tuple[bool, str]:
        """Validate reporter initials: 2 uppercase letters"""
        import re
        pattern = r'^[A-Z]{2}$'
        
        if not re.match(pattern, value):
            return False, "Invalid format. Expected: 2 uppercase letters (e.g., ZM)"
        
        return True, ""
```

---

## 🚀 DEPLOYMENT ARCHITECTURE

### Single Executable Deployment

```
Build Process:
1. Install dependencies: pip install -r requirements.txt
2. Build executable: pyinstaller --onefile --windowed main.py
3. Output: dist/FIU_System.exe (single file, ~15-25 MB)

Deployment:
1. Admin copies FIU_System.exe to \\shared\apps\
2. Admin runs first-time setup to configure database path
3. Users run FIU_System.exe directly from network share
4. No installation required on user machines
```

### First-Time Setup Flow

```python
def first_time_setup(page: ft.Page):
    """
    First-time setup wizard
    Admin configures database and backup paths
    """
    def on_setup_complete(database_path: str, backup_path: str):
        # 1. Validate paths are accessible
        if not os.path.exists(os.path.dirname(database_path)):
            show_error("Database directory not accessible")
            return
        
        if not os.path.exists(backup_path):
            show_error("Backup directory not accessible")
            return
        
        # 2. Initialize database if not exists
        if not os.path.exists(database_path):
            initialize_database(database_path)
        
        # 3. Save configuration
        Config.DATABASE_PATH = database_path
        Config.BACKUP_PATH = backup_path
        save_config_to_file()
        
        # 4. Validate database
        is_valid, message = validate_database(database_path)
        if not is_valid:
            show_error(f"Database validation failed: {message}")
            return
        
        # 5. Show success and proceed to login
        show_success("Setup complete! Please login.")
        show_login_screen()
    
    # Show setup wizard UI
    show_setup_wizard(on_setup_complete)
```

### Configuration Management

```python
# config.py
import json
from pathlib import Path

class Config:
    DATABASE_PATH = None
    BACKUP_PATH = None
    
    CONFIG_FILE = Path.home() / '.fiu_system' / 'config.json'
    
    @classmethod
    def load(cls):
        """Load configuration from file"""
        if cls.CONFIG_FILE.exists():
            with open(cls.CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                cls.DATABASE_PATH = config_data.get('database_path')
                cls.BACKUP_PATH = config_data.get('backup_path')
    
    @classmethod
    def save(cls):
        """Save configuration to file"""
        cls.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cls.CONFIG_FILE, 'w') as f:
            json.dump({
                'database_path': cls.DATABASE_PATH,
                'backup_path': cls.BACKUP_PATH,
            }, f, indent=2)
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if configuration exists"""
        return cls.DATABASE_PATH is not None and cls.BACKUP_PATH is not None
```

---

## 🔍 DATABASE VALIDATION

### Startup Validation Process

```python
def validate_database(db_path: str) -> tuple[bool, str]:
    """
    Comprehensive database validation on startup
    App refuses to run if validation fails
    """
    try:
        # 1. Check file exists
        if not os.path.exists(db_path):
            return False, f"Database file not found: {db_path}"
        
        # 2. Check file is accessible
        if not os.access(db_path, os.R_OK | os.W_OK):
            return False, "Database file is not readable/writable"
        
        # 3. Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 4. Check schema version
        cursor.execute("SELECT value FROM system_metadata WHERE key = 'schema_version'")
        result = cursor.fetchone()
        
        if not result:
            return False, "Database missing schema_version metadata"
        
        db_version = result[0]
        expected_version = "2.0.0"
        
        if db_version != expected_version:
            return False, f"Schema version mismatch: found {db_version}, expected {expected_version}"
        
        # 5. Verify required tables exist
        required_tables = [
            'users', 'reports', 'change_history', 'status_history',
            'dashboard_config', 'system_config', 'column_settings',
            'saved_filters', 'backup_log', 'session_log', 'audit_log'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            return False, f"Missing required tables: {', '.join(missing_tables)}"
        
        # 6. Verify critical data exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            return False, "No admin user found in database"
        
        cursor.execute("SELECT COUNT(*) FROM system_config")
        config_count = cursor.fetchone()[0]
        
        if config_count == 0:
            return False, "No system configuration found"
        
        cursor.execute("SELECT COUNT(*) FROM column_settings")
        column_count = cursor.fetchone()[0]
        
        if column_count == 0:
            return False, "No column settings found"
        
        # 7. Check WAL mode is enabled
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        
        if journal_mode.upper() != 'WAL':
            # Try to enable WAL mode
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            
            if journal_mode.upper() != 'WAL':
                return False, "Failed to enable WAL mode"
        
        conn.close()
        
        # 8. All validations passed
        return True, "Database validation successful"
        
    except sqlite3.DatabaseError as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
```

---

## 📊 PERFORMANCE OPTIMIZATION

### Query Optimization

```python
# Use indexes for frequently queried columns
CREATE INDEX idx_reports_report_number ON reports(report_number);
CREATE INDEX idx_reports_cic ON reports(cic);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_report_date ON reports(report_date);
CREATE INDEX idx_reports_is_deleted ON reports(is_deleted);

# Use EXPLAIN QUERY PLAN to verify index usage
EXPLAIN QUERY PLAN 
SELECT * FROM reports WHERE report_number = '2025/11/001';

# Result should show "USING INDEX idx_reports_report_number"
```

### Pagination Strategy

```python
def get_reports_paginated(page_number: int = 1, page_size: int = 50, filters: dict = None):
    """
    Get reports with pagination
    Only loads requested page to reduce memory usage
    """
    offset = (page_number - 1) * page_size
    
    # Build base query
    query = "SELECT * FROM reports WHERE is_deleted = 0"
    params = []
    
    # Add filters
    if filters:
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        
        if filters.get('search_term'):
            query += """ AND (
                report_number LIKE ? OR 
                reported_entity_name LIKE ? OR 
                cic LIKE ?
            )"""
            search_pattern = f"%{filters['search_term']}%"
            params.extend([search_pattern] * 3)
    
    # Add pagination
    query += f" ORDER BY report_id DESC LIMIT {page_size} OFFSET {offset}"
    
    # Execute
    results = db_manager.execute_with_retry(query, tuple(params))
    
    # Get total count for pagination
    count_query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
    count_params = []
    
    # Add same filters to count query
    # ... (omitted for brevity)
    
    total_count = db_manager.execute_with_retry(count_query, tuple(count_params))[0][0]
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        'data': results,
        'page': page_number,
        'page_size': page_size,
        'total_count': total_count,
        'total_pages': total_pages,
    }
```

### Caching Strategy

```python
class ConfigCache:
    """
    Cache system configuration to avoid repeated database queries
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._cache = {}
        self._last_refresh = None
        self._refresh_interval = 300  # 5 minutes
    
    def get(self, config_key: str) -> str:
        """Get configuration value with caching"""
        # Check if cache needs refresh
        if self._should_refresh():
            self._refresh_cache()
        
        return self._cache.get(config_key)
    
    def _should_refresh(self) -> bool:
        """Check if cache should be refreshed"""
        if self._last_refresh is None:
            return True
        
        elapsed = time.time() - self._last_refresh
        return elapsed > self._refresh_interval
    
    def _refresh_cache(self):
        """Refresh cache from database"""
        query = "SELECT config_key, config_value FROM system_config WHERE is_active = 1"
        results = self.db_manager.execute_with_retry(query)
        
        self._cache = {row['config_key']: row['config_value'] for row in results}
        self._last_refresh = time.time()
    
    def invalidate(self):
        """Force cache refresh on next access"""
        self._last_refresh = None
```

---

## 🔒 SECURITY CONSIDERATIONS

### SQL Injection Prevention

```python
# ❌ VULNERABLE - NEVER DO THIS
username = request.get('username')
query = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(query)

# ✅ SAFE - ALWAYS USE PARAMETERIZED QUERIES
username = request.get('username')
query = "SELECT * FROM users WHERE username = ?"
cursor.execute(query, (username,))
```

### Input Sanitization

```python
def sanitize_input(value: str, max_length: int = None) -> str:
    """
    Sanitize user input
    """
    if value is None:
        return ""
    
    # Strip whitespace
    value = value.strip()
    
    # Limit length
    if max_length:
        value = value[:max_length]
    
    # Remove control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
    
    return value
```

### Audit Logging

```python
def log_admin_action(user_id: int, username: str, action_type: str, details: dict):
    """
    Log administrative actions for audit trail
    """
    query = """
        INSERT INTO audit_log 
        (user_id, username, action_type, action_details, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """
    
    details_json = json.dumps(details)
    db_manager.execute_with_retry(query, (user_id, username, action_type, details_json))
```

---

## 📈 MONITORING & LOGGING

### Application Logging

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure application logging"""
    log_dir = Path.home() / '.fiu_system' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'application.log'
    
    # Create rotating file handler (max 10MB, keep 5 backups)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('fiu_system')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    return logger

# Usage
logger = setup_logging()
logger.info("Application started")
logger.error("Database connection failed", exc_info=True)
```

---

## 🎯 TESTING STRATEGY

### Unit Tests
```python
import unittest

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db_path = ':memory:'  # In-memory database for testing
        self.db_manager = DatabaseManager(self.db_path)
        initialize_database(self.db_path)
    
    def test_insert_report(self):
        """Test report insertion"""
        data = {
            'sn': 1,
            'report_number': '2025/11/001',
            'report_date': '04/11/2025',
            'reported_entity_name': 'Test Entity',
            'status': 'Open',
            'created_by': 'test_user'
        }
        
        report_id = insert_report(self.db_manager, data)
        self.assertIsNotNone(report_id)
        
        # Verify report was inserted
        report = get_report(self.db_manager, report_id)
        self.assertEqual(report['report_number'], '2025/11/001')
```

### Integration Tests
```python
def test_concurrent_writes():
    """Test concurrent write operations"""
    db_manager = DatabaseManager('test.db')
    queue = WriteQueue(db_manager)
    
    results = []
    
    def callback(result):
        results.append(result)
    
    # Submit multiple writes
    for i in range(10):
        query = "INSERT INTO test_table (value) VALUES (?)"
        queue.submit(query, (f"value_{i}",), callback)
    
    # Wait for completion
    queue.wait_completion()
    
    # Verify all writes succeeded
    assert len(results) == 10
```

---

## 📦 DEPENDENCIES & VERSIONS

```
Python: 3.10+
Flet: 0.25.0

Standard Library Only:
- sqlite3
- pathlib
- json
- datetime
- threading
- queue
- time
- os
- sys
- re
- csv
- logging
- contextlib
- hashlib
```

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] Database schema deployed to shared location
- [ ] Database path configured correctly
- [ ] Backup directory configured and accessible
- [ ] WAL mode enabled and verified
- [ ] Admin user created
- [ ] System configuration populated
- [ ] Column settings configured
- [ ] Default dashboard widgets created
- [ ] Executable built and tested
- [ ] Executable deployed to shared apps directory
- [ ] User accounts created
- [ ] Permissions verified for all roles
- [ ] Concurrent access tested (3 users)
- [ ] Backup system tested
- [ ] Export functionality tested
- [ ] Documentation provided to users

---

**END OF TECHNICAL ARCHITECTURE SPECIFICATION**
