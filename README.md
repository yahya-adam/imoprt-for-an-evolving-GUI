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
