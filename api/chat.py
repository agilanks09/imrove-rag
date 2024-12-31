from fastapi import APIRouter, Header
from typing import Optional
import uuid
from database.chat import ChatStore
from database.redis import RedisHandler
from database.document import LoanDocumentStore
from utils.jwt import JWT
from utils.timing import timer

router = APIRouter(
    prefix="/",
    tags=["User Chat"],
)

# Chat endpoint
@app.post("/kv-chat")
@timer
async def chat(
    request: ChatRequest,
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None),
):
    user_id = jwt.decode_token(authorization)["sub"]
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True
        chat_store.create_session(user_id, session_id, type='chat')
    
    conversation = redis_handler.get_conversation(session_id)
    conversation_str = "\n".join(f"{msg['role']}: {str(msg['content'])}" for msg in conversation) if conversation else ""

    intent_response = await llm.analyze_intent(request.message, conversation)
    intent = intent_response.intent

    if intent == 'out_of_scope':
        return {
            "response": "I'm sorry, I don't understand that. Please ask me about lending or loan options.",
            "session_id": session_id,
            "intent": intent,
            "intent_confidence": intent_response.confidence,
            "intent_reason": intent_response.reason
        }

    kb_result_str = ""
    if intent in ['specific_lender', 'filtered_lender_list']:
        query = llm.extract_feature_from_conversation(request.message, conversation)  
        kb_result_str = loan_store.search_documents(query)

    response = await llm.generate_response(intent, conversation_str, kb_result_str)
    
    if response is None:
        return {
            "response": "I'm sorry, I couldn't generate a response. Please try again.",
            "session_id": session_id,
            "intent": intent,
            "intent_confidence": intent_response.confidence,
            "intent_reason": intent_response.reason
        }

    new_conversation = [
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": response.response}
    ]

    conversation.extend(new_conversation)
    redis_handler.save_conversation(session_id, conversation)
    chat_store.update_session_messages(session_id, conversation, title=response.chat_title)
    
    return {
        "response": response.response,
        "session_id": session_id,
        "intent": intent,
        "intent_confidence": intent_response.confidence,
        "intent_reason": intent_response.reason
    }
