"""
Database setup and seed data
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Exercise, User
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./liftlog.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables and seed exercises"""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if exercises already seeded
    if db.query(Exercise).count() > 0:
        db.close()
        return
    
    # Seed common exercises
    exercises = [
        # Chest
        {"name": "Bench Press", "category": "chest", "equipment": "barbell", "primary_muscle": "chest"},
        {"name": "Incline Bench Press", "category": "chest", "equipment": "barbell", "primary_muscle": "chest"},
        {"name": "Dumbbell Bench Press", "category": "chest", "equipment": "dumbbell", "primary_muscle": "chest"},
        {"name": "Incline Dumbbell Press", "category": "chest", "equipment": "dumbbell", "primary_muscle": "chest"},
        {"name": "Dumbbell Fly", "category": "chest", "equipment": "dumbbell", "primary_muscle": "chest"},
        {"name": "Cable Fly", "category": "chest", "equipment": "cable", "primary_muscle": "chest"},
        {"name": "Push Up", "category": "chest", "equipment": "bodyweight", "primary_muscle": "chest"},
        {"name": "Chest Dip", "category": "chest", "equipment": "bodyweight", "primary_muscle": "chest"},
        
        # Back
        {"name": "Deadlift", "category": "back", "equipment": "barbell", "primary_muscle": "back"},
        {"name": "Barbell Row", "category": "back", "equipment": "barbell", "primary_muscle": "back"},
        {"name": "Dumbbell Row", "category": "back", "equipment": "dumbbell", "primary_muscle": "back"},
        {"name": "Pull Up", "category": "back", "equipment": "bodyweight", "primary_muscle": "back"},
        {"name": "Chin Up", "category": "back", "equipment": "bodyweight", "primary_muscle": "back"},
        {"name": "Lat Pulldown", "category": "back", "equipment": "cable", "primary_muscle": "lats"},
        {"name": "Seated Cable Row", "category": "back", "equipment": "cable", "primary_muscle": "back"},
        {"name": "T-Bar Row", "category": "back", "equipment": "barbell", "primary_muscle": "back"},
        
        # Legs
        {"name": "Squat", "category": "legs", "equipment": "barbell", "primary_muscle": "quads"},
        {"name": "Front Squat", "category": "legs", "equipment": "barbell", "primary_muscle": "quads"},
        {"name": "Leg Press", "category": "legs", "equipment": "machine", "primary_muscle": "quads"},
        {"name": "Romanian Deadlift", "category": "legs", "equipment": "barbell", "primary_muscle": "hamstrings"},
        {"name": "Leg Curl", "category": "legs", "equipment": "machine", "primary_muscle": "hamstrings"},
        {"name": "Leg Extension", "category": "legs", "equipment": "machine", "primary_muscle": "quads"},
        {"name": "Lunges", "category": "legs", "equipment": "dumbbell", "primary_muscle": "quads"},
        {"name": "Bulgarian Split Squat", "category": "legs", "equipment": "dumbbell", "primary_muscle": "quads"},
        {"name": "Calf Raise", "category": "legs", "equipment": "machine", "primary_muscle": "calves"},
        
        # Shoulders
        {"name": "Overhead Press", "category": "shoulders", "equipment": "barbell", "primary_muscle": "shoulders"},
        {"name": "Dumbbell Shoulder Press", "category": "shoulders", "equipment": "dumbbell", "primary_muscle": "shoulders"},
        {"name": "Lateral Raise", "category": "shoulders", "equipment": "dumbbell", "primary_muscle": "shoulders"},
        {"name": "Front Raise", "category": "shoulders", "equipment": "dumbbell", "primary_muscle": "shoulders"},
        {"name": "Face Pull", "category": "shoulders", "equipment": "cable", "primary_muscle": "rear delts"},
        {"name": "Rear Delt Fly", "category": "shoulders", "equipment": "dumbbell", "primary_muscle": "rear delts"},
        
        # Arms
        {"name": "Barbell Curl", "category": "arms", "equipment": "barbell", "primary_muscle": "biceps"},
        {"name": "Dumbbell Curl", "category": "arms", "equipment": "dumbbell", "primary_muscle": "biceps"},
        {"name": "Hammer Curl", "category": "arms", "equipment": "dumbbell", "primary_muscle": "biceps"},
        {"name": "Preacher Curl", "category": "arms", "equipment": "barbell", "primary_muscle": "biceps"},
        {"name": "Tricep Pushdown", "category": "arms", "equipment": "cable", "primary_muscle": "triceps"},
        {"name": "Skull Crusher", "category": "arms", "equipment": "barbell", "primary_muscle": "triceps"},
        {"name": "Tricep Dip", "category": "arms", "equipment": "bodyweight", "primary_muscle": "triceps"},
        {"name": "Close Grip Bench Press", "category": "arms", "equipment": "barbell", "primary_muscle": "triceps"},
        
        # Core
        {"name": "Plank", "category": "core", "equipment": "bodyweight", "primary_muscle": "core"},
        {"name": "Crunch", "category": "core", "equipment": "bodyweight", "primary_muscle": "abs"},
        {"name": "Leg Raise", "category": "core", "equipment": "bodyweight", "primary_muscle": "abs"},
        {"name": "Russian Twist", "category": "core", "equipment": "bodyweight", "primary_muscle": "obliques"},
        {"name": "Cable Crunch", "category": "core", "equipment": "cable", "primary_muscle": "abs"},
        {"name": "Ab Wheel Rollout", "category": "core", "equipment": "other", "primary_muscle": "core"},
    ]
    
    for ex in exercises:
        db.add(Exercise(**ex))
    
    db.commit()
    print(f"Seeded {len(exercises)} exercises")
    
    # Seed default user
    if not db.query(User).filter(User.username == "kevin").first():
        default_user = User(
            username="kevin",
            email="kevin@liftlog.app",
            hashed_password=pwd_context.hash("lift123"),
            display_name="Kevin"
        )
        db.add(default_user)
        db.commit()
        print("Created default user: kevin / lift123")
    
    db.close()


if __name__ == "__main__":
    init_db()
