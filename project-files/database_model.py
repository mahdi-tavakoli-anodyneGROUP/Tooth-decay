from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, func
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', admin={self.is_admin})>"

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    predicted_class = Column(String(100))
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="predictions")

    def __repr__(self):
        return f"<PredictionLog(user_id={self.user_id}, predicted_class='{self.predicted_class}')>"

class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", backref="login_logs")