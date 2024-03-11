from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# Define User model
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    profile_pic = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    create_date = db.Column(db.DateTime, nullable=False)
    last_login_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.email},{self.password}>'

    def serialize(self):
        return {
            'id': self.id,
            'profile_pic': self.profile_pic,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'create_date': self.create_date.strftime('%Y-%m-%d %H:%M:%S') if self.create_date else None,
            'last_login_date': self.last_login_date.strftime('%Y-%m-%d %H:%M:%S') if self.last_login_date else None,
        }


# Define Campaign model
class Campaign(db.Model):
    __tablename__ = 'campaign'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    pic = db.Column(db.String(120), nullable=True)
    goal_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    user = db.relationship('User', backref='campaigns')

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'pic': self.pic,
            'goal_amount': self.goal_amount,
            'current_amount': self.current_amount,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'user': self.user.serialize() if self.user else None
        }


# Define Donation model
class Donation(db.Model):
    __tablename__ = 'donation'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    donor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    donation_date = db.Column(db.DateTime, nullable=False)
    message = db.Column(db.Text, nullable=True)
    campaign = db.relationship('Campaign', backref='donations')
    donor_user = db.relationship('User', foreign_keys=[donor_user_id], uselist=False)

    def __repr__(self):
        return f'<Donation {self.amount}>'

    def serialize(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'donor_user_id': self.donor_user_id,
            'amount': self.amount,
            'donation_date': self.donation_date.strftime('%Y-%m-%d %H:%M:%S'),
            'message': self.message,
        }


# Define Payment model
class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey(
        'donation.id'), nullable=False)
    stripe_payment_id = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    payment_method_type = db.Column(db.String(20), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False)
    donation = db.relationship('Donation', backref='payment')

    def __repr__(self):
        return f'<Payment {self.amount}>'

    def serialize(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'stripe_payment_id': self.stripe_payment_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'payment_method_type': self.payment_method_type,
            'transaction_date': self.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
        }


def is_token_revoked(jti):
    """
    Check if a JWT token identified by JTI is revoked.

    :param jti:
    :param self: The JTI (JSON Token Identifier) of the JWT token to check.
    :return: True if the token is revoked, False otherwise.
    """
    return bool(TokenBlocklist.query.filter_by(jti=jti).first())


class TokenBlocklist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jti = db.Column(db.String(), nullable=True)
    create_at = db.Column(db.DateTime(), default=datetime.utcnow)

    def __repr__(self):
        return f"<Token {self.jti}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
