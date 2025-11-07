-- ============================================================================
-- FIU REPORT MANAGEMENT SYSTEM - DATABASE SCHEMA
-- Technology: Python + Flet + SQLite3 with WAL Mode
-- Version: 2.0 (Complete Rewrite)
-- Last Updated: 2025-11-04
-- ============================================================================

-- Enable WAL mode for better concurrency (set by Python code)
-- PRAGMA journal_mode=WAL;
-- PRAGMA synchronous=NORMAL;
-- PRAGMA cache_size=10000;
-- PRAGMA temp_store=MEMORY;

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now')),
    updated_by TEXT
);

INSERT OR REPLACE INTO system_metadata (key, value) VALUES ('schema_version', '2.0.0');
INSERT OR REPLACE INTO system_metadata (key, value) VALUES ('db_initialized', datetime('now'));

-- ============================================================================
-- USER MANAGEMENT
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password TEXT NOT NULL, -- Plain text as per client requirement
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'agent', 'reporter')),
    is_active INTEGER DEFAULT 1,
    failed_login_attempts INTEGER DEFAULT 0,
    last_login TEXT,
    theme_preference TEXT DEFAULT 'light' CHECK(theme_preference IN ('light', 'dark')),
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT,
    updated_at TEXT,
    updated_by TEXT
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ============================================================================
-- FINANCIAL CRIME REPORTS (Main Entity)
-- ============================================================================
CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sn INTEGER UNIQUE NOT NULL,
    report_number TEXT UNIQUE NOT NULL,
    report_date TEXT NOT NULL, -- DD/MM/YYYY format
    outgoing_letter_number TEXT,
    reported_entity_name TEXT NOT NULL,
    legal_entity_owner TEXT,
    gender TEXT CHECK(gender IN ('Ø°ÙƒØ±', 'Ø£Ù†Ø«Ù‰', '')),
    nationality TEXT,
    id_cr TEXT,
    account_membership TEXT,
    branch_id TEXT,
    cic TEXT,
    first_reason_for_suspicion TEXT,
    second_reason_for_suspicion TEXT,
    type_of_suspected_transaction TEXT,
    arb_staff TEXT CHECK(arb_staff IN ('Ù†Ø¹Ù…', 'Ù„Ø§', '')),
    total_transaction TEXT,
    report_classification TEXT,
    report_source TEXT,
    reporting_entity TEXT,
    paper_or_automated TEXT CHECK(paper_or_automated IN ('ÙˆØ±Ù‚ÙŠ', 'Ø¢Ù„ÙŠ', '')),
    reporter_initials TEXT,
    sending_date TEXT,
    original_copy_confirmation TEXT,
    fiu_number TEXT,
    fiu_letter_receive_date TEXT,
    fiu_feedback TEXT,
    fiu_letter_number TEXT,
    fiu_date TEXT,
    status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'Case Review', 'Under Investigation', 'Case Validation', 'Close Case', 'Closed with STR')),
    is_deleted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT NOT NULL,
    updated_at TEXT,
    updated_by TEXT
);

CREATE INDEX idx_reports_report_number ON reports(report_number);
CREATE INDEX idx_reports_sn ON reports(sn);
CREATE INDEX idx_reports_cic ON reports(cic);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_report_date ON reports(report_date);
CREATE INDEX idx_reports_is_deleted ON reports(is_deleted);
CREATE INDEX idx_reports_entity_name ON reports(reported_entity_name);
CREATE INDEX idx_reports_created_by ON reports(created_by);

-- ============================================================================
-- CHANGE HISTORY TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS change_history (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type TEXT NOT NULL CHECK(change_type IN ('INSERT', 'UPDATE', 'DELETE', 'REOPEN', 'ROLLBACK', 'STATUS_CHANGE')),
    change_reason TEXT,
    changed_by TEXT NOT NULL,
    changed_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_change_history_record ON change_history(table_name, record_id);
CREATE INDEX idx_change_history_date ON change_history(changed_at);
CREATE INDEX idx_change_history_user ON change_history(changed_by);
CREATE INDEX idx_change_history_type ON change_history(change_type);

-- ============================================================================
-- STATUS CHANGE HISTORY
-- ============================================================================
CREATE TABLE IF NOT EXISTS status_history (
    status_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    comment TEXT,
    changed_by TEXT NOT NULL,
    changed_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE
);

CREATE INDEX idx_status_history_report ON status_history(report_id);
CREATE INDEX idx_status_history_date ON status_history(changed_at);
CREATE INDEX idx_status_history_changed_by ON status_history(changed_by);

-- ============================================================================
-- DASHBOARD CONFIGURATION (DYNAMIC DASHBOARD SYSTEM)
-- ============================================================================
CREATE TABLE IF NOT EXISTS dashboard_config (
    widget_id INTEGER PRIMARY KEY AUTOINCREMENT,
    widget_type TEXT NOT NULL CHECK(widget_type IN ('kpi_card', 'bar_chart', 'line_chart', 'pie_chart', 'table', 'metric')),
    title TEXT NOT NULL,
    title_ar TEXT, -- Arabic translation
    sql_query TEXT NOT NULL, -- SQL query to fetch data
    position_row INTEGER DEFAULT 0,
    position_col INTEGER DEFAULT 0,
    width INTEGER DEFAULT 1, -- Grid width (1-12)
    height INTEGER DEFAULT 1, -- Grid height
    color TEXT DEFAULT '#3b82f6', -- Primary color
    icon TEXT, -- Icon name (for KPI cards)
    refresh_interval INTEGER DEFAULT 0, -- Seconds (0 = manual refresh)
    visible_to_roles TEXT DEFAULT 'admin,reporter', -- Comma-separated roles
    is_active INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    chart_options TEXT, -- JSON string for chart.js options
    created_by TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_by TEXT,
    updated_at TEXT
);

CREATE INDEX idx_dashboard_config_active ON dashboard_config(is_active);
CREATE INDEX idx_dashboard_config_order ON dashboard_config(display_order);
CREATE INDEX idx_dashboard_config_type ON dashboard_config(widget_type);

-- ============================================================================
-- SYSTEM CONFIGURATION
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type TEXT CHECK(config_type IN ('dropdown', 'setting', 'column', 'path')),
    config_category TEXT,
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    updated_by TEXT
);

CREATE INDEX idx_system_config_key ON system_config(config_key);
CREATE INDEX idx_system_config_type ON system_config(config_type);
CREATE INDEX idx_system_config_category ON system_config(config_category);

-- ============================================================================
-- SAVED FILTERS (USER PREFERENCES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS saved_filters (
    filter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filter_name TEXT NOT NULL,
    filter_criteria TEXT NOT NULL, -- JSON string
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_saved_filters_user ON saved_filters(user_id);

-- ============================================================================
-- COLUMN SETTINGS (DYNAMIC FORM FIELDS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS column_settings (
    column_id INTEGER PRIMARY KEY AUTOINCREMENT,
    column_name TEXT UNIQUE NOT NULL,
    display_name_en TEXT NOT NULL,
    display_name_ar TEXT NOT NULL,
    data_type TEXT DEFAULT 'TEXT' CHECK(data_type IN ('TEXT', 'INTEGER', 'REAL', 'DATE', 'DROPDOWN')),
    is_visible INTEGER DEFAULT 1,
    is_required INTEGER DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    validation_rules TEXT, -- JSON string
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    updated_by TEXT
);

CREATE INDEX idx_column_settings_visible ON column_settings(is_visible);
CREATE INDEX idx_column_settings_order ON column_settings(display_order);
CREATE INDEX idx_column_settings_name ON column_settings(column_name);

-- ============================================================================
-- BACKUP LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS backup_log (
    backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_filename TEXT NOT NULL,
    backup_path TEXT,
    backup_size INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    created_by TEXT
);

CREATE INDEX idx_backup_log_date ON backup_log(created_at);

-- ============================================================================
-- SESSION LOG (AUDIT TRAIL)
-- ============================================================================
CREATE TABLE IF NOT EXISTS session_log (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    login_time TEXT NOT NULL,
    logout_time TEXT,
    session_duration INTEGER, -- seconds
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_session_log_user ON session_log(user_id);
CREATE INDEX idx_session_log_login ON session_log(login_time);

-- ============================================================================
-- AUDIT LOG (ADMIN ACTIONS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    action_type TEXT NOT NULL, -- 'USER_CREATED', 'CONFIG_CHANGED', 'DASHBOARD_MODIFIED', etc.
    action_details TEXT, -- JSON string with details
    ip_address TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_date ON audit_log(created_at);
CREATE INDEX idx_audit_log_action ON audit_log(action_type);

-- ============================================================================
-- SYSTEM LOGS (APPLICATION-LEVEL LOGGING)
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    log_level TEXT NOT NULL CHECK(log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    module TEXT NOT NULL, -- Module/component that generated the log
    function_name TEXT, -- Function/method name
    message TEXT NOT NULL,
    user_id INTEGER, -- NULL if system-generated
    username TEXT, -- Username if user context available
    exception_type TEXT, -- Exception class name if applicable
    exception_message TEXT, -- Exception message if applicable
    stack_trace TEXT, -- Full stack trace if applicable
    extra_data TEXT, -- JSON string for additional context
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_module ON system_logs(module);
CREATE INDEX idx_system_logs_user ON system_logs(user_id);
CREATE INDEX idx_system_logs_timestamp_level ON system_logs(timestamp, log_level);

-- ============================================================================
-- DEFAULT DATA INSERTION
-- ============================================================================

-- Default Admin User
INSERT OR IGNORE INTO users (user_id, username, password, full_name, role, is_active, created_at, created_by)
VALUES (1, 'admin', 'admin123', 'System Administrator', 'admin', 1, datetime('now'), 'SYSTEM');

-- Default System Config Settings
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, display_order) VALUES
-- Application Settings
('app_name', 'FIU Report Management System', 'setting', 'general', 1),
('app_version', '2.0.0', 'setting', 'general', 2),
('session_timeout', '30', 'setting', 'security', 3),
('max_login_attempts', '5', 'setting', 'security', 4),
('auto_save_interval', '30', 'setting', 'general', 5),
('records_per_page', '50', 'setting', 'display', 6),
('date_format', 'DD/MM/YYYY', 'setting', 'general', 7),
('default_language', 'en', 'setting', 'general', 8),

-- Database Paths (CRITICAL - Admin sets these)
('database_path', '', 'path', 'database', 1),
('backup_directory', '', 'path', 'database', 2),
('backup_schedule', 'daily', 'setting', 'backup', 3),
('backup_time', '02:00', 'setting', 'backup', 4),
('backup_retention_days', '30', 'setting', 'backup', 5);

-- Default Dropdown Values - Gender
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, display_order) VALUES
('dropdown_gender_1', 'Ø°ÙƒØ±', 'dropdown', 'gender', 1),
('dropdown_gender_2', 'Ø£Ù†Ø«Ù‰', 'dropdown', 'gender', 2);

-- Default Dropdown Values - ARB Staff
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, display_order) VALUES
('dropdown_arb_staff_1', 'Ù†Ø¹Ù…', 'dropdown', 'arb_staff', 1),
('dropdown_arb_staff_2', 'Ù„Ø§', 'dropdown', 'arb_staff', 2);

-- Default Dropdown Values - Paper or Automated
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, display_order) VALUES
('dropdown_paper_automated_1', 'ÙˆØ±Ù‚ÙŠ', 'dropdown', 'paper_or_automated', 1),
('dropdown_paper_automated_2', 'Ø¢Ù„ÙŠ', 'dropdown', 'paper_or_automated', 2);

-- Default Dropdown Values - Status
INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, display_order) VALUES
('dropdown_status_1', 'Open', 'dropdown', 'status', 1),
('dropdown_status_2', 'Case Review', 'dropdown', 'status', 2),
('dropdown_status_3', 'Under Investigation', 'dropdown', 'status', 3),
('dropdown_status_4', 'Case Validation', 'dropdown', 'status', 4),
('dropdown_status_5', 'Close Case', 'dropdown', 'status', 5),
('dropdown_status_6', 'Closed with STR', 'dropdown', 'status', 6);

-- Default Column Settings (All Report Fields)
INSERT OR IGNORE INTO column_settings (column_name, display_name_en, display_name_ar, data_type, is_visible, is_required, display_order, validation_rules) VALUES
('sn', 'Serial Number', 'Ø§Ù„Ø±Ù‚Ù… Ø§Ù„ØªØ³Ù„Ø³Ù„ÙŠ', 'INTEGER', 1, 1, 1, '{"required": true, "type": "integer", "min": 1}'),
('report_number', 'Report Number', 'Ø±Ù‚Ù… Ø§Ù„ØªÙ‚Ø±ÙŠØ±', 'TEXT', 1, 1, 2, '{"required": true, "pattern": "^\\d{4}/\\d{2}/\\d{3}$", "example": "2025/11/001"}'),
('report_date', 'Report Date', 'ØªØ§Ø±ÙŠØ® Ø§Ù„ØªÙ‚Ø±ÙŠØ±', 'DATE', 1, 1, 3, '{"required": true, "format": "DD/MM/YYYY"}'),
('outgoing_letter_number', 'Outgoing Letter Number', 'Ø±Ù‚Ù… Ø§Ù„Ø®Ø·Ø§Ø¨ Ø§Ù„ØµØ§Ø¯Ø±', 'TEXT', 1, 0, 4, '{"type": "text"}'),
('reported_entity_name', 'Reported Entity Name', 'Ø§Ø³Ù… Ø§Ù„Ø¬Ù‡Ø© Ø§Ù„Ù…Ø¨Ù„Øº Ø¹Ù†Ù‡Ø§', 'TEXT', 1, 1, 5, '{"required": true, "maxLength": 255}'),
('legal_entity_owner', 'Legal Entity Owner', 'Ù…Ø§Ù„Ùƒ Ø§Ù„ÙƒÙŠØ§Ù† Ø§Ù„Ù‚Ø§Ù†ÙˆÙ†ÙŠ', 'TEXT', 1, 0, 6, '{"maxLength": 255}'),
('gender', 'Gender', 'Ø§Ù„Ø¬Ù†Ø³', 'DROPDOWN', 1, 0, 7, '{"options": ["Ø°ÙƒØ±", "Ø£Ù†Ø«Ù‰"]}'),
('nationality', 'Nationality', 'Ø§Ù„Ø¬Ù†Ø³ÙŠØ©', 'TEXT', 1, 0, 8, '{"maxLength": 100}'),
('id_cr', 'ID/CR', 'Ø±Ù‚Ù… Ø§Ù„Ù‡ÙˆÙŠØ©/Ø§Ù„Ø³Ø¬Ù„ Ø§Ù„ØªØ¬Ø§Ø±ÙŠ', 'TEXT', 1, 0, 9, '{"type": "numeric"}'),
('account_membership', 'Account/Membership', 'Ø±Ù‚Ù… Ø§Ù„Ø­Ø³Ø§Ø¨/Ø§Ù„Ø¹Ø¶ÙˆÙŠØ©', 'TEXT', 1, 0, 10, '{"type": "numeric"}'),
('branch_id', 'Branch ID', 'Ø±Ù‚Ù… Ø§Ù„ÙØ±Ø¹', 'TEXT', 1, 0, 11, '{"type": "integer"}'),
('cic', 'CIC', 'Ø±Ù‚Ù… CIC', 'TEXT', 1, 0, 12, '{"type": "numeric"}'),
('first_reason_for_suspicion', 'First Reason for Suspicion', 'Ø§Ù„Ø³Ø¨Ø¨ Ø§Ù„Ø£ÙˆÙ„ Ù„Ù„Ø§Ø´ØªØ¨Ø§Ù‡', 'TEXT', 1, 0, 13, '{}'),
('second_reason_for_suspicion', 'Second Reason for Suspicion', 'Ø§Ù„Ø³Ø¨Ø¨ Ø§Ù„Ø«Ø§Ù†ÙŠ Ù„Ù„Ø§Ø´ØªØ¨Ø§Ù‡', 'TEXT', 1, 0, 14, '{}'),
('type_of_suspected_transaction', 'Type of Suspected Transaction', 'Ù†ÙˆØ¹ Ø§Ù„Ù…Ø¹Ø§Ù…Ù„Ø© Ø§Ù„Ù…Ø´ØªØ¨Ù‡ Ø¨Ù‡Ø§', 'TEXT', 1, 0, 15, '{}'),
('arb_staff', 'ARB Staff', 'Ù…ÙˆØ¸Ù ARB', 'DROPDOWN', 1, 0, 16, '{"options": ["Ù†Ø¹Ù…", "Ù„Ø§"]}'),
('total_transaction', 'Total Transaction', 'Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù…Ø¹Ø§Ù…Ù„Ø©', 'TEXT', 1, 0, 17, '{"pattern": "^\\d+\\s*SAR$", "example": "605040 SAR"}'),
('report_classification', 'Report Classification', 'ØªØµÙ†ÙŠÙ Ø§Ù„ØªÙ‚Ø±ÙŠØ±', 'TEXT', 1, 0, 18, '{}'),
('report_source', 'Report Source', 'Ù…ØµØ¯Ø± Ø§Ù„ØªÙ‚Ø±ÙŠØ±', 'TEXT', 1, 0, 19, '{}'),
('reporting_entity', 'Reporting Entity', 'Ø§Ù„Ø¬Ù‡Ø© Ø§Ù„Ù…Ø¨Ù„ØºØ©', 'TEXT', 1, 0, 20, '{}'),
('paper_or_automated', 'Paper or Automated', 'ÙˆØ±Ù‚ÙŠ Ø£Ùˆ Ø¢Ù„ÙŠ', 'DROPDOWN', 1, 0, 21, '{"options": ["ÙˆØ±Ù‚ÙŠ", "Ø¢Ù„ÙŠ"]}'),
('reporter_initials', 'Reporter Initials', 'Ø£Ø­Ø±Ù Ø§Ù„Ù…Ø¨Ù„Øº', 'TEXT', 1, 0, 22, '{"pattern": "^[A-Z]{2}$", "maxLength": 2}'),
('sending_date', 'Sending Date', 'ØªØ§Ø±ÙŠØ® Ø§Ù„Ø¥Ø±Ø³Ø§Ù„', 'DATE', 1, 0, 23, '{"format": "DD/MM/YYYY"}'),
('original_copy_confirmation', 'Original Copy Confirmation', 'ØªØ£ÙƒÙŠØ¯ Ø§Ù„Ù†Ø³Ø®Ø© Ø§Ù„Ø£ØµÙ„ÙŠØ©', 'TEXT', 1, 0, 24, '{}'),
('fiu_number', 'FIU Number', 'Ø±Ù‚Ù… FIU', 'TEXT', 1, 0, 25, '{"type": "integer"}'),
('fiu_letter_receive_date', 'FIU Letter Receive Date', 'ØªØ§Ø±ÙŠØ® Ø§Ø³ØªÙ„Ø§Ù… Ø®Ø·Ø§Ø¨ FIU', 'DATE', 1, 0, 26, '{"format": "DD/MM/YYYY"}'),
('fiu_feedback', 'FIU Feedback', 'Ù…Ù„Ø§Ø­Ø¸Ø§Øª FIU', 'TEXT', 1, 0, 27, '{}'),
('fiu_letter_number', 'FIU Letter Number', 'Ø±Ù‚Ù… Ø®Ø·Ø§Ø¨ FIU', 'TEXT', 1, 0, 28, '{"type": "integer"}'),
('fiu_date', 'FIU Date', 'ØªØ§Ø±ÙŠØ® FIU', 'DATE', 1, 0, 29, '{"format": "DD/MM/YYYY"}'),
('status', 'Status', 'Ø§Ù„Ø­Ø§Ù„Ø©', 'DROPDOWN', 1, 1, 30, '{"required": true, "options": ["Open", "Case Review", "Under Investigation", "Case Validation", "Close Case", "Closed with STR"]}');

-- Default Dashboard Widgets (Examples for Admin to customize)
INSERT OR IGNORE INTO dashboard_config (widget_type, title, title_ar, sql_query, position_row, position_col, width, color, icon, visible_to_roles, is_active, display_order, created_by) VALUES
('kpi_card', 'Total Reports', 'Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ±', 'SELECT COUNT(*) as value FROM reports WHERE is_deleted = 0', 0, 0, 3, '#3b82f6', 'file-text', 'admin,reporter', 1, 1, 'SYSTEM'),
('kpi_card', 'Open Reports', 'Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ± Ø§Ù„Ù…ÙØªÙˆØ­Ø©', 'SELECT COUNT(*) as value FROM reports WHERE status = ''Open'' AND is_deleted = 0', 0, 3, 3, '#10b981', 'folder-open', 'admin,reporter', 1, 2, 'SYSTEM'),
('kpi_card', 'Under Investigation', 'Ù‚ÙŠØ¯ Ø§Ù„ØªØ­Ù‚ÙŠÙ‚', 'SELECT COUNT(*) as value FROM reports WHERE status = ''Under Investigation'' AND is_deleted = 0', 0, 6, 3, '#f59e0b', 'search', 'admin,reporter', 1, 3, 'SYSTEM'),
('kpi_card', 'Closed Cases', 'Ø­Ø§Ù„Ø§Øª Ù…ØºÙ„Ù‚Ø©', 'SELECT COUNT(*) as value FROM reports WHERE status IN (''Close Case'', ''Closed with STR'') AND is_deleted = 0', 0, 9, 3, '#ef4444', 'check-circle', 'admin,reporter', 1, 4, 'SYSTEM'),
('pie_chart', 'Reports by Status', 'Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ± Ø­Ø³Ø¨ Ø§Ù„Ø­Ø§Ù„Ø©', 'SELECT status as label, COUNT(*) as value FROM reports WHERE is_deleted = 0 GROUP BY status', 1, 0, 6, '#8b5cf6', NULL, 'admin,reporter', 1, 5, 'SYSTEM'),
('line_chart', 'Reports by Month', 'Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ± Ø­Ø³Ø¨ Ø§Ù„Ø´Ù‡Ø±', 'SELECT strftime(''%Y-%m'', created_at) as label, COUNT(*) as value FROM reports WHERE is_deleted = 0 AND created_at >= date(''now'', ''-12 months'') GROUP BY strftime(''%Y-%m'', created_at) ORDER BY label', 1, 6, 6, '#06b6d4', NULL, 'admin,reporter', 1, 6, 'SYSTEM');

-- ============================================================================
-- SAMPLE DATA (For Testing and Demo)
-- ============================================================================

-- Sample Users
INSERT OR IGNORE INTO users (username, password, full_name, role, is_active, created_at, created_by) VALUES
('agent1', 'pass123', 'Mohammed Al-Rashid', 'agent', 1, datetime('now'), 'admin'),
('reporter1', 'pass123', 'Sara Al-Khalid', 'reporter', 1, datetime('now'), 'admin');

-- Sample Reports
INSERT OR IGNORE INTO reports (
    sn, report_number, report_date, outgoing_letter_number, reported_entity_name,
    legal_entity_owner, gender, nationality, id_cr, account_membership,
    branch_id, cic, first_reason_for_suspicion, second_reason_for_suspicion,
    type_of_suspected_transaction, arb_staff, total_transaction, report_classification,
    report_source, reporting_entity, paper_or_automated, reporter_initials,
    sending_date, original_copy_confirmation, fiu_number, fiu_letter_receive_date,
    fiu_feedback, fiu_letter_number, fiu_date, status, created_by
) VALUES
(1, '2025/11/001', '04/11/2025', '3333', 'Example Financial Entity', 
 'Owner Name', 'Ø°ÙƒØ±', 'Saudi Arabian', '1122334455', '606051234567', 
 '55', '22554411', 'Suspicious transaction patterns detected during review period',
 'Potential fraud and deception indicators', 'Internal Transfers', 'Ù„Ø§', '605040 SAR',
 'Crime', 'INCIDENT REPORT', 'Compliance Department', 'Ø¢Ù„ÙŠ', 'ZM',
 '04/11/2025', 'CONFIRMED', '416158', '04/11/2025',
 'Entity added to database for monitoring', '5040', '04/11/2025',
 'Open', 'admin'),
(2, '2025/11/002', '04/11/2025', '3334', 'Second Entity Example', 
 'Second Owner', 'Ø£Ù†Ø«Ù‰', 'Egyptian', '2233445566', '606051234568', 
 '56', '22554412', 'Unusual cash deposit patterns', 'Large transactions without clear business purpose', 
 'Cash Deposits', 'Ù†Ø¹Ù…', '1250000 SAR', 'Crime', 'INCIDENT REPORT', 
 'Branch Compliance', 'ÙˆØ±Ù‚ÙŠ', 'AK', '04/11/2025', 'PENDING', '416159', 
 '04/11/2025', 'Under review', '5041', '04/11/2025', 'Case Review', 'agent1');

-- ============================================================================
-- VIEWS (For Reporting and Analytics)
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_active_reports AS
SELECT * FROM reports WHERE is_deleted = 0;

CREATE VIEW IF NOT EXISTS v_reports_with_history AS
SELECT 
    r.*,
    COUNT(DISTINCT ch.change_id) as change_count,
    MAX(ch.changed_at) as last_modified
FROM reports r
LEFT JOIN change_history ch ON r.report_id = ch.record_id AND ch.table_name = 'reports'
WHERE r.is_deleted = 0
GROUP BY r.report_id;

CREATE VIEW IF NOT EXISTS v_user_activity AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    u.role,
    u.last_login,
    COUNT(DISTINCT r.report_id) as reports_created,
    COUNT(DISTINCT ch.change_id) as changes_made
FROM users u
LEFT JOIN reports r ON u.username = r.created_by
LEFT JOIN change_history ch ON u.username = ch.changed_by
WHERE u.is_active = 1
GROUP BY u.user_id;

-- ============================================================================
-- TRIGGERS (Automatic Change Tracking)
-- ============================================================================

-- Trigger: Log report status changes
CREATE TRIGGER IF NOT EXISTS trg_reports_status_change
AFTER UPDATE OF status ON reports
FOR EACH ROW
WHEN OLD.status != NEW.status
BEGIN
    INSERT INTO status_history (report_id, from_status, to_status, changed_by, changed_at)
    VALUES (NEW.report_id, OLD.status, NEW.status, NEW.updated_by, NEW.updated_at);
    
    INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, changed_by, changed_at)
    VALUES ('reports', NEW.report_id, 'status', OLD.status, NEW.status, 'STATUS_CHANGE', NEW.updated_by, NEW.updated_at);
END;

-- Trigger: Log report deletion (soft delete)
CREATE TRIGGER IF NOT EXISTS trg_reports_soft_delete
AFTER UPDATE OF is_deleted ON reports
FOR EACH ROW
WHEN NEW.is_deleted = 1 AND OLD.is_deleted = 0
BEGIN
    INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, changed_by, changed_at)
    VALUES ('reports', NEW.report_id, 'is_deleted', '0', '1', 'DELETE', NEW.updated_by, NEW.updated_at);
END;

-- Trigger: Log report restoration (reopen)
CREATE TRIGGER IF NOT EXISTS trg_reports_reopen
AFTER UPDATE OF is_deleted ON reports
FOR EACH ROW
WHEN NEW.is_deleted = 0 AND OLD.is_deleted = 1
BEGIN
    INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, changed_by, changed_at)
    VALUES ('reports', NEW.report_id, 'is_deleted', '1', '0', 'REOPEN', NEW.updated_by, NEW.updated_at);
END;

-- ============================================================================
-- DATABASE VALIDATION QUERIES (Used by Python application on startup)
-- ============================================================================

-- Check schema version
-- SELECT value FROM system_metadata WHERE key = 'schema_version';

-- Verify all required tables exist
-- SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Count critical records
-- SELECT 
--     (SELECT COUNT(*) FROM users WHERE role = 'admin') as admin_count,
--     (SELECT COUNT(*) FROM system_config) as config_count,
--     (SELECT COUNT(*) FROM column_settings) as column_count,
--     (SELECT COUNT(*) FROM dashboard_config) as dashboard_count;

-- ============================================================================
-- END OF DATABASE SCHEMA
-- ============================================================================

-- Notes:
-- 1. This schema is designed for SQLite3 with WAL mode enabled
-- 2. All timestamps use ISO8601 format
-- 3. Foreign keys are enabled in Python code
-- 4. Indexes are created for frequently queried columns
-- 5. Triggers handle automatic change tracking
-- 6. Views provide convenient data access
-- 7. Dashboard configuration is stored in database for dynamic dashboards
-- 8. System validates database on startup using metadata table
