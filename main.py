import os
import random
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- INSTANT TERMINAL OTP DISPATCHER (ZERO SMTP ERRORS) ---
def send_otp_email(receiver_email: str, otp_code: str):
    """Prints OTP instantly and clearly in the terminal console"""
    print(f"\n==========================================")
    print(f" 🔑 OTP FOR {receiver_email} --> {otp_code}")
    print(f"==========================================\n")

# 1. Database Setup
if not os.path.exists("static"):
    os.makedirs("static")

SQLALCHEMY_DATABASE_URL = "sqlite:///./stocksense.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    surname = Column(String)
    country = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    otp_code = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    sku = Column(String, index=True)
    category = Column(String)
    unit_of_measure = Column(String)
    total_stock = Column(Integer, default=0)

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    transaction_type = Column(String) 
    quantity = Column(Integer)
    source_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def seed_default_user():
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@stocksense.com").first()
    if not admin:
        default_user = User(
            name="Admin",
            surname="User",
            country="India",
            email="admin@stocksense.com",
            password="admin123",
            is_verified=True
        )
        db.add(default_user)
        db.commit()
    db.close()

seed_default_user()

# 3. Pydantic Schemas
class UserRegister(BaseModel):
    name: str
    surname: str
    country: str
    email: str
    password: str

class VerifyRegisterOTP(BaseModel):
    email: str
    otp: str

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyLoginOTP(BaseModel):
    email: str
    otp: str

class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str
    new_password: str

class ProductCreate(BaseModel):
    user_id: int
    name: str
    sku: str
    category: str
    unit_of_measure: str
    initial_stock: int = 0

class MovementCreate(BaseModel):
    user_id: int
    product_id: int
    transaction_type: str 
    quantity: int
    source_location_id: Optional[int] = None
    destination_location_id: Optional[int] = None

# 4. Initialize App
app = FastAPI(title="StockSense API")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FRONTEND ROUTES ---
@app.get("/", response_class=RedirectResponse)
def root_redirect():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def serve_login():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    login_path = os.path.join(base_dir, "login.html")
    try:
        with open(login_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Error: Missing login.html</h1>"

@app.get("/app", response_class=HTMLResponse)
def serve_dashboard():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Error: Missing index.html</h1>"

@app.get("/logout", response_class=RedirectResponse)
def logout():
    return RedirectResponse(url="/login")


# --- AUTHENTICATION & OTP ENDPOINTS ---

@app.post("/api/auth/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    reg_otp = str(random.randint(100000, 999999))
    
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=400, detail="Email is already registered.")
        else:
            existing.name = user.name
            existing.surname = user.surname
            existing.country = user.country
            existing.password = user.password
            existing.otp_code = reg_otp
            db.commit()
    else:
        new_user = User(
            name=user.name,
            surname=user.surname,
            country=user.country,
            email=user.email,
            password=user.password,
            otp_code=reg_otp,
            is_verified=False
        )
        db.add(new_user)
        db.commit()

    send_otp_email(user.email, reg_otp)
    return {"status": "success", "requires_otp": True, "message": f"Verification code generated for {user.email}!"}

@app.post("/api/auth/verify-register-otp")
def verify_register_otp(req: VerifyRegisterOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.otp_code != req.otp:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
    
    user.is_verified = True
    user.otp_code = None
    db.commit()
    return {"status": "success", "message": "Account verified successfully! You can now sign in."}

@app.post("/api/auth/login")
def authenticate_user(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or user.password != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email address first.")

    # HARDCODED DEMO OTP: Use 123456 for the admin account, otherwise generate a random one
    if credentials.email == "admin@stocksense.com":
        login_otp = "123456"
    else:
        login_otp = str(random.randint(100000, 999999))
        
    user.otp_code = login_otp
    db.commit()
    
    send_otp_email(credentials.email, login_otp)
    return {"status": "success", "requires_otp": True, "message": f"Login OTP generated for {credentials.email}!"}

@app.post("/api/auth/verify-login-otp")
def verify_login_otp(req: VerifyLoginOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.otp_code != req.otp:
        raise HTTPException(status_code=400, detail="Invalid login OTP code.")
    
    user.otp_code = None
    db.commit()
    return {"status": "success", "message": "Login successful", "user_id": user.id}

@app.post("/api/auth/request-otp")
def request_otp(req: OTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found in database records.")
    
    generated_otp = str(random.randint(100000, 999999))
    user.otp_code = generated_otp
    db.commit()
    
    send_otp_email(req.email, generated_otp)
    return {"status": "success", "message": f"Reset OTP generated for {req.email}!"}

@app.post("/api/auth/reset-password")
def reset_password(req: OTPVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found.")
    
    if user.otp_code and user.otp_code == req.otp:
        user.password = req.new_password
        user.otp_code = None 
        db.commit()
        return {"status": "success", "message": "Password reset successfully! You can now log in."}
    
    raise HTTPException(status_code=400, detail="Invalid or expired OTP code.")


# --- ISOLATED INVENTORY API ENDPOINTS ---

@app.get("/locations/")
def get_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()

@app.get("/api/products/")
def get_products(user_id: int, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.user_id == user_id).all()

@app.post("/products/")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    product_data = product.model_dump(exclude={"initial_stock"})
    db_product = Product(**product_data, total_stock=product.initial_stock)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.post("/inventory/move/")
def process_stock_movement(movement: MovementCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == movement.product_id, Product.user_id == movement.user_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    actual_quantity = movement.quantity

    if movement.transaction_type == "Receipt":
        product.total_stock += movement.quantity
    elif movement.transaction_type == "Delivery":
        if product.total_stock < movement.quantity:
            raise HTTPException(status_code=400, detail="Not enough stock")
        product.total_stock -= movement.quantity
        actual_quantity = -movement.quantity
    else:
        raise HTTPException(status_code=400, detail="Invalid type")

    ledger_entry = StockMovement(
        user_id=movement.user_id,
        product_id=product.id,
        transaction_type=movement.transaction_type,
        quantity=actual_quantity,
        source_location_id=movement.source_location_id,
        destination_location_id=movement.destination_location_id
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(product)
    
    return {"status": "Success", "product": product.name, "new_total_stock": product.total_stock}

@app.get("/inventory/ledger/")
def get_ledger(user_id: int, db: Session = Depends(get_db)):
    return db.query(StockMovement).filter(StockMovement.user_id == user_id).order_by(StockMovement.id.desc()).all()

@app.get("/api/dashboard/")
def get_dashboard(user_id: int, db: Session = Depends(get_db)):
    total_products = db.query(Product).filter(Product.user_id == user_id).count()
    low_stock_items = db.query(Product).filter(Product.user_id == user_id, Product.total_stock < 10).all()
    return {
        "Total Products in Stock": total_products,
        "Low Stock Alerts": [p.name for p in low_stock_items]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
