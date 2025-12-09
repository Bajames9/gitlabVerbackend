from backend.databse import db
from sqlalchemy.dialects.mysql import JSON

class Recipes(db.Model):
    __tablename__ = "recipes"

    RecipeId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False)
    AuthorName = db.Column(db.String(255))
    Description = db.Column(db.Text)
    RecipeCategory = db.Column(db.String(255))
    Keywords = db.Column(db.String(255))
    CookTime = db.Column(db.String(50))
    PrepTime = db.Column(db.String(50))
    TotalTime = db.Column(db.String(50))
    DatePublished = db.Column(db.DateTime)
    AggregatedRating = db.Column(db.Float)
    ReviewCount = db.Column(db.Integer)
    RecipeServings = db.Column(db.String(50))
    RecipeYield = db.Column(db.String(50))
    RecipeIngredientQuantities = db.Column(JSON)
    RecipeIngredientParts = db.Column(JSON)
    RecipeInstructions = db.Column(JSON)
    NutritionFacts = db.Column(JSON)
    Images = db.Column(JSON)