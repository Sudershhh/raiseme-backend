from datetime import datetime, timedelta

from auth import auth_bp
from flask import Flask, jsonify, request
from flask_cors import CORS
from models import db, User, Campaign, Donation, Payment, TokenBlocklist, is_token_revoked
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt

# Create an instance of Flask-SQLAlchemy
ACCESS_EXPIRES = timedelta(hours=2)

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///raiseme.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES  # Change this!
jwt = JWTManager(app)

db.init_app(app)
app.register_blueprint(auth_bp, url_prefix='/auth')

with app.app_context():
    db.create_all()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return is_token_revoked(jti)


@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    serialized_users = [user.serialize() for user in users]
    return jsonify({'users': serialized_users})


@app.route('/users', methods=['PUT'])
@jwt_required()
def update_user():
    user = User.query.get(request.headers.get('UserId'))
    current_user_email = get_jwt_identity()
    if user.email != current_user_email:
        return jsonify({'message': 'Invalid user id'}), 401
    if user:
        data = request.json
        if 'profile_pic' in data:
            user.profile_pic = data['profile_pic']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.password = data['password']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        # You can update other fields similarly

        db.session.commit()

        return jsonify({'message': 'User updated successfully'})
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/campaigns', methods=['GET'])
def get_all_campaigns():
    campaigns = Campaign.query.all()
    serialized_campaigns = [campaign.serialize() for campaign in campaigns]
    return jsonify({'campaigns': serialized_campaigns})


@app.route('/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    # Retrieve the campaign by its ID
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    if campaign:
        return jsonify(campaign.serialize()), 200
    else:
        return jsonify({'message': 'Campaign not found'}), 404


@app.route('/user-campaigns', methods=['GET'])
@jwt_required()
def get_campaigns():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    if user.email != current_user_email:
        return jsonify({'message': 'Invalid user id'}), 401

    campaigns = Campaign.query.filter_by(user_id=user.id).all()
    serialized_campaigns = [campaign.serialize() for campaign in campaigns]
    return jsonify({'campaigns': serialized_campaigns})


@app.route('/campaigns', methods=['POST'])
@jwt_required()
def create_campaign():
    current_user_email = get_jwt_identity()
    data = request.json
    user_id = data.get('user_id')
    title = data.get('title')
    description = data.get('description')
    pic = data.get('pic')
    goal_amount = data.get('goal_amount')
    current_amount = data.get('current_amount')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status = data.get('status')

    auth_user = User.query.filter_by(id=user_id).first()

    if auth_user.email != current_user_email:
        return jsonify({'message': 'Invalid user id'}), 401

    start_date_as_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_as_datetime = datetime.strptime(end_date, '%Y-%m-%d')

    new_campaign = Campaign(user_id=auth_user.id,
                            title=title,
                            description=description,
                            pic=pic,
                            goal_amount=goal_amount,
                            current_amount=current_amount,
                            start_date=start_date_as_datetime,
                            end_date=end_date_as_datetime,
                            status=status,
                            user=auth_user)

    db.session.add(new_campaign)
    db.session.commit()

    return jsonify({'message': 'Campaign created successfully'})


@app.route('/campaigns/<int:campaign_id>', methods=['PUT'])
@jwt_required()
def update_campaign(campaign_id):
    # Retrieve the campaign by its ID
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    if not campaign:
        return jsonify({'message': 'Campaign not found'}), 404

    # Get the ID of the currently authenticated user
    current_user_id = get_jwt_identity()

    # Check if the current user is the owner of the campaign or an admin
    # Assuming you have a 'is_admin' attribute in your User model
    if campaign.user_id != current_user_id and not User.query.get(current_user_id).is_admin:
        return jsonify({'message': 'Unauthorized to update this campaign'}), 403

    data = request.json
    campaign.title = data.get('title', campaign.title)
    campaign.description = data.get('description', campaign.description)
    campaign.pic = data.get('pic', campaign.pic)
    campaign.goal_amount = data.get('goal_amount', campaign.goal_amount)
    campaign.current_amount = data.get('current_amount', campaign.current_amount)
    start_date = data.get('start_date', campaign.start_date.strftime('%Y-%m-%d'))
    end_date = data.get('end_date', campaign.end_date.strftime('%Y-%m-%d'))
    campaign.status = data.get('status', campaign.status)

    campaign.start_date = datetime.strptime(start_date, '%Y-%m-%d')
    campaign.end_date = datetime.strptime(end_date, '%Y-%m-%d')

    db.session.commit()

    return jsonify({'message': 'Campaign updated successfully'}), 200


@app.route('/campaigns/<int:campaign_id>', methods=['DELETE'])
@jwt_required()
def delete_campaign(campaign_id):
    # Retrieve the campaign by its ID
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    if not campaign:
        return jsonify({'message': 'Campaign not found'}), 404

    # Get the ID of the currently authenticated user
    current_user_id = get_jwt_identity()

    # Check if the current user is the owner of the campaign or an admin
    if campaign.user_id != current_user_id and not User.query.get(current_user_id).is_admin:
        return jsonify({'message': 'Unauthorized to delete this campaign'}), 403

    db.session.delete(campaign)
    db.session.commit()

    return jsonify({'message': 'Campaign deleted successfully'}), 200


@app.route('/campaigns', methods=['GET'])
def get_campaigns_for_one_user():
    user = User.query.get_or_404(request.json["id"])
    campaigns = Campaign.query.filter_by(user_id=user.id).all()
    serialized_campaigns = [campaign.serialize() for campaign in campaigns]
    return jsonify({'campaigns': serialized_campaigns})


@app.route('/donations', methods=['POST'])
def create_donation():
    data = request.json
    print(data)
    required_fields = ['campaign_id', 'amount', 'donation_date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    donation_date_str = data['donation_date']
    try:
        donation_date = datetime.strptime(donation_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid donation_date format'}), 400
    campaign_id = data['campaign_id']
    campaign = Campaign.query.filter_by(id=campaign_id).first()
    if campaign:
        campaign.current_amount += int(data['amount'])
        db.session.commit()

    new_donation = Donation(
        campaign_id=data['campaign_id'],
        donor_user_id=data.get('donor_user_id'),
        amount=data['amount'],
        donation_date=donation_date,
        message=data.get('message')
    )



    db.session.add(new_donation)

    try:
        db.session.commit()
        return jsonify({'message': 'Donation created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# @app.route('/donations', methods=['GET'])
# def get_donations_for_one_campaign():
#     user = User.query.get_or_404(request.json["id"])
#     donations = Donation.query.filter_by(user_id=user.id).all()
#     serialized_donations = [donation.serialize() for donation in donations]
#     return jsonify({'donations': serialized_donations})

@app.route('/donations/<int:campaign_id>', methods=['GET'])
def get_donations_for_one_campaign(campaign_id):
    
    campaign = Campaign.query.filter_by(id = campaign_id).first()
    print(campaign.id)
    donations = Donation.query.filter_by(campaign_id=campaign.id).all()
    serialized_donations = [donation.serialize() for donation in donations]
    return jsonify({'donations': serialized_donations})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
