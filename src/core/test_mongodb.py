from .document_db import DOC_DB

def test_mongodb():
    # Test small document
    test_content = b"This is a test document"
    doc_id = DOC_DB.insert_document(
        "test.txt",
        "text/plain",
        test_content,
        "This is a test document",
        {"test": "metadata"}
    )
    
    if doc_id:
        print(f"Document inserted successfully! ID: {doc_id}")
        # Try to retrieve
        document = DOC_DB.get_full_document(doc_id)
        if document and document["content"] == test_content:
            print("Document retrieval successful!")
        else:
            print("Document retrieval failed")
    else:
        print("Document insertion failed")

if __name__ == "__main__":
    test_mongodb()
