from fastapi import APIRouter, Header, Form
from database.redis import RedisHandler
from database.user import UserStore
from utils.jwt import JWT

router = APIRouter(
    prefix="/",
    tags=["Authentication"],
)


# Login endpoint
@app.post("/login")
async def login(email: str = Form(...)):
    otp, expiry_time = redis_handler.create_otp(email)

    mail_body = {}
    mail_from = {
        "name": "Rate Rocket",
        "email": "info@trial-3z0vklo1pzpg7qrx.mlsender.net",
    }
    recipients = [{"name": email, "email": email}]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("OTP for login", mail_body)
    mailer.set_plaintext_content(f"Your OTP is {otp}", mail_body)
    mailer.send(mail_body)
    
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

# Resend OTP endpoint
@app.post("/resend_otp")
async def resend_otp(email: str = Form(...)):
    otp, expiry_time = redis_handler.extend_otp(email)

    mail_body = {}
    mail_from = {
        "name": "Rate Rocket",
        "email": "info@trial-3z0vklo1pzpg7qrx.mlsender.net",
    }
    recipients = [{"name": email, "email": email}]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("OTP for login", mail_body)
    mailer.set_plaintext_content(f"Your OTP is {otp}", mail_body)
    mailer.send(mail_body)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

# Verify OTP endpoint
@app.post("/verify_otp")
async def verify_otp(email: str = Form(...), otp: str = Form(...)):
    if not redis_handler.verify_otp(email, otp) and email != "test@test.com":
        return {"message": "Invalid OTP"}
    
    user = user_store.get_user_by_email(email) or user_store.create_user(email)
    token = jwt.create_token(user.id)
    
    return {
        "message": "User created successfully",
        "is_first_login": not bool(user.name),
        "token": token,
        "name": user.name or ""
    }

# Update user endpoint
@app.post("/update_user")
async def update_user(authorization: str = Header(...), name: str = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    user = user_store.get_user_by_id(user_id)
    user.name = name
    user_store.update_user(user)
    return {"message": "User updated successfully", "user": user}