"""
LiftLog API - Strava for weightlifting
"""
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import os

from database import get_db, init_db, engine
from models import Base, User, Exercise, Workout, WorkoutSet, PersonalRecord, Comment, workout_likes

# Config
SECRET_KEY = os.getenv("SECRET_KEY", "liftlog-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

app = FastAPI(title="LiftLog API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============ SCHEMAS ============

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    follower_count: int = 0
    following_count: int = 0
    workout_count: int = 0
    
    class Config:
        from_attributes = True

class ExerciseResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    equipment: Optional[str]
    primary_muscle: Optional[str]
    
    class Config:
        from_attributes = True

class SetCreate(BaseModel):
    exercise_id: int
    set_number: int
    reps: Optional[int] = None
    weight: Optional[float] = None
    weight_unit: str = "lbs"
    rpe: Optional[float] = None
    notes: Optional[str] = None

class SetResponse(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str
    set_number: int
    reps: Optional[int]
    weight: Optional[float]
    weight_unit: str
    rpe: Optional[float]
    is_pr: bool
    
    class Config:
        from_attributes = True

class WorkoutCreate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    is_public: bool = True

class WorkoutResponse(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    title: Optional[str]
    notes: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]
    is_public: bool
    like_count: int
    comment_count: int
    is_liked: bool = False
    sets: List[SetResponse] = []
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PRResponse(BaseModel):
    exercise_id: int
    exercise_name: str
    max_weight: Optional[float]
    max_weight_date: Optional[datetime]
    estimated_1rm: Optional[float]


# ============ AUTH HELPERS ============

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def get_optional_user(token: str = None, db: Session = Depends(get_db)) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except:
        return None


# ============ AUTH ENDPOINTS ============

@app.post("/api/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username taken")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email taken")
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        display_name=user.display_name or user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    token = create_access_token({"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer", "user": {"id": db_user.id, "username": db_user.username}}

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        bio=current_user.bio,
        avatar_url=current_user.avatar_url,
        follower_count=len(current_user.followers),
        following_count=len(current_user.following),
        workout_count=current_user.workouts.count()
    )


# ============ EXERCISE ENDPOINTS ============

@app.get("/api/exercises", response_model=List[ExerciseResponse])
async def list_exercises(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Exercise)
    if category:
        query = query.filter(Exercise.category == category)
    if search:
        query = query.filter(Exercise.name.ilike(f"%{search}%"))
    return query.order_by(Exercise.name).all()


# ============ WORKOUT ENDPOINTS ============

@app.post("/api/workouts")
async def start_workout(
    workout: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new workout"""
    db_workout = Workout(
        user_id=current_user.id,
        title=workout.title,
        notes=workout.notes,
        is_public=workout.is_public,
        started_at=datetime.utcnow()
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return {"id": db_workout.id, "started_at": db_workout.started_at}

@app.post("/api/workouts/{workout_id}/sets")
async def add_set(
    workout_id: int,
    set_data: SetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a set to workout"""
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == current_user.id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Check if this is a PR
    is_pr = False
    if set_data.weight and set_data.reps:
        # Get current max for this exercise
        current_max = db.query(func.max(WorkoutSet.weight)).join(Workout).filter(
            Workout.user_id == current_user.id,
            WorkoutSet.exercise_id == set_data.exercise_id,
            WorkoutSet.reps >= set_data.reps
        ).scalar()
        
        if current_max is None or set_data.weight > current_max:
            is_pr = True
            # Update PR record
            pr = db.query(PersonalRecord).filter(
                PersonalRecord.user_id == current_user.id,
                PersonalRecord.exercise_id == set_data.exercise_id
            ).first()
            
            if not pr:
                pr = PersonalRecord(user_id=current_user.id, exercise_id=set_data.exercise_id)
                db.add(pr)
            
            if not pr.max_weight or set_data.weight > pr.max_weight:
                pr.max_weight = set_data.weight
                pr.max_weight_date = datetime.utcnow()
            
            # Calculate E1RM (Brzycki formula)
            if set_data.reps < 10:
                e1rm = set_data.weight * (36 / (37 - set_data.reps))
                if not pr.estimated_1rm or e1rm > pr.estimated_1rm:
                    pr.estimated_1rm = round(e1rm, 1)
                    pr.estimated_1rm_date = datetime.utcnow()
    
    db_set = WorkoutSet(
        workout_id=workout_id,
        exercise_id=set_data.exercise_id,
        set_number=set_data.set_number,
        reps=set_data.reps,
        weight=set_data.weight,
        weight_unit=set_data.weight_unit,
        rpe=set_data.rpe,
        notes=set_data.notes,
        is_pr=is_pr
    )
    db.add(db_set)
    db.commit()
    db.refresh(db_set)
    
    exercise = db.query(Exercise).get(set_data.exercise_id)
    
    return {
        "id": db_set.id,
        "is_pr": is_pr,
        "exercise_name": exercise.name if exercise else None
    }

@app.put("/api/workouts/{workout_id}/finish")
async def finish_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Finish a workout"""
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == current_user.id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    workout.ended_at = datetime.utcnow()
    workout.duration_minutes = int((workout.ended_at - workout.started_at).total_seconds() / 60)
    
    # Auto-generate title if not set
    if not workout.title:
        exercises = db.query(Exercise.name).join(WorkoutSet).filter(WorkoutSet.workout_id == workout_id).distinct().all()
        if exercises:
            workout.title = ", ".join([e[0] for e in exercises[:3]])
            if len(exercises) > 3:
                workout.title += f" +{len(exercises) - 3} more"
    
    db.commit()
    return {"id": workout_id, "duration_minutes": workout.duration_minutes, "title": workout.title}

@app.get("/api/workouts/{workout_id}")
async def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workout details"""
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Check visibility
    if not workout.is_public and workout.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Private workout")
    
    user = workout.user
    sets = []
    for s in workout.sets:
        sets.append(SetResponse(
            id=s.id,
            exercise_id=s.exercise_id,
            exercise_name=s.exercise.name,
            set_number=s.set_number,
            reps=s.reps,
            weight=s.weight,
            weight_unit=s.weight_unit,
            rpe=s.rpe,
            is_pr=s.is_pr
        ))
    
    is_liked = current_user in workout.liked_by
    
    return WorkoutResponse(
        id=workout.id,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        title=workout.title,
        notes=workout.notes,
        started_at=workout.started_at,
        ended_at=workout.ended_at,
        duration_minutes=workout.duration_minutes,
        is_public=workout.is_public,
        like_count=workout.like_count,
        comment_count=workout.comment_count,
        is_liked=is_liked,
        sets=sets
    )

@app.get("/api/workouts")
async def list_my_workouts(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get my workout history"""
    workouts = db.query(Workout).filter(
        Workout.user_id == current_user.id
    ).order_by(desc(Workout.started_at)).offset(offset).limit(limit).all()
    
    result = []
    for w in workouts:
        sets = []
        for s in w.sets:
            sets.append(SetResponse(
                id=s.id,
                exercise_id=s.exercise_id,
                exercise_name=s.exercise.name,
                set_number=s.set_number,
                reps=s.reps,
                weight=s.weight,
                weight_unit=s.weight_unit,
                rpe=s.rpe,
                is_pr=s.is_pr
            ))
        result.append({
            "id": w.id,
            "title": w.title,
            "started_at": w.started_at,
            "duration_minutes": w.duration_minutes,
            "like_count": w.like_count,
            "comment_count": w.comment_count,
            "sets": sets
        })
    
    return result


# ============ FEED ENDPOINTS ============

@app.get("/api/feed")
async def get_feed(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get social feed (workouts from people you follow + your own)"""
    following_ids = [u.id for u in current_user.following]
    following_ids.append(current_user.id)
    
    workouts = db.query(Workout).filter(
        Workout.user_id.in_(following_ids),
        Workout.is_public == True,
        Workout.ended_at != None  # Only finished workouts
    ).order_by(desc(Workout.ended_at)).offset(offset).limit(limit).all()
    
    result = []
    for w in workouts:
        user = w.user
        sets = []
        for s in w.sets:
            sets.append({
                "exercise_name": s.exercise.name,
                "set_number": s.set_number,
                "reps": s.reps,
                "weight": s.weight,
                "is_pr": s.is_pr
            })
        
        result.append({
            "id": w.id,
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "title": w.title,
            "started_at": w.started_at,
            "duration_minutes": w.duration_minutes,
            "like_count": w.like_count,
            "comment_count": w.comment_count,
            "is_liked": current_user in w.liked_by,
            "sets": sets
        })
    
    return result

@app.get("/api/feed/discover")
async def discover_feed(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Discover new workouts from anyone"""
    workouts = db.query(Workout).filter(
        Workout.is_public == True,
        Workout.ended_at != None
    ).order_by(desc(Workout.ended_at)).offset(offset).limit(limit).all()
    
    result = []
    for w in workouts:
        user = w.user
        result.append({
            "id": w.id,
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "title": w.title,
            "duration_minutes": w.duration_minutes,
            "like_count": w.like_count,
            "is_liked": current_user in w.liked_by
        })
    
    return result


# ============ SOCIAL ENDPOINTS ============

@app.post("/api/workouts/{workout_id}/like")
async def like_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like a workout"""
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    if current_user in workout.liked_by:
        # Unlike
        workout.liked_by.remove(current_user)
        workout.like_count = max(0, workout.like_count - 1)
        liked = False
    else:
        # Like
        workout.liked_by.append(current_user)
        workout.like_count += 1
        liked = True
    
    db.commit()
    return {"liked": liked, "like_count": workout.like_count}

@app.post("/api/workouts/{workout_id}/comments")
async def add_comment(
    workout_id: int,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add comment to workout"""
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    db_comment = Comment(
        workout_id=workout_id,
        user_id=current_user.id,
        content=comment.content
    )
    db.add(db_comment)
    workout.comment_count += 1
    db.commit()
    db.refresh(db_comment)
    
    return CommentResponse(
        id=db_comment.id,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        content=db_comment.content,
        created_at=db_comment.created_at
    )

@app.get("/api/workouts/{workout_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    workout_id: int,
    db: Session = Depends(get_db)
):
    """Get comments for workout"""
    comments = db.query(Comment).filter(Comment.workout_id == workout_id).order_by(Comment.created_at).all()
    return [
        CommentResponse(
            id=c.id,
            user_id=c.user_id,
            username=c.user.username,
            display_name=c.user.display_name,
            avatar_url=c.user.avatar_url,
            content=c.content,
            created_at=c.created_at
        ) for c in comments
    ]

@app.post("/api/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow/unfollow a user"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Can't follow yourself")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user in current_user.following:
        current_user.following.remove(target_user)
        following = False
    else:
        current_user.following.append(target_user)
        following = True
    
    db.commit()
    return {"following": following}

@app.get("/api/users/{user_id}")
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "follower_count": len(user.followers),
        "following_count": len(user.following),
        "workout_count": user.workouts.count(),
        "is_following": user in current_user.following,
        "is_me": user.id == current_user.id
    }

@app.get("/api/users/{user_id}/workouts")
async def get_user_workouts(
    user_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's public workouts"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    query = db.query(Workout).filter(Workout.user_id == user_id, Workout.ended_at != None)
    if user_id != current_user.id:
        query = query.filter(Workout.is_public == True)
    
    workouts = query.order_by(desc(Workout.started_at)).limit(limit).all()
    
    return [{
        "id": w.id,
        "title": w.title,
        "started_at": w.started_at,
        "duration_minutes": w.duration_minutes,
        "like_count": w.like_count
    } for w in workouts]


# ============ STATS/PR ENDPOINTS ============

@app.get("/api/stats/prs")
async def get_my_prs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get my personal records"""
    prs = db.query(PersonalRecord).filter(PersonalRecord.user_id == current_user.id).all()
    
    result = []
    for pr in prs:
        exercise = db.query(Exercise).get(pr.exercise_id)
        if exercise and pr.max_weight:
            result.append({
                "exercise_id": pr.exercise_id,
                "exercise_name": exercise.name,
                "max_weight": pr.max_weight,
                "max_weight_date": pr.max_weight_date,
                "estimated_1rm": pr.estimated_1rm
            })
    
    return sorted(result, key=lambda x: x.get('estimated_1rm') or 0, reverse=True)

@app.get("/api/stats/exercise/{exercise_id}")
async def get_exercise_history(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get history for a specific exercise"""
    sets = db.query(WorkoutSet).join(Workout).filter(
        Workout.user_id == current_user.id,
        WorkoutSet.exercise_id == exercise_id
    ).order_by(desc(Workout.started_at)).limit(100).all()
    
    return [{
        "date": s.workout.started_at,
        "set_number": s.set_number,
        "reps": s.reps,
        "weight": s.weight,
        "is_pr": s.is_pr
    } for s in sets]


# ============ STARTUP ============

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "liftlog"}


# ============ STATIC FILES ============

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/manifest.json")
async def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.json")

@app.get("/")
@app.get("/{path:path}")
async def serve_frontend(path: str = ""):
    # Serve index.html for all non-API routes (SPA)
    file_path = FRONTEND_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_DIR / "index.html")
