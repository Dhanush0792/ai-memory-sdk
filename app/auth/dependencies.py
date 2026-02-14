from app.database import db

# ... (rest of imports)

# ... (logger setup)

# ... (security setup)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token and query DB for user.
    Raises 401 if token is invalid, expired, user not found, or user is inactive.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # Immediate invalidation check: Query DB
        with db.get_cursor() as cur:
            cur.execute("SELECT id, role, is_active FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
        if not user:
            logger.warning("auth_failed_user_not_found", user_id=user_id)
            raise credentials_exception
            
        if not user["is_active"]:
            logger.warning("auth_failed_user_disabled", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Account disabled", # Explicit 401 for disabled users as requested
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return {"id": str(user["id"]), "role": user["role"]}
        
    except JWTError:
        raise credentials_exception

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
