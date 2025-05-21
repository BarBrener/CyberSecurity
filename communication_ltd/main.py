
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db import Base, engine, SessionLocal
import app.models as models
import app.schemas as schemas
import app.utils as utils
import json
import random
import string
import sqlite3
import html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import hashlib

app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

with open("config.json", "r") as f:
    config = json.load(f)

login_attempts = {}
reset_codes = {}

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) |
        (models.User.email == user.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    if not utils.validate_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet complexity requirements"
        )

    hashed_password = utils.hash_password(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    username = user.username
    password = user.password

    db_user = db.query(models.User).filter(models.User.username == username).first()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if login_attempts.get(username, 0) >= config["max_login_attempts"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked. Too many failed login attempts.")

    if not utils.verify_password(password, db_user.hashed_password):
        login_attempts[username] = login_attempts.get(username, 0) + 1
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    login_attempts[username] = 0

    return {"message": "Login successful!"}

@app.post("/change-password")
def change_password(request: schemas.ChangePasswordRequest, db: Session = Depends(get_db)):
    username = request.username
    current_password = request.current_password
    new_password = request.new_password

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not utils.verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")

    if not utils.validate_password(new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password does not meet complexity requirements")

    new_hashed_password = utils.hash_password(new_password)
    user.hashed_password = new_hashed_password

    db.commit()

    return {"message": "Password changed successfully!"}

@app.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = request.email

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    sha1_code = hashlib.sha1(random_string.encode()).hexdigest()

    reset_codes[email] = sha1_code

    return {"reset_code": sha1_code, "message": f"Reset code sent to {email}"}

@app.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    email = request.email
    reset_code = request.reset_code
    new_password = request.new_password

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    stored_reset_code = reset_codes.get(email)
    if stored_reset_code != reset_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset code")

    if not utils.validate_password(new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password does not meet complexity requirements")

    new_hashed_password = utils.hash_password(new_password)
    user.hashed_password = new_hashed_password

    db.commit()
    reset_codes.pop(email, None)

    return {"message": "Password reset successfully!"}

@app.post("/add-client")
def add_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    new_client = models.Client(name=client.name, sector=client.sector)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return {"message": f"Client '{new_client.name}' added successfully."}

@app.post("/login-vulnerable")
def vulnerable_login(data: schemas.UserLogin):
    conn = sqlite3.connect("communication_ltd.db")
    cursor = conn.cursor()

    query = f'''
    SELECT * FROM users
    WHERE username = '{data.username}' AND hashed_password = '{data.password}'
    '''
    print("RUNNING QUERY:", query)

    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"message": f"Login successful! Welcome {result[1]}"}
    else:
        return {"error": "Invalid credentials"}

@app.get("/list-clients", response_model=list[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db)):
    clients = db.query(models.Client).all()
    return clients

app.mount("/html", StaticFiles(directory="html"), name="html")

@app.get("/", response_class=FileResponse)
def serve_home():
    return "html/index.html"

#dildo