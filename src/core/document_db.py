import os
import json
import sys
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
import datetime
from bson.errors import InvalidId

class DocumentDatabase:
    def __init__(self):
        self.config = self.load_config()
        self.client = None
        self.db = None
        self.fs = None
        self.fallback_storage = []
        self.connect()
        
    def load_config(self):
        """Load MongoDB configuration from JSON file"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            config_path = os.path.join(base_path, "config", "mongodb_config.json")
            
            with open(config_path) as f:
                config = json.load(f)
                print("Loaded MongoDB config:")
                print(f"  Host: {config.get('host', 'localhost')}")
                print(f"  Port: {config.get('port', 27017)}")
                print(f"  Database: {config.get('database', 'document_db')}")
                return config
        except Exception as e:
            print(f"Failed to load MongoDB config: {str(e)}")
            return {
                "host": "localhost",
                "port": 27017,
                "database": "document_db"
            }
            
    def connect(self):
        """Establish MongoDB connection"""
        try:
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 27017)
            self.client = MongoClient(host, port)
            print(f"Connecting to MongoDB at {host}:{port}...")
            
            # Test connection
            self.client.server_info()
            print("MongoDB connection successful!")
            
            # Get database
            db_name = self.config.get("database", "document_db")
            self.db = self.client[db_name]
            self.fs = GridFS(self.db)
            print(f"Using database: {db_name}")

            # Create text index if collection exists
            if "documents" in self.db.list_collection_names():
                if "extracted_text_text" not in self.db.documents.index_information():
                    self.db.documents.create_index([("extracted_text", "text")])
                    print("Created text index for search")
            
        except Exception as e:
            print(f"MongoDB connection failed: {str(e)}")
            print("Using in-memory fallback storage for documents")
    
    def insert_document(self, file_name, file_type, content, extracted_text, metadata):
        """Insert a new document with metadata"""
        file_id = None
        try:
            if self.client:
                # Store file content in GridFS
                file_id = self.fs.put(
                    content,
                    filename=file_name,
                    content_type=file_type,
                    metadata=metadata
                )
                document = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "extracted_text": extracted_text,
                    "metadata": metadata,
                    "created_at": datetime.datetime.utcnow()  # Fixed datetime call
                }
                result = self.db.documents.insert_one(document)
                return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error inserting document: {str(e)}")
            # Cleanup orphaned GridFS file if created
            if file_id:
                try:
                    self.fs.delete(file_id)
                    print(f"Deleted orphaned GridFS file: {file_id}")
                except Exception as delete_err:
                    print(f"Failed to delete orphaned file: {str(delete_err)}")
        
        # Fallback to in-memory storage
        print("Using in-memory fallback storage")
        doc_id = len(self.fallback_storage)
        self.fallback_storage.append({
            "id": str(doc_id),
            "file_name": file_name,
            "file_type": file_type,
            "content": content,
            "extracted_text": extracted_text,
            "metadata": metadata,
            "created_at": datetime.datetime.utcnow()  # Add timestamp for consistency
        })
        return str(doc_id)
            
    
    def get_document_text(self, doc_id):
        """Get extracted text from a document"""
        try:
            if self.client:
                document = self.db.documents.find_one({"_id": ObjectId(doc_id)})
                return document["extracted_text"] if document else None
        except (InvalidId, Exception):
            pass

        # Fallback to in-memory storage
        try:
            doc = self.fallback_storage[int(doc_id)]
            return doc["extracted_text"]
        except (IndexError, ValueError):
            return ""
        
    def search_documents(self, search_term):
        """Search documents by content"""
        results = []
        if self.client:
            try:
                # Create text index if it doesn't exist
                if "extracted_text_text" not in self.db.documents.index_information():
                    self.db.documents.create_index([("extracted_text", "text")])
                
                results = self.db.documents.find(
                    {"$text": {"$search": search_term}},
                    {"file_name": 1, "score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})])
                return [(str(doc["_id"]), doc["file_name"]) for doc in results]
            except Exception as e:
                print(f"MongoDB search error: {str(e)}")
        
        # Fallback to simple in-memory search
        for doc in self.fallback_storage:
            if search_term.lower() in doc["extracted_text"].lower():
                results.append((doc["id"], doc["file_name"]))
        return results
    
    def get_all_documents(self):
        """Get all documents metadata"""
        try:
            documents = self.db.documents.find({}, {"file_name": 1, "file_type": 1})
            return [(str(doc["_id"]), doc["file_name"], doc["file_type"]) for doc in documents]
        except Exception as e:
            print(f"Error getting documents: {str(e)}")
            return []
            
    def get_full_document(self, doc_id):
        """Get complete document data"""
        try:
            # First try MongoDB
            if self.client:
                document = self.db.documents.find_one({"_id": ObjectId(doc_id)})
                if not document:
                    return None
                
                try:    
                    # Retrieve file content from GridFS
                    file_content = self.fs.get(document["file_id"]).read()
                except Exception as e:
                    print(f"GridFS error: {str(e)}")
                    return None
                
                return {
                    "id": str(document["_id"]),
                    "file_name": document["file_name"],
                    "file_type": document["file_type"],
                    "content": file_content,
                    "extracted_text": document["extracted_text"],
                    "metadata": document["metadata"]
                }
        
        except Exception as e:
            print(f"Error getting full document: {str(e)}")
        
        # Fallback to in-memory storage
        try:
            doc = self.fallback_storage[int(doc_id)]
            return {
                "id": doc["id"],
                "file_name": doc["file_name"],
                "file_type": doc["file_type"],
                "content": doc["content"],
                "extracted_text": doc["extracted_text"],
                "metadata": doc["metadata"]
            }
        except (IndexError, ValueError):
            return None
        
    def delete_document(self, doc_id):
        """Delete a document by its ID"""
        try:
            if self.client:
                # Convert string to ObjectId
                obj_id = ObjectId(doc_id)
                # First, get the document to find the associated GridFS file_id
                document = self.db.documents.find_one({"_id": obj_id})
                if document:
                    # Delete the GridFS file
                    self.fs.delete(document["file_id"])
                    # Delete the document metadata
                    result = self.db.documents.delete_one({"_id": obj_id})
                    return result.deleted_count > 0
                return False
        except (InvalidId, Exception) as e:
            print(f"Error deleting document from MongoDB: {str(e)}")
        
       # Fallback: delete from in-memory storage
        try:
            index = int(doc_id)
            if 0 <= index < len(self.fallback_storage):
                del self.fallback_storage[index]
                return True
            return False
        except (ValueError, IndexError):
            return False

# Global Document Database Instance
DOC_DB = DocumentDatabase()
