import sys
import os
import importlib
import tkinter as tk
import re
from tkinter import ttk
from tkinter import messagebox, Listbox, simpledialog
from customtkinter import *
from core.transformation import DATABASE
import pandas as pd
from tkinter import filedialog
from sqlalchemy import create_engine
import json
import magic
from PIL import Image, ImageTk
from core.document_db import DOC_DB



# Replace the existing base_path code with:
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        # Go up two levels: gui -> src -> project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

base_path = get_base_path()
sys.path.append(base_path)
sys.path.append(os.path.join(base_path, "plugins"))

class DynamicTreeview(ttk.Treeview):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.transform_mgr = TransformManager()
        self.app = None
        
        # horizontal and vertical scrollbars of dynamic treeview
        self.vertical_scrollbar = ttk.Scrollbar(parent, orient= VERTICAL, command=self.yview)
        self.horizontal_scrollbar = ttk.Scrollbar(parent, orient= HORIZONTAL, command=self.xview)

        self.config(xscrollcommand=self.horizontal_scrollbar.set)
        self.config(yscrollcommand=self.vertical_scrollbar.set)

        self.vertical_scrollbar.pack(side="right", fill="y" )
        self.horizontal_scrollbar.pack(side="bottom", fill="x")
        self.pack(expand=True, fill="both")
        
        # Initialize other attributes and menus
        self.current_table = None
        self.primary_key = None
        self.context_menu = tk.Menu(self, tearoff=0)
        self.column_menu = tk.Menu(self, tearoff=0)
        self.insert_menu = tk.Menu(self.parent, tearoff=0)

    
    def update_treeview(self, table_name, columns, data, primary_key):
        #bring table's metadata
        self.current_table = table_name
        self.primary_key = primary_key
        self.delete(*self.get_children())
        self["columns"] = columns
        self["show"] = "headings"
        for col in columns:
            self.heading(col, text=col)
            self.column(col, width=200, anchor="center" ,stretch= tk.NO)
        for row in data:
            self.insert("", END, values=row)
        # context menus when right click on row
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Insert", command=self.insertRow)
        self.context_menu.add_command(label="Update", command=self.updateRow)
        self.context_menu.add_command(label="Delete", command=self.deleteRow)
        self.context_menu.add_command(label="Add Column", command=self.add_column_dialog)
        self.context_menu.add_command(label="Conditional Update", command=self.conditionalUpdate)
        self.bind("<Button-3>", self.show_contextMenu)

    def show_context_menu(self, event):
        # Close existing menu before opening a new one 
        if self.context_menu:
            self.context_menu.unpost()
        # Show the menu at the clicked position
        self.context_menu.post(event.x_root, event.y_root)
        # Bind left-click or escape key to close the menu
        self.bind("<Button-1>", self.close_context_menu)
        self.bind("<Escape>", self.close_context_menu)
    
    def close_context_menu(self, event=None):
        if hasattr(self, 'context_menu') and self.context_menu:
            self.context_menu.unpost()
        # Unbind the events to avoid interference
        self.unbind("<Button-1>")
        self.unbind("<Escape>")

    def show_column_menu(self, event):
        # Close any existing menus first
        if hasattr(self, 'column_menu'):
            self.column_menu.unpost()
        # context menus when right click on column name   
        self.column_menu = tk.Menu(self, tearoff=0)
        self.column_menu.add_command(label="Rename Column", command=lambda: self.rename_column)
        self.column_menu.add_command(label="Delete Column", command=lambda: self.deleteColumn)
        self.column_menu.add_command(label="Add Column", command= lambda: self.add_column_dialog)
        # Show the menu and bind close events
        self.column_menu.post(event.x_root, event.y_root)
        self.bind("<Button-1>", self.close_column_menu)
        self.bind("<Escape>", self.close_column_menu)

    def close_column_menu(self, event=None):
        if hasattr(self, 'column_menu') and self.close_column_menu:
            self.column_menu.unpost()
        self.unbind("<Button-1>")
        self.unbind("<Escape>")   

    def show_contextMenu(self, event):
        region = self.identify_region(event.x, event.y)
        if hasattr(self, 'context_menu') and self.close_context_menu:
            self.context_menu.unpost()
        if hasattr(self, 'column_menu') and self.close_column_menu:
            self.column_menu.unpost()
        
        if region == "heading":
            col_id = self.identify_column(event.x)
            col_index = int(col_id[1:]) - 1
            self["columns"][col_index]
            self.show_column_menu(event, col_index)
        
        elif region == "cell":
            row_id = self.identify_row(event.y)
            self.selection_set(row_id)
            self.show_context_menu(event)
        else:
            self.show_insert_menu(event)
          
    def show_context_menu(self, event):
        if self.context_menu:
            self.context_menu.unpost()
        self.context_menu.post(event.x_root, event.y_root)
        self.bind("<Button-1>", self.close_context_menu)
        self.bind("<Escape>", self.close_context_menu)
    def show_column_menu(self, event, col_index):
        if col_index < 0 or col_index >= len(self["columns"]):
            return 
        if hasattr(self, 'column_menu'):
            self.column_menu.unpost()
        self.column_menu = tk.Menu(self, tearoff=0)
        self.column_menu.add_command(label="Rename Column", command=lambda idx=col_index: self.rename_column(idx))
        self.column_menu.add_command(label="Delete Column",command=lambda idx=col_index: self.deleteColumn(idx))
        self.column_menu.add_command(label="Add Column",command=lambda idx=col_index: self.add_column_dialog(idx))
        self.column_menu.post(event.x_root, event.y_root)
        self.bind("<Button-1>", self.close_column_menu)
        self.bind("<Escape>", self.close_column_menu)

    def show_insert_menu(self, event):
        if hasattr(self, 'insert_menu'):
            self.insert_menu.unpost()
        insert_menu = tk.Menu(self.parent, tearoff=0)
        insert_menu.add_command(label="Insert", command=self.insertRow)
        insert_menu.post(event.x_root, event.y_root)
        self.bind("<Button-1>", lambda e: insert_menu.unpost())
        self.bind("<Escape>", lambda e: insert_menu.unpost())
 
    def insertRow(self):
        if not self.primary_key:
         messagebox.showerror("Error", "Table has no primary key defined")
         return
        popup = tk.Toplevel()
        popup.title("Insert New Row")
        entries = []
        for i, col in enumerate(self["columns"]):
            tk.Label(popup, text=col).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(popup)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entries.append(entry)
        # saving data in database
        def save():
            values_dict = {col: entry.get() for col, entry in zip(self["columns"], entries)}
            self.transform_mgr.insert_row(self.current_table, values_dict)
            self.insert("", END, values=list(values_dict.values()))
            popup.destroy()
            messagebox.showinfo("Success", "Row inserted successfully")

        tk.Button(popup, text="Save", command=save).grid(row=len(self["columns"]), columnspan=2)

    def updateRow(self):
        if not self.primary_key:
         messagebox.showerror("Error", "Table has no primary key defined")
         return
        selected = self.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to update")
            return
        old_values = self.item(selected[0], "values")
        pk_index = self["columns"].index(self.primary_key)
        pk_value = old_values[pk_index]
        popup = tk.Toplevel()
        popup.title("Update Row")
        entries = []
        for i, (col, val) in enumerate(zip(self["columns"], old_values)):
            tk.Label(popup, text=col).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(popup)
            entry.insert(0, val)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entries.append(entry)
        # save data in database
        def save():
            updated_values = [entry.get() for entry in entries]
            values_dict = {
                col: val
                for col, val in zip(self["columns"], updated_values)
                if col != self.primary_key
            }
            self.transform_mgr.update_row(self.current_table, self.primary_key,pk_value ,values_dict)
            self.item(selected[0], values=updated_values)
            popup.destroy()
            messagebox.showinfo("Success", "Row updated successfully")

        tk.Button(popup, text="Save", command=save).grid(row=len(self["columns"]), columnspan=2)

    def deleteRow(self):
        selected = self.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a row to delete")
            return
        selected_values = self.item(selected[0], "values")
        pk_index = self["columns"].index(self.primary_key)
        primary_key_value = selected_values[pk_index]

        if messagebox.askyesno("Confirm", "Delete this row?"):
          success = self.transform_mgr.delete_row(
            self.current_table, 
            self.primary_key,  # pk_column
            primary_key_value   # pk_value
        )
          if success:
            self.delete(selected[0])
            messagebox.showinfo("Success", "Record deleted successfully")
          else:
            messagebox.showerror("Error", "Failed to delete record")
    
    def rename_column(self, col_index):
        # Add validation
        if not isinstance(col_index, int):
         messagebox.showerror("Error", "Invalid column index")
         return
        current_col = self["columns"][col_index]
        new_name = simpledialog.askstring("Rename Column", "New name:", initialvalue=current_col)
        # Validate new nam
        if not new_name or not new_name.isidentifier():
         messagebox.showerror("Error", "Invalid column name")
         return
        #if new_name and new_name != current_col:
        if self.transform_mgr.rename_column(self.current_table, current_col, new_name):
                self.app.load_table(self.current_table)

    def display_columns(self):
       # displays columns's names on listbox (assist on merging columns)
        self.cursor = DATABASE.connection.cursor()
        self.cursor.execute(f'SHOW COLUMNS FROM {self.current_table}')
        columns=self.cursor.fetchall()
        self.app.column_list.delete(0, tk.END)
        for col in columns:
            self.app.column_list.insert(tk.END, col[0])
    
    def add_column_dialog(self, col_index):
        self["columns"][col_index] 
        col_name = simpledialog.askstring("New Column", "Column name:")
        col_type = simpledialog.askstring("Data Type", "Format: VARCHAR(n)/INT/DATE", initialvalue="VARCHAR(255)")
        
        valid_patterns = {
        "VARCHAR": r"^VARCHAR\(\d+\)$",  # VARCHAR(255)
        "INT": r"^INT$",                 # INT
        "DATE": r"^DATE$"                # DATE
    }
    
        if not any(re.fullmatch(pattern, col_type.upper()) 
               for pattern in valid_patterns.values()):
          messagebox.showerror("Error", 
            "Invalid format! Valid examples:\n"
            "- VARCHAR(255)\n"
            "- INT\n"
            "- DATE")
          return

        if not col_type: 
           # User cancelled or left empty
          messagebox.showerror("Error", "Data type is required")
          return
        if not col_type.startswith(("VARCHAR", "INT", "DATE")):
          messagebox.showwarning("Warning", "Invalid data type. Use VARCHAR(n), INT, DATE etc.")
          return
        if col_name:
              # FIXED VARIABLE NAME
            if self.transform_mgr.add_column(self.current_table , col_name, col_type):
                  self.app.load_table(self.current_table)
            else:
                messagebox.showerror("Error", "Failed to add column")
               
    def deleteColumn(self, col_index):
        column_name = self["columns"][col_index]
        if messagebox.askyesno("Confirm", f"Delete column '{column_name}'?"):
            if self.transform_mgr.remove_column(self.current_table, column_name):
               self.app.load_table(self.current_table)

    def conditionalUpdate(self):
      selected = self.selection()
      if not selected:
        messagebox.showwarning("Warning", "Select a row to condition")
        return

    # Create condition dialog
      popup = CTkToplevel()
      popup.title("Conditional Update")
      popup.geometry("600x400")  # Set a fixed size for the popup

      # Create a scrollable container
      scrollable_frame = CTkScrollableFrame(popup)
      scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
      scrollable_frame.pack(fill="both", expand=True)
    
    # Condition inputs
      condition_frame = CTkFrame(scrollable_frame)
      condition_frame.pack(fill="x", padx=5, pady=5)
    
    # Update inputs
      update_frame = CTkFrame(scrollable_frame)
      update_frame.pack(fill="x", padx=5, pady=5)
    
    # Condition fields
      conditions = {}
      for i, col in enumerate(self["columns"]):
        CTkLabel(condition_frame, text=f"{col} = ").grid(row=i, column=0)
        entry = CTkEntry(condition_frame)
        entry.grid(row=i, column=1)
        conditions[col] = entry

    # Update fields
      updates = {}
      for i, col in enumerate(self["columns"]):
        CTkLabel(update_frame, text=f"New {col}: ").grid(row=i, column=0)
        entry = CTkEntry(update_frame)
        entry.grid(row=i, column=1)
        updates[col] = entry

      def execute_update():
        cond_values = {k: v.get() for k, v in conditions.items() if v.get()}
        update_values = {k: v.get() for k, v in updates.items() if v.get()}
        
        if not cond_values or not update_values:
            messagebox.showwarning("Input Error", "Both condition and update fields required")
            return   
        try:
            affected_rows = self.transform_mgr.conditional_update(self.current_table, cond_values, update_values)
            messagebox.showinfo("Success", f"Updated {affected_rows} records")
            self.app.load_table(self.current_table)
            popup.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

      CTkButton(popup, text="Execute Update", command=execute_update).pack(pady=10)
      

                
class TransformManager:
    def __init__(self):
        self.operations = {}
        self.load_plugins() # Load plugins automatically
        
        self.register("add_column", self.add_column)
        self.register("rename_column", self.rename_column)
        self.register("remove_column", self.remove_column)
        self.register("conditional_update", self.conditional_update)
        self.register("insert_row", self.insert_row)
        self.register("delete_row", self.delete_row)
        self.register("update_row", self.update_row)
        

    def register(self, name: str, func: callable):
        """Register a new operation with a unique name."""
        self.operations[name] = func

    def execute(self, operation_name, **params):
        """Execute a registered operation by name with given parameters."""
        try:
            func = self.operations[operation_name]
            return func(**params)
        except KeyError:
            messagebox.showerror("Error", f"Unknown operation: {operation_name}")
            return False
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False           

    def load_transformations(self, config_file: str, default_table: str = None):
        # open JSON whereby checks operations and their parameters
        with open(config_file, 'r') as f:
            transformations = json.load(f)
        if not isinstance(transformations, list):
            transformations = [transformations]
        for transform in transformations:
            operation = transform.pop("operation")
            # Inject default table if missing
            if "table_name" not in transform and default_table:
                transform["table_name"] = default_table
            # Validate required parameters
            if "table_name" not in transform:
                raise ValueError("JSON must specify 'table' or a table must be selected in the GUI.")
            self.execute(operation, **transform)           


    def merge_columns(self, table_name, source_columns, new_column):
        """Business logic: Merge columns using the database."""
        try:
            success = DATABASE.merge_columns(table_name, source_columns, new_column)
            return success
        except Exception as e:
            print(f"Merge failed: {e}")
            return False
    
    def insert_row(self, table_name, values_dict):
        """ insert row operation"""
        try:
            succuss=DATABASE.dynamic_insert(table_name, values_dict)
            return succuss
        except Exception as e:
            print(f"row insertion failed: {e}")
            return False

    def rename_column(self, table_name, old_col_name, new_col_name):
        """Rename column operation."""
        try:
            success= DATABASE.rename_column(table_name, old_col_name, new_col_name)
            return success
        except Exception as e:
            print(f"rename of column failed: {e}")
            return False

    #def insert_batch(self, table_name, values_list):
        """Insert multiple rows in one operation."""
        #success = True
        #for values_dict in values_list:
            #if not DATABASE.dynamic_insert(table_name, values_dict):
                #success = False
        #return success
    
    def delete_row(self, table_name, pk_column, primary_key_value):
        """ delete row operation"""
        try:
            success= DATABASE.dynamic_delete(table_name, pk_column, primary_key_value)
            return success
        except Exception  as e:
            print(f" Row deletion failed: {e}")
            return False

    def add_column(self, table_name, column_name, data_type):
        """Add column operation."""
        # Example: Validate column name
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", column_name):
            raise ValueError("Invalid column name!")
        try:
            success= DATABASE.add_column(table_name, column_name, data_type)
            return success
        except Exception as e:
            print(f"Adding column failed: {e}")
            return False

    def update_row(self, table_name, pk_column, old_pk_value, updates_dict):
        """update row operation"""
        try:
            success = DATABASE.dynamic_update(table_name, pk_column, old_pk_value, updates_dict)
            return success
        except Exception as e:
            print(f"Row updation failed: {e}")
            return False
 
    def remove_column(self, table_name, column_name):
        """Remove column operation."""
        try: 
            success = DATABASE.remove_column(table_name, column_name)
            return success
        except Exception as e:
            print(f"Column Removal failed: {e}")
            return False

    def conditional_update(self, table_name, conditions, updates):
        """Conditional update operation."""
        try:
            affected_rows = DATABASE.conditional_update(table_name, conditions, updates)
            return affected_rows
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False

    def load_plugins(self):
        base_path = get_base_path()
        print("\n=== Plugin Loading ===")
        if getattr(sys, 'frozen', False):
        # For frozen app, plugins are in the same directory as executable
            plugin_dir = os.path.join(os.path.dirname(sys.executable), "plugins")
        else:
        # For development, use relative path
            plugin_dir = os.path.join(base_path, "plugins")
        print(f"Looking for plugins in: {plugin_dir}")  # Debug path
        if not os.path.exists(plugin_dir):
            print(f"Error: Directory '{plugin_dir}' not found!")
            # Create empty directory to prevent crashes
            os.makedirs(plugin_dir, exist_ok=True)
            return
        print(f"Found plugins: {os.listdir(plugin_dir)}")
        
        for filename in os.listdir(plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    print(f"\nLoading plugin: {filename}")
                    module = importlib.import_module(f"plugins.{module_name}")
                    if hasattr(module, "register_plugin"):
                        print(f"Registered operations from {filename}:")
                        module.register_plugin(self)
                        print(f"   - {list(self.operations.keys())}")
                    else:
                        print(f"No register_plugin() in {filename}")
                except Exception as e:
                    print(f" Plugin {filename} failed: {str(e)}")

class App:
    def __init__(self, root, dataViewFrame): # Add dataViewFrame parameter
        self.root = root
        self.tree = DynamicTreeview(dataViewFrame)
        self.tree.app= self
        self.table_var = tk.StringVar()
        self.transform_mgr = TransformManager()
        self.core_operations = self.load_config("core_operations.json")
        self._register_transformations()
        self._add_plugin_buttons()
        self.create_document_frame()
        
    def _register_transformations(self):
        """Register all transformation operations with the TransformManager."""
        self.transform_mgr.register("merge_columns", self.transform_mgr.merge_columns)
        
    # Main widgets
        self.import_btn = CTkButton(self.root, text="Import Dataset", command=self.import_dataset) 
        self.import_btn.pack(fill= "none", expand= None,padx=5 ,pady=10, anchor= "sw")

        self.script_btn = CTkButton(self.root, text="Run Script", command=self.run_script)
        self.script_btn.pack(fill= None, expand= None,padx=5 ,pady=10, anchor= "sw")

        self.table_selector = ttk.Combobox(self.root, textvariable=self.table_var, state="readonly")
        self.table_selector.pack(fill= None, expand= None, padx=10 ,pady= 10, anchor="nw", before= self.import_btn)
        self.table_selector.bind("<<ComboboxSelected>>", self.load_table)
    
        self.column_list = Listbox(self.root, width=100, height=7, selectmode=MULTIPLE)
        self.column_list.pack(fill="none", expand= None, padx=5, ipadx= 10, anchor= "w")

        self.merge_btn = CTkButton(self.root, text="Merge Columns", command=self.merge_columns)
        self.merge_btn .pack(fill="none", expand= None, padx=5,pady= 20, anchor= "w")
        self.tables = self.get_table_list()
        self.table_selector["values"] = self.tables
 
    def load_config(self, filename):
        try:
            base_path = get_base_path()
            # script_dir = base_path
            config_path = os.path.join(base_path, "config", filename)
            # Check if file exists
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"'{filename}' not found in directory: {base_path}")
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            # Check if "core_operations" key exists
            if "core_operations" not in config_data:
                raise KeyError(f"Key 'core_operations' missing in {filename}")
            return config_data["core_operations"]
            
        except Exception as e:
            messagebox.showerror("Config Error", str(e))
            return []  # Fallback to empty list

    def _add_plugin_buttons(self):
        # Load core operations from JSON instead of hardcoding
        self.core_operations = self.load_config("core_operations.json")
        print("[DEBUG] Core operations:", self.core_operations)
        print("[DEBUG] Plugin buttons being created for:", self.transform_mgr.operations.keys())
        y_position = 200
        # plugin_frame = CTkFrame(self.root)  # Create dedicated frame
        # plugin_frame.pack(side="right", fill="y", padx=10, pady=10)

        for op_name in self.transform_mgr.operations:
            # Skip core operations
            if op_name in self.core_operations:
                continue  # Do not create a button for these
            if op_name == "insert_batch":
            # Special handling for insert_batch
                btn = CTkButton(
                    self.root,
                    text=op_name,
                    command=lambda op=op_name: self.run_insert_batch(op)
                )
            # Handler for plugins needing column_name (e.g., lowercase_column)
            elif op_name in ["lowercase_column", "uppercase_column"]:
                btn = CTkButton(
                self.root,
                text=op_name,
                command=lambda op=op_name: self.run_generic_plugin(op)
            )
            else:
                # Default handling (e.g., lowercase_column)
                btn = CTkButton(
                    self.root,
                    text=op_name,
                    command=lambda op=op_name: self.run_generic_plugin(op)
                ) 
            # Create buttons only for plugin operations
            #btn = CTkButton(root, text=op_name, command=lambda op=op_name: self.run_plugin(op))
            btn.place(x=900, y=y_position)
            y_position += 40

    def run_generic_plugin(self, operation_name):
        """For plugins like lowercase_column that need a single input."""
        # Example: Ask for a column name
        column_name = simpledialog.askstring("Input", f"Enter column name:")
        if column_name:
            self.transform_mgr.execute(
                operation_name,
                table_name=self.table_var.get(),
                column_name=column_name
            )
            self.refresh_data()

    def run_insert_batch(self, operation_name): 
        """Special handler for insert_batch."""
        current_table = self.table_var.get()
        if not current_table:
            messagebox.showerror("Error", "Select a table first!")
            return
        # Open a JSON file dialog to get values_list
        file_path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
                # values_list = config.get("values_list", [])
            # Execute the plugin
            success = self.transform_mgr.execute(
                operation_name,
                table_name=current_table,
                config=config
            )
            if success:
                self.refresh_data()
                messagebox.showinfo("Success", "Batch data inserted!")
            else:
                messagebox.showerror("Error", "Batch insert failed.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_plugin(self, operation_name):
        current_table = self.table_var.get()
        if not current_table:
            messagebox.showerror("Error", "Select a table first!")
            return
        # New: Get the column name from the user
        if operation_name in ["lowercase_column", "uppercase_column"]:
            column_name = simpledialog.askstring("Input", f"Enter column name to {operation_name}:")
            if not column_name:
                return  # User cancelled
            self.transform_mgr.execute(operation_name, table_name=current_table, column_name=column_name)
        else:
            self.transform_mgr.execute(operation_name, table_name=current_table)
        self.refresh_data()

    def run_script(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not file_path:
           return
        current_table = self.table_var.get()
        if not current_table:
            messagebox.showerror("Error", "No table selected in the GUI!")
            return
        self.transform_mgr.load_transformations(file_path, default_table=current_table)
        self.refresh_data()
    
    def import_dataset(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("Excel", "*.xls")])
        if not file_path:
            return

        try:
        # Read file
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

        # Generate table name
            base_name = os.path.basename(file_path).split('.')[0]
            table_name = re.sub(r"[^a-zA-Z0-9_]", "", base_name)
            table_name = table_name.strip("_") or "new_table"

        # Process columns
            sanitized_columns = []
            for idx, (col, dtype) in enumerate(df.dtypes.items()):
                sanitized_col = re.sub(r"[^a-zA-Z0-9_]", "", col)
                sanitized_col = sanitized_col.strip("_") or f"col_{idx}"
                
            
            # Data type detection
                if pd.api.types.is_datetime64_any_dtype(dtype):
                    sql_type = "DATETIME"
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                elif "int" in str(dtype):
                    sql_type = "INT"
                elif "float" in str(dtype):
                    sql_type = "FLOAT"
                elif "object" in str(dtype):
                    sql_type = "VARCHAR(255)"
                elif "bool" in str(dtype):
                    sql_type = "BOOLEAN"
                else:
                    sql_type = "VARCHAR(255)"
            
                sanitized_columns.append(f"`{sanitized_col}` {sql_type}")

        # Add primary key
            sanitized_columns.append("`id` INT AUTO_INCREMENT PRIMARY KEY")
            create_table_query = f"CREATE TABLE `{table_name}` ({', '.join(sanitized_columns)})"
            print("Generated Query:", create_table_query)

        # Handle table conflicts
            original_table_name = table_name
            if DATABASE.table_exists(original_table_name):
                new_name = simpledialog.askstring("Conflict", f"Table '{original_table_name}' exists. New name:")
                if new_name:
                    table_name = new_name
                else:
                    return
    

        # Create table
            DATABASE._execute_sql(f"DROP TABLE IF EXISTS `{original_table_name}`", commit=True)
            success = DATABASE._execute_sql(create_table_query, commit=True)
            if not success:
                raise Exception("Failed to create table")

        # Bulk insert
            # Use base_path to find credentials config:
            base_path = get_base_path()
            config_path = os.path.join(base_path, "config", "mysql_config.json")
            with open(config_path) as f:
                db_config = json.load(f)
            connection_string = (
                f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}/{db_config['database']}"
            )
            engine = create_engine(connection_string)
            df.to_sql(name=table_name, con=engine, if_exists="append", index=False)

            # engine = create_engine("mysql+pymysql://root:itfm_1234@localhost/university")
            # df.to_sql(name=table_name,con=engine,if_exists="append",index=False )
            #DATABASE.connection.close()
            #DATABASE.connect()
        # Refresh GUI
            self.tables = self.get_table_list()
            self.table_selector["values"] = self.tables
            #self.table_var.set(table_name)
            #self.load_table()
            messagebox.showinfo("Success", f"Imported '{table_name}' successfully!")

        except Exception as e:
            error_msg = f"Line {sys.exc_info()[-1].tb_lineno}: {str(e)}"
            messagebox.showerror("Import Error", error_msg)
            DATABASE.connection.rollback()

    def refresh_data(self):
      self.load_table()
      self.tree.update_treeview(self.tree.current_table, *DATABASE.get_table_metadata(self.tree.current_table))

    def get_table_list(self):
        self.cursor =DATABASE.connection.cursor()
        self.cursor.execute("SHOW TABLES")
        tables = [table[0] for table in self.cursor.fetchall()]
        return tables

    def load_table(self, event=None, table_name= None):
        # Force full reload
        if table_name is None:
           if event is not None:
              table_name = self.table_var.get()
           else:
              table_name = self.tree.current_table if hasattr(self.tree, 'current_table') else None
        if hasattr(self.tree, 'current_table'):
          prev_table = self.tree.current_table
        else:
          prev_table = None
        self.tree.current_table = None
        table_name = self.table_var.get() if event else prev_table
        columns, data, pk = DATABASE.get_table_metadata(table_name)
        if not pk: return
        self.tree.update_treeview(table_name, columns, data, pk)
        self.column_list.delete(0, tk.END)
        for col in columns:
            self.column_list.insert(tk.END, col)
            
    def merge_columns(self):
        selected = self.column_list.curselection()
        if len(selected) < 2:
            messagebox.showwarning("Warning", "Select at least 2 columns!")
            return
        cols_to_merge = [self.column_list.get(i) for i in selected]
        new_name = simpledialog.askstring("Merge Columns", "New column name:")
        current_columns = [self.column_list.get(i) for i in range(self.column_list.size())]
        if new_name in current_columns:
          messagebox.showerror("Error", "Column name already exists in this table!")
          return
        if not new_name: return
        #Delegate to TransformManager
        success = self.transform_mgr.merge_columns(self.table_var.get(), source_columns= cols_to_merge, new_column= new_name)
        #  Refresh the GUI if successful
        if success:
            self.refresh_data()
        else:
            messagebox.showerror("Error", "Merge failed!")


    def create_document_frame(self):
        """Create UI elements for document management"""
        self.doc_frame = CTkFrame(self.root)
        self.doc_frame.pack(fill="x", padx=10, pady=10, expand=False)
        
        # Upload section
        upload_frame = CTkFrame(self.doc_frame)
        upload_frame.pack(fill="x", pady=5)
        
        CTkButton(upload_frame, text="📄 Upload Document", 
                 command=self.upload_document, width=150).pack(side="left", padx=5)
        
        # Search section
        search_frame = CTkFrame(self.doc_frame)
        search_frame.pack(fill="x", pady=5)
        
        self.search_entry = CTkEntry(search_frame, placeholder_text="Search document content...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        CTkButton(search_frame, text="🔍 Search", width=80,
                 command=self.search_documents).pack(side="left", padx=5)
        
        # Document list and preview
        list_preview_frame = CTkFrame(self.doc_frame)
        list_preview_frame.pack(fill="both", expand=True, pady=5)
        
        self.doc_list = CTkScrollableFrame(list_preview_frame, width=450)
        self.doc_list.pack(side="left", fill="y", padx=5)
        
        self.doc_preview = CTkTextbox(list_preview_frame, wrap="word")
        self.doc_preview.pack(side="left", fill="both", expand=True, padx=5)
        self.doc_preview.configure(state="disabled")  # Make read-only
        
        self.refresh_document_list()
        
    def upload_document(self):
        file_types = [
            ("Documents", "*.pdf *.docx *.doc"),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.docx *.doc *.DOC"),
            ("All Files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if not file_path:
            return
        
        # NEW: Check for duplicate filename
        file_name = os.path.basename(file_path)
        existing_docs = DOC_DB.get_all_documents()
        existing_filenames = [doc[1] for doc in existing_docs]  # [1] is filename 
        
        if file_name in existing_filenames:
            if not messagebox.askyesno("Duplicate File", 
                                      f"'{file_name}' already exists. Overwrite?"):
                return 
            
        # Process file
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        from file_processor import validate_file
        validate_file(file_bytes, os.path.basename(file_path))
        from file_processor import extract_text, get_file_metadata
            
        text = extract_text(file_bytes, os.path.basename(file_path))
        metadata = get_file_metadata(file_bytes, os.path.basename(file_path))
        file_name = os.path.basename(file_path)
        file_type = magic.from_buffer(file_bytes, mime=True)
            
            # Save to database
        doc_id = DOC_DB.insert_document(
            file_name, 
            file_type, 
            file_bytes, 
            text, 
            metadata
        )
        if doc_id:
            messagebox.showinfo("Success", "Document uploaded successfully!")
            self.refresh_document_list()
        else:
            messagebox.showerror("Error", "Failed to save document to database")
    
    def refresh_document_list(self):
        """Populate document list from database"""
        # Clear existing widgets
        for widget in self.doc_list.winfo_children():
            widget.destroy()
            
        # Fetch documents
        documents = DOC_DB.get_all_documents()
        
        if not documents:
            CTkLabel(self.doc_list, text="No documents uploaded").pack(pady=10)
            return
            
        for doc in documents:
            doc_id, file_name, file_type = doc
            frame = CTkFrame(self.doc_list)
            frame.pack(fill="x", pady=2)
           # Create a clickable label for the document name
            label = CTkLabel(
                frame, 
                text=file_name,
                cursor="hand2",
                anchor="w"
            )
            label.pack(side="left", fill="x", expand=True, padx=5)
        
            # Bind left-click to show document
            label.bind("<Button-1>", lambda e, id=doc_id: self.show_document(id))
        
            # Bind right-click to context menu
            label.bind("<Button-3>", lambda e, id=doc_id: self.show_doc_context_menu(e, id))

            CTkButton(
                frame,
                text="📄",  # Document icon
                command=lambda id=doc_id: self.show_document_viewer(id),
                width=60
            ).pack(side="right" , padx=5)
  

    def show_document(self, doc_id):
        """Show document content in preview pane"""
        try:
            text = DOC_DB.get_document_text(doc_id)
            self.doc_preview.configure(state="normal")
            self.doc_preview.delete("1.0", "end")
            self.doc_preview.insert("1.0", text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load document: {str(e)}")
            self.doc_preview.insert("1.0", "Document content not available")
        finally:
            self.doc_preview.configure(state="disabled")
       
    def search_documents(self):
        """Search documents by content"""
        search_term = self.search_entry.get().strip()
        if not search_term:
            messagebox.showwarning("Search", "Please enter a search term")
            return
        try:    
            results = DOC_DB.search_documents(search_term)
            self.doc_preview.configure(state="normal")
            self.doc_preview.delete("1.0", "end")
        
            if not results:
                self.doc_preview.insert("1.0", "No documents found matching your search")
                return
            
            self.doc_preview.insert("1.0", f"Found {len(results)} documents:\n\n")
            for doc in results:
                doc_id, file_name = doc
                self.doc_preview.insert("end", f"- {file_name} (ID: {doc_id})\n")
        except Exception as e:
            messagebox.showerror("Search Error", f"Search failed: {str(e)}")
        finally:
            self.doc_preview.configure(state="disabled")
    

    def show_document_viewer(self, doc_id):
        """Open document in dedicated viewer window"""
        document = DOC_DB.get_full_document(doc_id)
        if not document:
            return
    
        viewer = CTkToplevel(self.root)
        viewer.title(f"Document Viewer - {document['file_name']}")
        viewer.geometry("800x600")
    
        # Main container using grid for better layout control
        viewer.grid_columnconfigure(0, weight=1)
        viewer.grid_rowconfigure(1, weight=1)
    
        # Metadata panel - top section
        meta_frame = CTkFrame(viewer)
        meta_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
    
        # Display metadata in a grid
        row = 0
        for key, value in document['metadata'].items():
            CTkLabel(meta_frame, text=f"{key}:", anchor="e").grid(row=row, column=0, sticky="e", padx=5, pady=2)
            CTkLabel(meta_frame, text=str(value), anchor="w").grid(row=row, column=1, sticky="w", padx=5, pady=2)
            row += 1
    
        # Text content - middle section
        text_frame = CTkFrame(viewer)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)
    
        text_widget = CTkTextbox(text_frame, wrap="word")
        text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        text_widget.insert("1.0", document['extracted_text'])
        text_widget.configure(state="disabled")
    
        # Button frame - bottom section
        button_frame = CTkFrame(viewer)
        button_frame.grid(row=2, column=0, sticky="sew", padx=10, pady=10)
        button_frame.grid_columnconfigure(1, weight=1)
    
        # Make the window modal
        viewer.grab_set()
        viewer.transient(self.root)
        viewer.wait_window()

    
    def show_doc_context_menu(self, event, doc_id):
        #Show context menu for document with download option
        menu = tk.Menu(self.root, tearoff=0)
    
    # Get document name for the menu
        document = DOC_DB.get_full_document(doc_id)
        doc_name = document['file_name'] if document else f"Document {doc_id}"
        
        menu.add_command(
            label=f"Download {doc_name}",
            command=lambda: self.download_document(doc_id, doc_name)
        )
        menu.add_separator()
        menu.add_command(
            label="View Content",
            command=lambda: self.show_document(doc_id)
        )
        menu.add_command(
            label="Open Viewer",
            command=lambda: self.show_document_viewer(doc_id)
        )
        menu.add_separator()
        menu.add_command(
            label="Delete",
            command=lambda: self.delete_document(doc_id)
        )

        menu.tk_popup(event.x_root, event.y_root)

    def delete_document(self, doc_id):
        #Delete document from database"""
        if messagebox.askyesno("Confirm Delete", "Permanently delete this document?"):
            if DOC_DB.delete_document(doc_id):
                self.refresh_document_list()
                self.doc_preview.configure(state="normal")
                self.doc_preview.delete("1.0", "end")
                self.doc_preview.configure(state="disabled")
                messagebox.showinfo("Success", "Document deleted")
            else:
                messagebox.showerror("Error", "Failed to delete document")
        
    
    def download_document(self, doc_id, filename):
        document = DOC_DB.get_full_document(doc_id)
        if not document:
            return
        # Get filename if not provided
        if not filename:
            filename = document['file_name']

        # Get the file extension from the original filename
        file_ext = os.path.splitext(filename)[1][1:]  # Get extension without dot
        if not file_ext:
            # Default extensions based on file type
            if "pdf" in document[2].lower():
                file_ext = "pdf"
            elif "word" in document[2].lower():
                file_ext = "docx"
            else:
                file_ext = "bin"

        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            initialfile=filename,
            defaultextension=f".{file_ext}",
            filetypes=[(f"{file_ext.upper()} files", f"*.{file_ext}"), ("All files", "*.*")]
        )

        if not save_path:
            return
        try:
            with open(save_path, "wb") as f:
                f.write(document["content"])  # content is at index 3
            messagebox.showinfo("Success", "Document downloaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save document: {str(e)}")

def main():
    root = CTk()
    root.geometry('1000x500+100+100')
    root.title("User Graphical Interface")

    dataViewFrame = CTkFrame(root)
    dataViewFrame.pack(expand=True, fill='both', padx=10, pady=10)

    app = App(root,dataViewFrame)
    root.mainloop()

if __name__ == "__main__":
    main()



    

    
