from datetime import datetime
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import JSON
from .. import db, mdb, login_manager, contents_collection

from .business import calculate_charge_rule, calculate_reduce_charge



class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.BigInteger, primary_key=True)
    # body = db.Column(LONGTEXT)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    amount = db.Column(db.Integer)
    currency = db.Column(db.String(64), default='IRT')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, index=True, default=datetime.now)
    
    @classmethod
    def create_charge_transaction(cls, user_id: int, amount: int, description='Charge user by bank'):
        obj = cls(user_id=user_id, amount=amount, description=description)
        db.session.add(obj)
        db.session.commit()
        return obj


class Bank(db.Model):
    __tablename__ = 'banks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    slug = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    logo_url = db.Column(db.Text)
    api_key = db.Column(db.Text)
    description = db.Column(db.Text)
    
    
    created_at = db.Column(db.DateTime,default=datetime.now)
    updated_at = db.Column(db.DateTime,default=datetime.now, onupdate=datetime.now)
    
    
    @classmethod 
    def get_bank_by_slug(cls, slug):
        return cls.query.filter_by(slug=slug).first()
    
        
    

class Receipt(db.Model):
    __tablename__ = 'receipts'
    # STATUSES: pending, success, failed
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(128), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'))
    transaction = db.Column(db.BigInteger, db.ForeignKey('transactions.id'), nullable=True)
    currency = db.Column(db.String(64), default='IRT')
    amount = db.Column(db.Integer)
    status = db.Column(db.String(64))
    tracker_id = db.Column(db.String(64))
    
    description = db.Column(db.Text)
    additional_data = db.Column(JSON, default=dict)  # JSON column with default value
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    
    @classmethod
    def create_receipt(cls, user_id, amount, bank_id):
        number = datetime.now().strftime("%Y%m%d%H%M%S")
        obj = cls(number=number, 
                  user_id=user_id, 
                  amount=amount, 
                  bank_id=bank_id,
                  status='pending'
                  )
        db.session.add(obj)
        return obj

    def update_additional_data(self, new_data):
        if not isinstance(new_data, dict):
            raise ValueError("new_data must be a dictionary")
        
        if self.additional_data is None:
            self.additional_data = {}

        self.additional_data.update(new_data)
        db.session.commit()
        return self
    
    def set_status(self, status='success'):
        self.status = status
        db.session.commit()
        return self
    
    def set_tracker_id(self, tracker_id):
        self.tracker_id = tracker_id
        db.session.commit()
        return self
    
    def add_transaction(self, bank_slug='zibal', description=''):
        bank = Bank.query.filter_by(slug=bank_slug).first()
        self.bank_id = bank.id
        # Add transaction for user
        Transaction.create_charge_transaction(user_id=self.user_id, 
                                              amount=self.amount, 
                                              description='User charges for {} [{}]'.format(self.tracker_id, description))
        # To have system balance, add another transaction for bank
        
        Transaction.create_charge_transaction(user_id=bank.user_id, 
                                              amount=self.amount * -1, 
                                              description='Payment {} [{}]'.format(self.tracker_id, description))
        
        db.session.commit()
        return self


class Charge(db.Model):
    __tablename__ = 'charges'
    id = db.Column(db.BigInteger, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    word_count = db.Column(db.Integer)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, index=True, default=datetime.now)
    
    
    @classmethod
    def add_user_charge(cls, user_id, toman_amount):
        total_words = calculate_charge_rule(toman_amount)
        obj = cls(user_id=user_id,
                  word_count=total_words)
        db.session.add(obj)
        db.session.commit()
        return obj

    @classmethod
    def reduce_user_charge(cls, user_id, total_words, model='gpt-3.5'):
        if total_words < 0:
            total_words = -1 * total_words
        total_words = calculate_reduce_charge(total_words, model=model)
        obj = cls(user_id=user_id,
                  word_count=total_words * -1)
        db.session.add(obj)
        db.session.commit()
        return obj
    
    @classmethod
    def get_user_charge(cls, user_id):
        total_word_count = db.session.query(db.func.sum(cls.word_count)).filter_by(user_id=user_id).scalar()
        return total_word_count if total_word_count is not None else 0
