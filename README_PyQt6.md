# FIU Report Management System - PyQt6 Edition

## Version 2.0.0 - Modern Architecture Refactoring

This is a complete refactoring of the FIU Report Management System from Flet to PyQt6 with modern, modular architecture.

## Key Improvements

### Technology Stack
- **UI Framework**: Migrated from Flet to PyQt6
- **Architecture**: Modular, service-oriented design
- **Logging**: Database-backed logging system with audit trail
- **Async Operations**: QThread workers for responsive UI
- **Styling**: Modern Material Design-inspired QSS stylesheet

### Architecture Overview

```
FIU System/
├── main.py                    # Application orchestrator (minimal entry point)
├── config.py                  # Configuration management
├── requirements.txt           # PyQt6 dependencies
│
├── database/                  # Database layer
│   ├── db_manager.py         # Database operations with retry logic
│   ├── init_db.py            # Database initialization
│   ├── queue_manager.py      # Write queue for concurrency
│   └── schema.sql            # Enhanced schema with system_logs table
│
├── services/                  # Business logic layer
│   ├── auth_service.py       # Authentication & user management
│   ├── report_service.py     # Report CRUD operations
│   ├── dashboard_service.py  # Dashboard statistics
│   └── logging_service.py    # Database-backed logging
│
├── ui/                        # Presentation layer
│   ├── windows/              # Main application windows
│   │   ├── login_window.py   # Modern login interface
│   │   └── main_window.py    # Main application window with navigation
│   │
│   ├── widgets/              # Reusable view components
│   │   ├── dashboard_view.py         # Dashboard with KPI cards
│   │   ├── reports_view.py           # Reports management
│   │   ├── log_management_view.py    # Admin log interface
│   │   └── placeholder_view.py       # Placeholder for future views
│   │
│   ├── dialogs/              # Dialog windows (empty, ready for implementation)
│   └── workers.py            # QThread workers for async operations
│
├── models/                    # Data models (ready for implementation)
├── resources/                 # Application resources
│   └── style.qss             # Modern QSS stylesheet
│
└── utils/                     # Utility modules (preserved from original)
    ├── logger.py             # File logging configuration
    ├── permissions.py        # RBAC system
    ├── validation.py         # Input validation
    ├── export.py             # CSV export
    └── date_utils.py         # Date formatting
```

## New Features

### 1. Database-Backed Logging
- All logs stored in `system_logs` table
- Track user context with each log entry
- Exception tracking with stack traces
- Log filtering, export to file, and cleanup capabilities

### 2. Admin Log Management Interface
- View logs with filtering (level, module, date range)
- Export logs to .txt file
- Clear old logs with confirmation
- Real-time log statistics

### 3. Modern UI with PyQt6
- Clean, professional Material Design-inspired interface
- Responsive layouts using Qt layouts
- Modern sidebar navigation
- KPI cards with color coding
- Dark navigation with light content area

### 4. Async Operations
- QThread workers for long-running tasks
- Progress reporting for user feedback
- Non-blocking UI operations
- Proper thread cleanup

### 5. Service Layer Architecture
- Clear separation of concerns
- Business logic isolated from UI
- Easy to test and maintain
- Dependency injection pattern

## Installation

### Requirements
```bash
pip install -r requirements.txt
```

### Dependencies
- PyQt6 >= 6.7.0
- Python >= 3.9
- python-dateutil >= 2.8.2
- bcrypt >= 4.1.2

## Running the Application

```bash
python main.py
```

### First Run
On first run, the system will:
1. Create default directories in `~/FIU_System/`
2. Initialize the database with schema
3. Create default admin user (admin/admin123)
4. Apply modern stylesheet

### Default Login
- Username: `admin`
- Password: `admin123`

**Note**: Change the default password immediately after first login.

## Current Implementation Status

### ✅ Completed
- [x] PyQt6 framework integration
- [x] Modular architecture with services layer
- [x] Database-backed logging system
- [x] Login window with async authentication
- [x] Main window with sidebar navigation
- [x] Dashboard view with KPI cards
- [x] Reports list view with filtering
- [x] Admin log management interface
- [x] QThread workers for async operations
- [x] Modern QSS stylesheet
- [x] Clean main.py orchestrator

### 🚧 To Be Implemented
- [ ] Add/Edit report dialog with full form
- [ ] User management CRUD interface
- [ ] System settings configuration
- [ ] CSV export functionality
- [ ] Advanced filtering and search
- [ ] Report status workflow
- [ ] Backup/restore interface
- [ ] Dashboard charts (using matplotlib or pyqtgraph)
- [ ] Report history viewer
- [ ] Print functionality

## Key Design Patterns

### 1. Service Layer Pattern
Business logic is encapsulated in service classes that can be reused across different UI components.

### 2. Model-View Separation
UI components (views) are separated from data access (services), making the code more maintainable.

### 3. Dependency Injection
Services are injected into UI components, making testing easier and reducing coupling.

### 4. Worker Thread Pattern
Long-running operations use QThread workers to keep the UI responsive.

### 5. Signal-Slot Mechanism
Qt's signal-slot mechanism is used for clean event handling and loose coupling.

## Database Schema Enhancements

### New Table: system_logs
Stores all application logs with:
- Timestamp and log level
- Module and function context
- User association
- Exception details with stack traces
- Extra data as JSON

### Enhanced Audit Trail
- All user actions logged
- Report changes tracked
- Status changes with history
- Session management

## Stylesheet Customization

The application uses a comprehensive QSS stylesheet (`resources/style.qss`) that can be customized:

- Color schemes
- Button styles
- Table appearance
- Card components
- Hover effects

## Configuration

Configuration is stored in `~/.fiu_system/config.json`:

```json
{
  "database_path": "~/FIU_System/database/fiu_reports.db",
  "backup_path": "~/FIU_System/backups/",
  "session_timeout": 30,
  "max_login_attempts": 5,
  "records_per_page": 50
}
```

## Logging

Application logs are stored in two places:
1. **File**: `~/.fiu_system/app.log` (rotating, 10MB max, 5 backups)
2. **Database**: `system_logs` table (queryable, filterable)

## Security Considerations

### Current Implementation
- Plain text passwords (legacy requirement)
- Session management with timeout
- Failed login attempt tracking
- Account locking after 5 failed attempts
- Role-based access control (RBAC)

### Future Enhancements
- bcrypt password hashing (bcrypt library already installed)
- Two-factor authentication
- Password complexity requirements
- Session encryption

## Development Guidelines

### Adding a New View

1. Create view class in `ui/widgets/`:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout
class MyView(QWidget):
    def __init__(self, service, logging_service):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        # Build UI
        pass

    def refresh(self):
        # Called when view is refreshed
        pass
```

2. Import and add to main.py:
```python
from ui.widgets.my_view import MyView

# In setup_views():
my_view = MyView(self.some_service, self.logging_service)
self.main_window.add_view('my_view', my_view)
```

### Adding a New Service

1. Create service class in `services/`:
```python
class MyService:
    def __init__(self, db_manager, logging_service):
        self.db_manager = db_manager
        self.logger = logging_service

    def my_operation(self):
        # Business logic
        pass
```

2. Initialize in main.py:
```python
self.my_service = MyService(self.db_manager, self.logging_service)
```

## Testing

### Manual Testing Checklist
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] View dashboard statistics
- [ ] Filter and search reports
- [ ] View system logs
- [ ] Export logs to file
- [ ] Clear logs with confirmation
- [ ] Logout and re-login
- [ ] Window close confirmation

### Unit Testing (Future)
Structure is ready for pytest integration:
```
tests/
├── test_services/
├── test_ui/
└── test_database/
```

## Performance Considerations

- **Async Operations**: All database queries that might take >100ms use QThread workers
- **Pagination**: Reports and logs use limit/offset pagination
- **Lazy Loading**: Views load data only when activated
- **Connection Pooling**: Database manager handles connections efficiently
- **WAL Mode**: SQLite WAL mode for better concurrency

## Migration from Flet Version

The old Flet-based code is preserved in backup files:
- `main_old_flet.py.bak`
- `admin_panel_old_flet.py.bak`

These can be used as reference for business logic that needs to be reimplemented.

## Troubleshooting

### Database Locked Error
- Ensure no other instances are running
- Check WAL mode is enabled
- Increase timeout in db_manager.py

### StyleSheet Not Loading
- Check `resources/style.qss` exists
- Verify file encoding is UTF-8
- Check logs for stylesheet errors

### QThread Warnings
- Ensure workers are properly cleaned up
- Check for circular references
- Verify signals are connected before starting threads

## License

[Your License Here]

## Contributors

[Your Team/Contributors Here]

## Changelog

### Version 2.0.0 (2025-11-07)
- Complete refactoring from Flet to PyQt6
- Implemented modular service-oriented architecture
- Added database-backed logging system
- Created modern Material Design-inspired UI
- Implemented async operations with QThread workers
- Enhanced database schema with system_logs table
- Added admin log management interface
- Created comprehensive QSS stylesheet

---

**Note**: This is a work in progress. Additional features and views will be implemented in future updates.
