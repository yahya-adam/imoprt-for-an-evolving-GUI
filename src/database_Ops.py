import pymysql
from tkinter import messagebox
#import os

class DatabaseOperations:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host= "localhost",
                user= "root",
                password= "your database password",
                database= "your database name"        
            )
            self.cursor = self.connection.cursor()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            raise
    # Core operation that all others will use
    def _execute_sql(self, query, params=None, commit=True):
        """Generic SQL execution with error handling"""
        try:
            print(" Executing Query:", query)
            print(" Parameters:", params)
            self.cursor.execute(query, params or ())
            if commit:
                self.connection.commit() # commit only if successful
            return True
        except Exception as e:
            print(" Error :", e)
            self.connection.rollback() # roll back on failure
            messagebox.showerror("Database Error", str(e))
            return False
    def column_exists(self,table_name, column_name):
        self.cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = %s AND column_name = %s", (table_name, column_name))
        return self.cursor.fetchone()[0] > 0

    def get_column_type(self, table_name, column_name):
        """Get the data type of a column in a table."""
        try:
            query = """
                SELECT DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = %s AND COLUMN_NAME = %s
            """
            self.cursor.execute(query, (table_name, column_name))
            result = self.cursor.fetchone()
            if not result:
                raise ValueError(f"Column '{column_name}' not found in table '{table_name}'.")
            return result[0]  # Returns the data type (e.g., 'varchar', 'int')
        except Exception as e:
            print(f"Error getting column type: {e}")
            return None

    # getting metadata of tables
    def get_table_metadata(self, table_name):
        """Get columns, data, and primary key for a table"""
        try:
            # Get columns and primary key
            self.cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns_info = self.cursor.fetchall()
            columns = [col[0] for col in columns_info]
            primary_key = next((col[0] for col in columns_info if col[3] == "PRI"), None)
            # Get table data
            self.cursor.execute(f"SELECT * FROM {table_name}")
            data = self.cursor.fetchall()
            return columns, data, primary_key
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get metadata: {str(e)}")
            return [], [], None
        
    def table_exists(self, table_name):
        """Check if a table exists in the database."""
        self.cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return self.cursor.fetchone() is not None
    
# implementation of Insert, Update, Delete operations
    def dynamic_insert(self, table_name, values_dict):
        """Insert a new row with dynamic columns"""
        columns = ', '.join(values_dict.keys())
        placeholders = ', '.join(['%s'] * len(values_dict))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        return self._execute_sql(query, tuple(values_dict.values()))

    def dynamic_update(self, table_name, pk_column, old_pk_value, updates_dict):
        """Update specific row with dynamic columns"""
        set_clause = ', '.join([f"{col}=%s" for col in updates_dict.keys()])
        query = f"UPDATE `{table_name}` SET {set_clause} WHERE {pk_column}=%s"
        #query = f"UPDATE '{table_name}' SET {set_clause} WHERE {pk_column}=%s"
        params = list(updates_dict.values()) + [old_pk_value]
        return self._execute_sql(query, params)

    def dynamic_delete(self, table_name, pk_column, primary_key_value):
        """Delete a specific row"""
        query = f"DELETE FROM `{table_name}` WHERE {pk_column}=%s"
        #query = f"DELETE FROM '{table_name}' WHERE {pk_column}=%s"
        return self._execute_sql(query, (primary_key_value,))
    
# implementation of rename column, remove column, add column, and merge columns

    def merge_columns(self, table_name, source_columns, new_column):
        for col in source_columns:
            col_type = self.get_column_type(table_name, col)
            if not col_type or "char" not in col_type.lower():  # Covers VARCHAR, CHAR, TEXT, etc.
                raise ValueError(f"Cannot merge non-string column: {col} (type: {col_type})")
        print(f"[DATABASE] Merging {source_columns} into {new_column} in {table_name}")
        """Merge multiple columns into a new column"""
        try:
            if self.column_exists(table_name, new_column):
                messagebox.showerror("Error", f"Column '{new_column}' already exists! Choose a different name.")
                return False
            # First add the new column
            if not self.add_column(table_name, new_column, "VARCHAR(255)"):
                return False
            # Then populate it with merged data
            with self.connection.cursor() as cursor:
                concat_expr = "CONCAT_WS(' ', " + ", ".join([f"`{col}`" for col in source_columns]) + ")"
                query = f"UPDATE `{table_name}` SET `{new_column}` = {concat_expr}"
            return self._execute_sql(query)
        except Exception as e:
            self.connection.rollback()
            # Cleanup if merge failed
            if self.column_exists(table_name, new_column):
                self.remove_column(table_name, new_column)
            messagebox.showerror("Merge Error", str(e))
            return False

    def add_column(self, table_name, column_name, data_type="VARCHAR(255)"):
        """Add a new column to a table"""
        try:
            if self.column_exists(table_name, column_name):
               messagebox.showerror("Error", f"Column '{column_name}' already exists!")
               return False
            query = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {data_type}"
            return self._execute_sql(query)
        except Exception as e:
            self.connection.rollback()
            messagebox.showerror("Error", f"Add column failed: {str(e)}")
            return False

    def rename_column(self, table_name, old_col_name, new_col_name):
        """Rename an existing column"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}` WHERE Field = %s", (old_col_name,))
            col_info = cursor.fetchone()
            print(col_info)
            if not col_info:
                raise ValueError("Column not found")
            # Build and execute rename query
            query = (f"""ALTER TABLE `{table_name}` CHANGE COLUMN `{old_col_name}`
                      `{new_col_name}` {col_info[1]} 
                       {'NOT NULL' if col_info[2] == 'NO' else ''} 
                       {col_info[4] or ''}""")
            # Clean the query by removing extra whitespace
            query = " ".join(query.split())
            return self._execute_sql(query)
        except Exception as e:
            messagebox.showerror("Rename Error", str(e))
            return False

    def remove_column(self, table_name, column_name):
        """Remove a column from a table"""
        # Check for foreign key constraints first
        self.cursor.execute ("SELECT COUNT(*) " \
        "FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_NAME = %s " \
        "AND COLUMN_NAME = %s " \
        "AND REFERENCED_TABLE_NAME IS NOT NULL",  (table_name, column_name))
        result= self.cursor.fetchone()
        if result and result[0] > 0:
            messagebox.showerror("Error", "Column is referenced in foreign key constraints!")
            return False

        query = f"ALTER TABLE `{table_name}` DROP COLUMN `{column_name}`"
        return self._execute_sql(query)
# Conditional update
    def conditional_update(self, table_name, conditions, updates):
        """Update rows based on conditions"""
        try:
            if not conditions or not updates:
                raise ValueError("Both conditions and updates must be provided")
            set_parts = [] # Update fields
            where_parts = [] # Condition fields
            for col in updates:
                set_parts.append(f"`{col}` = %s")
            for col in conditions:
                where_parts.append(f"`{col}` = %s")     
            query = (f"UPDATE `{table_name}` " f"SET {', '.join(set_parts)} "
                      f"WHERE {' AND '.join(where_parts)}")
            params = list(updates.values()) + list(conditions.values())
            
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise e
    

    

        