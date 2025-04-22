from database_Ops import DatabaseOperations

# Singleton instance
DATABASE = DatabaseOperations()

                #host=os.getenv("DB_HOST", "db"),
                #user=os.getenv("DB_USER", "root"),
                #password=os.getenv("DB_PASSWORD", "rootpass"),
                #database=os.getenv("DB_NAME", "university")