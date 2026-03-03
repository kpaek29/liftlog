"""
LiftLog Database Models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Many-to-many: followers
followers = Table(
    'followers',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('followed_id', Integer, ForeignKey('users.id'), primary_key=True)
)

# Many-to-many: workout likes
workout_likes = Table(
    'workout_likes',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('workout_id', Integer, ForeignKey('workouts.id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100))
    bio = Column(Text)
    avatar_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    workouts = relationship('Workout', back_populates='user', lazy='dynamic')
    comments = relationship('Comment', back_populates='user')
    
    # Following/followers
    following = relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref='followers'
    )


class Exercise(Base):
    """Master list of exercises"""
    __tablename__ = 'exercises'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    category = Column(String(50))  # chest, back, legs, shoulders, arms, core
    equipment = Column(String(50))  # barbell, dumbbell, machine, bodyweight, cable
    description = Column(Text)
    
    # Track which muscles
    primary_muscle = Column(String(50))
    secondary_muscles = Column(String(200))  # comma-separated


class Workout(Base):
    """A single workout session"""
    __tablename__ = 'workouts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(200))
    notes = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration_minutes = Column(Integer)
    
    # Social
    is_public = Column(Boolean, default=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='workouts')
    sets = relationship('WorkoutSet', back_populates='workout', cascade='all, delete-orphan')
    comments = relationship('Comment', back_populates='workout', cascade='all, delete-orphan')
    liked_by = relationship('User', secondary=workout_likes, backref='liked_workouts')


class WorkoutSet(Base):
    """Individual set within a workout"""
    __tablename__ = 'workout_sets'
    
    id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    
    set_number = Column(Integer, nullable=False)
    reps = Column(Integer)
    weight = Column(Float)  # in lbs (can convert to kg in frontend)
    weight_unit = Column(String(10), default='lbs')
    
    # Optional tracking
    rpe = Column(Float)  # Rate of Perceived Exertion (1-10)
    rest_seconds = Column(Integer)
    notes = Column(String(500))
    
    # Is this a PR?
    is_pr = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workout = relationship('Workout', back_populates='sets')
    exercise = relationship('Exercise')


class PersonalRecord(Base):
    """Track PRs for each user/exercise"""
    __tablename__ = 'personal_records'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    
    # Different PR types
    max_weight = Column(Float)
    max_weight_date = Column(DateTime)
    max_reps = Column(Integer)
    max_reps_date = Column(DateTime)
    max_volume = Column(Float)  # weight x reps
    max_volume_date = Column(DateTime)
    
    # E1RM (estimated 1 rep max)
    estimated_1rm = Column(Float)
    estimated_1rm_date = Column(DateTime)


class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workout = relationship('Workout', back_populates='comments')
    user = relationship('User', back_populates='comments')
