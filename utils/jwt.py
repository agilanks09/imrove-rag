import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class JWT:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = {"sub": data} if isinstance(data, (str, int)) else data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=1)  # Default 15 min
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return decoded

    def verify_token(self, token: str) -> bool:
        try:
            self.decode_token(token)
            return True
        except jwt.InvalidTokenError:
            return False
