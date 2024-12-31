from fastapi import APIRouter, Header, Form
from utils.jwt import JWT
from database.chat import ChatStore
from database.redis import RedisHandler

router = APIRouter(
    prefix="/",
    tags=["Session"],
)


# Get user sessions endpoint
@app.get("/sessions")
async def get_sessions(authorization: str = Header(...), limit: int = 10):
    user_id = jwt.decode_token(authorization)["sub"]
    return chat_store.get_user_sessions(user_id, limit)

# Get session details endpoint
@app.get("/session")
async def get_session(authorization: str = Header(...), session_id: str = Header(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    session = chat_store.get_session(user_id, session_id)
    session_messages = [message.to_dict() for message in session.messages]
    redis_handler.save_session(session_id, session_messages)
    if session.type == "upload":
        redis_handler.save_document_info(session_id, session.document_info)
    return session

# Update message feedback endpoint
@app.post("/update_message_feedback")
async def update_message_feedback(authorization: str = Header(...), session_id: str = Header(...), message_index: int = Form(...), feedback: str = Form(...), rating: int = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    return chat_store.update_message_feedback(user_id, session_id, message_index, feedback, rating)

# Update the title of the session
@app.post("/update_session_title")
async def update_session_title(authorization: str = Header(...), session_id: str = Header(...), title: str = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    return chat_store.update_session_title(user_id, session_id, title)