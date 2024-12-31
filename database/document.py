from datetime import datetime
from typing import Optional, List
from pymongo import MongoClient
from bson import ObjectId
from config import settings
from models.document import LoanDocument

class LoanDocumentStore:
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGO_DATABASE]
        self.documents = self.db.documents

    def store_document(self, document: LoanDocument) -> bool:
        document.created_at = datetime.utcnow()
        result = self.documents.insert_one(document.to_dict())
        return bool(result.inserted_id)

    def get_document_by_id(self, document_id: str) -> Optional[LoanDocument]:
        doc = self.documents.find_one({"document_id": document_id})
        return LoanDocument.from_dict(doc) if doc else None

    def update_document(self, document_id: str, data: dict) -> bool:
        data["updated_at"] = datetime.utcnow()
        result = self.documents.update_one(
            {"document_id": document_id},
            {"$set": data}
        )
        return result.modified_count > 0

    def delete_document(self, document_id: str) -> bool:
        result = self.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "deleted", "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    def find_similar_documents(self, document: LoanDocument) -> List[dict]:
        query = {
            "$and": [
                {"status": "active"},
                {"$or": [
                    {"borrower_name": document.borrower_name},
                    {"property_address": document.property_address},
                    {
                        "$and": [
                            {"loan_amount": document.loan_amount},
                            {"lender_name": document.lender_name}
                        ]
                    }
                ]}
            ]
        }
        return list(self.documents.find(query))

    def search_documents(self, query: str) -> str:
        # Implement vector search or keyword search based on query
        # This is a placeholder - actual implementation would depend on search requirements
        return ""
