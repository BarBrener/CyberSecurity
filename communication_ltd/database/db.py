from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# כתובת החיבור למסד נתונים (קובץ SQLite שישמר אצלך בפרויקט)
DATABASE_URL = "sqlite:///./communication_ltd.db"

# יצירת מנוע (Engine) לדאטאבייס
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# יצירת סשן עבודה מול הדאטאבייס
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# בסיס להגדרת המודלים שלנו (Users, Clients וכו')
Base = declarative_base()
