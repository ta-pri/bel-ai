from . import db
from datetime import datetime
 
class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    cover_url = db.Column(db.String(500), default='/static/img/book_placeholder.jpg')
    description = db.Column(db.Text, default='')
    price = db.Column(db.Float, default=0.0)
    genre = db.Column(db.String(100), default='')
    year = db.Column(db.Integer, default=2024)
    is_new = db.Column(db.Boolean, default=False)
    is_sale = db.Column(db.Boolean, default=False)
    sale_percent = db.Column(db.Integer, default=0)
    is_seasonal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
 
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'pages': self.pages,
            'publisher': self.publisher,
            'cover_url': self.cover_url,
            'description': self.description,
            'price': self.price,
            'genre': self.genre,
            'year': self.year,
            'is_new': self.is_new,
            'is_sale': self.is_sale,
            'sale_percent': self.sale_percent,
            'is_seasonal': self.is_seasonal,
        }
 
 
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
 
 
class Request(db.Model):
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(200), default='')
    message = db.Column(db.Text, default='')
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=True)
    book = db.relationship('Book', backref='requests')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)