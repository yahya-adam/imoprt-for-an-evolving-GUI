# Database Transformation GUI

A graphical interface for performing database operations with MySQL integration and plugin support.

## Features

- **Core Operations**:
  - CRUD (Insert/Update/Delete rows)
  - Column management (Add/Rename/Remove/Merge)
  - Conditional updates
  - Batch operations via JSON scripts

- **Plugin System**:
  - Extend functionality with Python plugins
  - Pre-built plugins: Case conversion, batch inserts
  - Auto-loads plugins from `plugins/` directory

- **Import/Export**:
  - CSV/Excel to MySQL table conversion
  - JSON configuration support
  - Schema validation

## Prerequisites

- MySQL Server 8.0+
- Python 3.8+
- Required packages:
  ```bash
  pip install pymysql pandas sqlalchemy tk customtkinter jsonschema
# In database_Ops.py
self.connection = pymysql.connect(
    host="localhost",
    user="root",
    password="your MYSQL password",  # Change to your credentials
    database="database name"   # Create this database first
)
# sturcture of files 
├── core_operations.json       # Core operation definitions
├── database_Ops.py            # Database connection & operations
├── GUI.py                     # Main application window
├── transformManagerDatabase.py# Database singleton
├── plugins/                   # Custom operations
│   └── lowercase_plugin.py    # Sample plugin
├── *.json                     # Operation scripts
# when executing run script
use provided JSON files (i.e., Rename_column.json, delete_column.json, and merge_columns)
# plugins usage
    Place plugins in plugins/ directory
    Available plugins auto-load on startup
    Access plugin buttons on right sidebar
