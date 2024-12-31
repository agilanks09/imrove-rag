from fastapi import APIRouter, File, Header, UploadFile, HTTPException, Form
from typing import Optional
import uuid
import logging
from pydantic import BaseModel
from time import perf_counter

from config import settings
from llm.xai_handler import XAIHandler
from utils.processor import DocumentProcessor
from database.redis import RedisHandler
from database.chat import ChatStore
from database.document import LoanDocumentStore
from models.document import LoanDocument
from utils.jwt import JWT
from utils.timing import timer

# Initialize router and shared instances
router = APIRouter(
    prefix="/",
    tags=["Upload"],
)

# Initialize services
llm = XAIHandler(settings.XAI_API_KEY)
doc_processor = DocumentProcessor()
redis_handler = RedisHandler(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD
)
chat_store = ChatStore()
loan_store = LoanDocumentStore()
jwt = JWT(settings.JWT_SECRET_KEY, "HS256")

# Setup logging
logger = logging.getLogger(__name__)

# Define request models
class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context_type: str = "both"

# Upload document endpoint
@router.post("/upload")
@timer
async def upload_document(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None)
):
    user_id = jwt.decode_token(authorization)["sub"]
    if not session_id:
        session_id = str(uuid.uuid4())
        
    content = await file.read()
    text = doc_processor.process_document(content, file.filename)
    
    # Check if the document is empty
    if not text:
        return {
            "session_id": session_id,
            "document_id": None,
            "extracted_info": None,
            "message": "The document is empty",
        }

    document_id = str(uuid.uuid4())

    # Check if the document is relevant
    relevancy = llm.check_relevance(text)
    if relevancy.get('document_type') == 'irrelevant_document':
        return {
            "session_id": session_id,
            "document_id": None,
            "extracted_info": None,
            "message": "The document is not relevant",
            "confidence": relevancy.confidence
        }
    
    # Extract information using LLM
    document_info = llm.extract_document_info(text)
    extracted_info = document_info.extracted_info
    
    # Check similar documents in the database
    similar_documents = loan_store.find_similar_documents(LoanDocument(**extracted_info.model_dump()))

    # Check if the user has an existing session with all similar documents
    existing_session = None
    for document_data in similar_documents:
        document = LoanDocument.from_dict(document_data)
        existing_session = chat_store.get_session_by_document_id(user_id, document.document_id)
        if not existing_session:
            break

    # If similar document exists and user has no existing session, return message
    if len(similar_documents) and not existing_session:
        conversation = [
            {"role": "user", "content": "Uploaded document"},
            {"role": "assistant", "content": "Similar document already exists. Contact admin for more information."}
        ]
        redis_handler.save_conversation(session_id, conversation)
        chat_store.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info.model_dump())
        chat_store.update_session_messages(session_id, conversation, title=document_info.chat_title)
        return {
            "session_id": session_id,
            "document_id": None,
            "message": "Similar document already exists. Contact admin for more information.",
        }

    if existing_session:
        conversation = [
            {"role": "user", "content": "Uploaded document"},
            {"role": "assistant", "content": "Similar document already exists."}
        ]
        redis_handler.save_conversation(session_id, conversation)
        chat_store.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info.model_dump())
        chat_store.update_session_messages(session_id, conversation, title=document_info.chat_title)
        return {
            "session_id": existing_session.session_id,
            "document_id": existing_session.document_id,
            "message": "Similar document already exists."
        }

    loan_document = extracted_info.model_dump()
    loan_document["document_id"] = document_id
    loan_document["created_by"] = user_id

    if document_info.consent:
        loan_document = LoanDocument(**loan_document)
        loan_store.store_document(loan_document)

    redis_handler.save_previous_info(session_id, extracted_info.model_dump())
    redis_handler.save_document_id(session_id, document_id)

    conversation = [
        {"role": "user", "content": "Uploaded document"},
        {"role": "assistant", "content": document_info.message}
    ]
    redis_handler.save_conversation(session_id, conversation)

    chat_store.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info.model_dump())
    chat_store.update_session_messages(session_id, conversation, title=document_info.chat_title)

    response = {
        "session_id": session_id,
        "document_id": document_id,
        "extracted_info": extracted_info.model_dump(),
        "message": document_info.message,
        "consent": document_info.consent,
        "is_updated": document_info.is_updated
    }

    logger.info(f"Upload response: {response}")
    
    return response

# Upload chat endpoint
@router.post("/upload_chat")
@timer
async def upload_chat(
    request: ChatRequest, 
    session_id: str = Header(...)
):
    try:

        start = perf_counter()
        conversation = redis_handler.get_conversation(session_id)
        previous_info = redis_handler.get_previous_info(session_id)
        document_id = redis_handler.get_document_id(session_id)
        logger.info(f"Redis retrieval took {perf_counter() - start:.2f} seconds")

        start = perf_counter()
        response = llm.extract_document_info_from_conversation(
            prompt=request.message,
            conversation=conversation,
            previous_info=previous_info
        )
        logger.info(f"LLM processing took {perf_counter() - start:.2f} seconds")
        
        if response.consent:
            start = perf_counter()
            try: 
                response_data = response.model_dump()
                response_data["document_id"] = document_id
                if not loan_store.get_document_by_id(document_id):
                    loan_document = LoanDocument(document_id=document_id, **response_data['extracted_info'])
                    loan_store.store_document(loan_document)
                else:
                    loan_document = LoanDocument(document_id=document_id, **response_data['extracted_info'])
                    loan_store.update_document(document_id, loan_document.to_dict())
                logger.info(f"Loan document store operation took {perf_counter() - start:.2f} seconds")
            except Exception as e:
                logger.error(f"Error handling loan store: {e}")
        
        start = perf_counter()
        conversation.extend([
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.message}
        ])
        redis_handler.save_conversation(session_id, conversation)
        chat_store.update_session_messages(session_id, conversation, "") # title is empty, so it will not be updated

        if response.extracted_info:
            redis_handler.save_previous_info(session_id, response.extracted_info.model_dump())
            chat_store.update_session_document_info(session_id, response.extracted_info.model_dump())

        logger.info(f"Conversation update took {perf_counter() - start:.2f} seconds")
        
        return {
            "extracted_info": response.extracted_info.model_dump() if response.extracted_info else None,
            "message": response.message,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error in upload_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
