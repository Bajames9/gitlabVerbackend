from pygments.lexer import default

from backend.databse import db
from sqlalchemy.dialects.mysql import JSON

class Lists(db.Model):
    __tablename__ = "RecipeLists"
    __table_args__ = {'extend_existing': True}

    list_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.userId", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    recipe_ids = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    is_public = db.Column(db.Boolean, nullable=False, default=False)
