from datetime import datetime
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt

from models import db, User, TokenBlocklist

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    new_user = User(email=email,
                    create_date=datetime.now(),
                    first_name=first_name,
                    last_name=last_name,
                    password=generate_password_hash(password, method='pbkdf2:sha256'),
                    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email_data = data.get('email')
    password_data = data.get('password')

    # check for email and password in database
    user = User.query.filter_by(email=email_data).first()

    if user is not None:
        if check_password_hash(user.password, password_data):
            access_token = create_access_token(identity=email_data)
            refresh_token = create_refresh_token(identity=user.email)

            return (jsonify({
                "message": "Logged In ",
                "tokens": {"access": access_token, "refresh": refresh_token},
                "user": user.serialize()
            }), 200,)

    return jsonify({'message': 'Bad Credentials'}), 401


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(verify_type=False)
def logout_user():
    jwt = get_jwt()

    jti = jwt['jti']
    token_type = jwt['type']

    token_b = TokenBlocklist(jti=jti)

    token_b.save()

    return jsonify({"message": f"{token_type} token revoked successfully"}), 200
