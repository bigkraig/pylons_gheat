"""The application's model objects"""
from googleheat.model.meta import Session, Base
from sqlalchemy import Table, Column, Float, Integer, DateTime, BLOB

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    Session.configure(bind=engine)

class Points(Base):
    __tablename__ = "points"
    uid = Column("UID", BLOB(length=16), primary_key=True, autoincrement=False)
    latitude = Column("LAT", Float)
    longitude = Column("LNG", Float)
    modtime = Column("MODTIME", DateTime)
    seentime = Column("SEENTIME", DateTime)
    