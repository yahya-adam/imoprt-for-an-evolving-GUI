
from core.transformation import DATABASE
from jsonschema import validate, ValidationError
import json
import config
def lowercase_column(table_name, column_name):
    """Convert a column's values to lowercase."""
    # Example SQL: UPDATE `table` SET `column` = LOWER(`column`)
    query = f"UPDATE `{table_name}` SET `{column_name}` = LOWER(`{column_name}`)"
    return DATABASE._execute_sql(query)

def uppercase_column(table_name, column_name):
    """Convert a column's values to uppercase."""
    # Example SQL: UPDATE `table` SET `column` = LOWER(`column`)
    query = f"UPDATE `{table_name}` SET `{column_name}` = UPPER(`{column_name}`)"
    return DATABASE._execute_sql(query)

def insert_batch(table_name, config):
    """Insert multiple rows into a table."""
    # Define the JSON schema for validation
    schema = {
        "type": "object",
        "properties": {
            "operation": {"type": "string"},
            "table_name": {"type": "string"},
            "values_list": {"type": "array"}
        },
        "required": ["values_list"]
    }
    try:
        # Validate the JSON against the schema
        # Validate the CONFIG against the schema, not values_list
        validate(instance=config, schema=schema)
        
        # Extract the values list from config
        values_list = config["values_list"]

        for row in values_list:
            DATABASE.dynamic_insert(table_name, row)
        return True
    except ValidationError as e:
        # Handle schema validation errors
        print(f"JSON validation failed: {e.message}")
        return False
    except json.JSONDecodeError as e:
        # Handle invalid JSON syntax
        print(f"Invalid JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"Batch insert failed: {e}")
        return False 
# Register with TransformManager
def register_plugin(transform_mgr):
    transform_mgr.register("lowercase_column", lowercase_column)
    transform_mgr.register("uppercase_column", uppercase_column)
    transform_mgr.register("insert_batch", insert_batch)


