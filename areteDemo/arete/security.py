from passlib.context import CryptContext

# CryptContext centralizes hashing config 
pwd_context = CryptContext(
    schemes=["argon2"],
    default="argon2",
    deprecated="auto",
)


# Password hashing and verification functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Password verification for plain vs hashed passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password) #checks if plain password matches hashed password
    except Exception:
        
        return False   #in case of any error during verification, return False
