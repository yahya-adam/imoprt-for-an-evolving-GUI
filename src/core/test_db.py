
from core.database import DATABASE

if __name__ == "__main__":
    try:
        DATABASE.cursor.execute("SELECT VERSION()")
        version = DATABASE.cursor.fetchone()
        print(f"MySQL Version: {version[0]}")
    except Exception as e:
        print(f"Database error: {e}")
