from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(200))
    counterparty_account = db.Column(db.String(50))
    transaction_number = db.Column(db.String(50))
    accounting_date = db.Column(db.Date, nullable=False, index=True)
    value_date = db.Column(db.Date)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='EUR')
    description = db.Column(db.Text)
    details = db.Column(db.Text)
    message = db.Column(db.Text)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    tag = db.relationship('Tag', back_populates='transactions')
    
    @property
    def is_income(self):
        return self.amount > 0
    
    @property
    def is_expense(self):
        return self.amount < 0
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount} {self.currency} on {self.accounting_date}>'


class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6366f1')  # Default indigo color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    transactions = db.relationship('Transaction', back_populates='tag')
    
    def __repr__(self):
        return f'<Tag {self.name}>'
