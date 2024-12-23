from flask import Flask, request, redirect, url_for, flash, jsonify, session, send_from_directory, render_template_string  
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash, check_password_hash
import argparse
# from models import db, User, Transaction, Submission, Peoplemetrics, Planetmetrics, Prosperitymetrics, Governancemetrics
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.inspection import inspect
from algosdk import account
import json
from algotransaction import first_transaction_example
from algosdk.v2client import algod
from asa_creation import createASA, optinASA, transferASA
import json
from base64 import b64decode
from algosdk import transaction
from algosdk.transaction import PaymentTxn
from utils import algod_details
from faker import Faker
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
import random
from datetime import datetime
import requests
from modelsBanks import db, User, UserRole, Transaction, Submission, SocialMetrics, EnvironmentalMetrics, GovernanceMetrics
from werkzeug.security import generate_password_hash
import json
import numpy as np

ecochainPK = "4pGX12svaEoBYqBX7WfriGIhUB3VjkeUofm6IM3Y+6b69JOah+47V6+PX/KeLfpDMv683zGwQ2R83pkdj7FwCA=="
ecochainAddress = "7L2JHGUH5Y5VPL4PL7ZJ4LP2IMZP5PG7GGYEGZD432MR3D5ROAEDKWFGRU"
ADMIN_EMAIL = 'admin@example.com'  # Replace with the actual admin email
ADMIN_PASSWORD = 'adminpassword'  # Replace with the actual admin password
ADMIN_PASSWORD_HASHED = generate_password_hash('adminpassword')
load_dotenv() 
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecochain.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this in production
app.config['MAIL_SERVER'] = 'mail.smtp2go.com'
app.config['MAIL_PORT'] = 587  # Use 465 for SSL
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('SMTP2GO_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('SMTP2GO_PASSWORD')

mail = Mail(app)

jwt = JWTManager(app)

db.init_app(app)
CORS(app)
fake = Faker()

@app.route("/")
def home():
    return jsonify({
        "status": "success", 
        "message": "Welcome to EcoChain"
        }), 200

@app.route("/login", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.json.get('email')
        password = request.json.get('password')

        print(f"email: {email}, password: {password}")
        
        user = User.query.filter_by(Email=email).first()

        if user and check_password_hash(user.Password, password):
            access_token = create_access_token(identity=user.UserID, additional_claims={"role": user.Role.value})  # Use enum value
            print("Access token created: ", access_token)
            return jsonify(access_token=access_token, success=True, role=user.Role.value), 200  # Include role in response

        # Check if the provided credentials match the admin credentials
        elif email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASHED, password):
            # Create an access token with the admin role
            access_token = create_access_token(identity=email, additional_claims={"role": UserRole.admin.value})  # Use enum value
            print("Admin access token created: ", access_token)
            return jsonify(access_token=access_token, success=True, role=UserRole.admin.value), 200  # Include role in response
        
        return jsonify({
            "success": False, 
            "message": "Invalid email or password"
            }), 401
    

@app.route("/admin/submissions", methods=["GET"])
@jwt_required()
def admin_submissions():
    # Check if the logged-in user is an admin
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.Role.value != 'admin':  # Or use another value if you've defined roles differently
        return jsonify({"msg": "Unauthorized"}), 403  # Forbidden

    # Fetch all submissions from the database
    submissions = Submission.query.all()

    # Convert submissions to a list of dictionaries
    submission_list = [submission.as_dict() for submission in submissions]

    return jsonify(submission_list), 200


@app.route("/auditor/submissions", methods=["GET", "POST"])
@jwt_required()
def auditor_submissions():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.Role.value != 'auditor':
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == 'GET':
        # Fetch pending submissions (assuming Status=1 means pending)
        submissions = Submission.query.filter_by(Status=1).all()  
        submission_list = [submission.as_dict() for submission in submissions]
        return jsonify(submission_list), 200

    elif request.method == 'POST':
        data = request.get_json()
        submission_id = data.get('submission_id')
        action = data.get('action')  # 'view' or 'approve' or 'reject'
        feedback = data.get('feedback')

        if not submission_id or not action:
            return jsonify({"msg": "Missing submission_id or action"}), 400

        submission = Submission.query.get(submission_id)
        if not submission:
            return jsonify({"msg": "Submission not found"}), 404

        
        if action.lower() == 'view':
            # Redirect to the submission details page for the auditor
            return redirect(url_for('auditor_submission_details', submission_id=submission_id))
        
        elif action.lower() == 'approve':
            submission.Status = 2  # Or another value representing 'approved'
            # Send email notification to the bank (implement send_email_to_bank)
            send_email_to_bank(submission_id, 'approved', feedback)


        elif action.lower() == 'reject':
            submission.Status = 3  # Or another value representing 'rejected'
            # Send email notification to the bank
            send_email_to_bank(submission_id, 'rejected', feedback)

        else:
            return jsonify({"msg": "Invalid action value"}), 400
        
        if action.lower() in ('approve', 'reject'):
            # Reset the ReviewingAuditorID to null after approval or rejection
            submission.ReviewingAuditorID = None 

        # Store the feedback (this is the main change)
        submission.Feedback = feedback  
        db.session.commit()

        return jsonify({"msg": "Submission status updated successfully"}), 200
    

# New route to display submission details to the auditor
@app.route("/auditor/submissions/<int:submission_id>", methods=["GET"])
@jwt_required()
def auditor_submission_details(submission_id):
    current_user_id = get_jwt_identity()
    try:
        submission = Submission.query.get(submission_id)
        if not submission:
            return jsonify({"msg": "Submission not found"}), 404
        
        # Check if the submission is already being reviewed by another auditor
        if submission.ReviewingAuditorID is not None and submission.ReviewingAuditorID != current_user_id:
            return jsonify({"msg": "Submission is currently being reviewed by another auditor."}), 400
    
        # Set the ReviewingAuditorID to the current auditor's ID
        submission.ReviewingAuditorID = current_user_id
        db.session.commit()

        # Fetch associated metrics
        social_metrics = SocialMetrics.query.filter_by(SubmissionID=submission_id).first()
        environmental_metrics = EnvironmentalMetrics.query.filter_by(SubmissionID=submission_id).first()
        governance_metrics = GovernanceMetrics.query.filter_by(SubmissionID=submission_id).first()

        # Format the data for the frontend
        submission_data = {
            "submission": submission.as_dict(),
            "social_metrics": social_metrics.as_dict() if social_metrics else {},
            "environmental_metrics": environmental_metrics.as_dict() if environmental_metrics else {},
            "governance_metrics": governance_metrics.as_dict() if governance_metrics else {}
        }

        return jsonify(submission_data), 200
    except Exception as e:
        print(f"Error fetching submission details: {e}")
        return jsonify({"msg": "Failed to fetch submission details"}), 500  
    

@app.route("/auditor/submissions/<int:submission_id>/feedback", methods=["POST"])
@jwt_required()
def submit_auditor_feedback(submission_id):
    try:
        submission = Submission.query.get(submission_id)
        if not submission:
            return jsonify({"msg": "Submission not found"}), 404

        feedback = request.json.get('feedback')
        
        # Store the feedback (you might need to add a Feedback column to your Submission model)
        submission.Feedback = feedback  
        db.session.commit()

        return jsonify({"msg": "Feedback submitted successfully"}), 200
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({"msg": "Failed to submit feedback"}), 500


@app.route("/register", methods=["POST"])
def register():
    if request.method == "POST":
        email = request.json.get("email")
        password = request.json.get("password")
        name = request.json.get("name")
        role = request.json.get('role')  # Get the selected role from the frontend

        # Validate the role (ensure it's one of the allowed roles)
        if role not in [role.value for role in UserRole]:
            return jsonify({"success": False, "message": "Invalid role"}), 400


        # Check if the email is already in use
        existing_user = User.query.filter_by(Email=email).first()
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email is already in use"
            }), 400

        hashed_password = generate_password_hash(password)
        private_key, address = account.generate_account()

        #add funds to user account
        transamount = 1000000  #0.3 algos as algo account must have a minimum of 0.1 algo, gas fees are 0.0001 so users have 300 free transactions
        algonote = {"algo top-up": transamount}

        confirmedTxn = first_transaction_example(ecochainPK, ecochainAddress, address, transamount,  algonote)
        
        new_user = User(Email=email, 
                        Password=hashed_password, 
                        Name = name,
                        Role=UserRole(role),  # Assign the selected role
                        AlgorandPrivateKey = private_key,
                        AlgorandAddress = address
                        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            access_token = create_access_token(identity=new_user.UserID)
            print("Access token created: ", access_token)
            return jsonify(access_token=access_token, success=True), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "An error occurred while registering the user"
            }), 500

@app.route("/update_org", methods=["POST"])
@jwt_required()
def update_org():
    if request.method == "POST":
        location = request.json.get("location")
        industry = request.json.get("industry")
        size = request.json.get("size")
        description = request.json.get("description")

        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Update the fields
        user.Location = location
        user.Size = size
        user.Industry = industry
        user.Description = description
        # Commit the changes to the database
        db.session.commit()
        return jsonify(success=True), 200


@app.route("/start_submission", methods=["GET"])
@jwt_required()
def start_submission():
    if request.method == "GET":
        
        # Check if a submission ID already exists in the session
        submission_id = session.get('submission_id')
        print("in here")
        if not submission_id:
            # If not, create a new Submission record
            current_user_id = get_jwt_identity()
            new_submission = Submission(UserID=current_user_id,
                                        Status=0)
            
            db.session.add(new_submission)
            db.session.commit()
            submission_id = new_submission.SubmissionID
            session['submission_id'] = submission_id
        
        # Return a success message along with the submission ID.
        return jsonify({
            "success": True, 
            "message": "Submission started successfully",
            "submission_id": submission_id
        }), 200

    else:
        # Handle GET or other methods if necessary.
        return jsonify({
            "status": "info", 
            "message": "GET request for start_submission"
        }), 200

@app.route("/input_submission/<submission_id>", methods=["POST"])
@jwt_required()
def input_submission(submission_id):
   
    user_id = get_jwt_identity()
    data = request.get_json()
    print(data)

    first_name = data.get("FirstName")
    last_name = data.get("LastName")
    start_period_str = data.get("StartPeriod")
    end_period_str = data.get("EndPeriod")

    start_period = datetime.strptime(start_period_str, '%Y-%m-%d').date()
    end_period = datetime.strptime(end_period_str, '%Y-%m-%d').date()
    
    existing_info = Submission.query.filter_by(SubmissionID=submission_id).first()
    
    if existing_info:
        existing_info.FirstName = first_name
        existing_info.LastName = last_name
        existing_info.StartPeriod = start_period
        existing_info.EndPeriod = end_period
    else:
        new_info = Submission(
            FirstName=first_name,
            LastName=last_name,
            StartPeriod=start_period,
            EndPeriod=end_period,
            SubmissionID=submission_id,
            UserID = user_id
        )
        db.session.add(new_info)
    
    try:
        db.session.commit()
        return jsonify({
            "success": True, 
            "message": "User details added successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

def nullify_empty_string(string):
    if string == "":
        return None
    else:
        return string

@app.route("/input_social_metrics/<submission_id>", methods=["POST"])
@jwt_required()
def input_social_metrics(submission_id):
    data = request.get_json()
    print(data)

    # Assuming your SocialMetrics model is correctly defined with all the new metrics
    existing_metric = SocialMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        # Update the existing entry
        for key, value in data.items():
            # Apply nullify_empty_string to each value
            setattr(existing_metric, key, nullify_empty_string(value)) 
    else:
        # Create a new entry
        new_metric = SocialMetrics(**data, SubmissionID=submission_id)
        db.session.add(new_metric)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Social metrics added/updated successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/input_environmental_metrics/<submission_id>", methods=["POST"])
@jwt_required()
def input_environmental_metrics(submission_id):
    data = request.get_json()
    print(data)

    # Assuming your EnvironmentalMetrics model is correctly defined with all the new metrics
    existing_metric = EnvironmentalMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        # Update the existing entry
        for key, value in data.items():
            # Apply nullify_empty_string to each value
            setattr(existing_metric, key, nullify_empty_string(value)) 
    else:
        # Create a new entry
        new_metric = EnvironmentalMetrics(**data, SubmissionID=submission_id)
        db.session.add(new_metric)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Environmental metrics added/updated successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/input_governance_metrics/<submission_id>", methods=["POST"])
@jwt_required()
def input_governance_metrics(submission_id):
    data = request.get_json()
    print(data)

    # Assuming your GovernanceMetrics model is correctly defined with all the new metrics
    existing_metric = GovernanceMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        # Update the existing entry
        for key, value in data.items():
            # Apply nullify_empty_string to each value
            setattr(existing_metric, key, nullify_empty_string(value)) 
    else:
        # Create a new entry
        new_metric = GovernanceMetrics(**data, SubmissionID=submission_id)
        db.session.add(new_metric)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Governance metrics added/updated successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    

def get_bank_name_from_submission(submission_id):
  """
  Retrieves the bank name associated with a submission.

  Args:
      submission_id (int): The ID of the submission.

  Returns:
      str: The name of the bank.
  """
  try:
    # Get the submission
    submission = Submission.query.get(submission_id)
    if submission is None:
      return None  # Or handle the case where the submission is not found

    # Get the user associated with the submission
    user = User.query.get(submission.UserID)
    if user is None:
      return None  # Or handle the case where the user is not found

    # Return the user's name as the bank name
    return user.Name

  except Exception as e:
    # Handle any potential errors (e.g., database errors)
    print(f"Error retrieving bank name: {e}")
    return None  # Or handle the error appropriately


def detect_outliers(submission_data, bank_name, historical_data):
 
    outliers = []

    # Access the "Mean" and "Standard Deviation" dictionaries once
    mean_data = historical_data[bank_name].get("Mean", {})
    std_dev_data = historical_data[bank_name].get("Standard Deviation", {})

    for metric_type, metrics in submission_data.items():
        if metric_type == 'EnvironmentalMetrics' and metrics:
            for metric in ["Scope1", "Scope2", "Scope3", "TotalNonRenewableEnergy", "TotalRenewableEnergy", "WasteToLandfill", "RecycledWaste", "TotalWaterConsumption"]:  # List of metrics to check
                try:
                    # Get the value from the metrics dictionary
                    numeric_value = float(metrics[metric])  # Corrected line

                    # Access the mean and standard deviation for the current metric
                    mean = mean_data.get(metric)  
                    std = std_dev_data.get(metric)

                    if mean is not None and std is not None:
                        difference = abs(numeric_value - mean)
                        threshold = 2 * std
                        print(f"  Difference: {difference}, Threshold: {threshold}")  # Print difference and threshold
                        
                        if difference >= threshold:
                            outliers.append(f"{metric_type}: {metric}")
                            print(f"  Outlier detected!")
                            
                
                except ValueError:
                    print(f"Non-numeric value encountered for {metric_type}: {metric}")
                except AttributeError:
                    print(f"Metric {metric} not found in {metric_type}")

    return outliers



@app.route("/trans/<submission_id>", methods=["POST"])
@jwt_required()
def trans(submission_id):
    print("in server")

    submission = Submission.query.get(submission_id)
    

    # List of models to fetch data from
    models = [SocialMetrics, EnvironmentalMetrics, GovernanceMetrics]  # Updated models

    environmental_metrics_obj = EnvironmentalMetrics.query.filter_by(SubmissionID=submission_id).first()
    
    if environmental_metrics_obj:
        environmental_metrics = {
            "Scope1": environmental_metrics_obj.Scope1,
            "Scope2": environmental_metrics_obj.Scope2,
            "Scope3": environmental_metrics_obj.Scope3,
            "TotalNonRenewableEnergy": environmental_metrics_obj.TotalNonRenewableEnergy,
            "TotalRenewableEnergy": environmental_metrics_obj.TotalRenewableEnergy,
            "WasteToLandfill": environmental_metrics_obj.WasteToLandfill,
            "RecycledWaste": environmental_metrics_obj.RecycledWaste,
            "TotalWaterConsumption": environmental_metrics_obj.TotalWaterConsumption
        }
    else:
        environmental_metrics = {}  # Handle case where no metrics are found
    
    # Define submission_data 
    submission_data = {'EnvironmentalMetrics': environmental_metrics}

    # Fetch metrics and create a combined dictionary
    data = {}
    grouped_metrics = {}
    for model in models:
        model_name = model.__name__
        metric = model.query.filter_by(SubmissionID=submission_id).first()
        if metric:
            # Get the column names and values for the metric using introspection
            columns = {column.name: getattr(metric, column.name) for column in inspect(model).columns}
            data.update(columns)
            grouped_metrics[model_name] = columns

    # Remove the SubmissionID key as it's common and not needed in the output
    data.pop('SubmissionID', None)

    user_id = get_jwt_identity() # Get the user's ID from the JWT token

    # Load historical data from JSON file
    with open('historical_data.json', 'r') as f:
        historical_data = json.load(f)

    # Get the bank name from the submission data (replace with your actual implementation)
    bank_name = get_bank_name_from_submission(submission_id)  

    # Detect outliers (pass only environmental_metrics)
    print("submission_data:", submission_data)  
    print("bank_name:", bank_name)  
    outliers = detect_outliers(submission_data, bank_name, historical_data)
    print("Detected outliers:", outliers) 

    if outliers:
        # Handle outliers (e.g., flag for auditor review)
        submission.Status = 1  # Or another value representing 'flagged'
        # Store outlier details
        submission.Outliers = ', '.join(outliers)

        # Notify the auditor (implement send_email_to_auditor)
        # send_email_to_auditor(submission_id, bank_name, outliers)

        return jsonify({
            "success": False,
            "message": "Submission flagged for review due to outliers. Please wait for auditor approval."
        }), 400  # Or another appropriate status code
    
    else:
        # Proceed with your existing logic to send data to BaaS
        submission.Status = 2  # Pending (or another suitable value)

    db.session.commit()
    
    # Send data to BaaS platform 
    baas_response = send_data_to_baas(grouped_metrics, submission_id, user_id) 
    if not baas_response["success"]:
        return jsonify({
            "success": False,
            "message": "Failed to send data to BaaS platform"
            }), 500
        
    return jsonify({
    "success": True,
    "message": "Data sent to BaaS platform. Waiting for blockchain confirmation."
    }), 200
    

def send_email_to_auditor(submission_id, bank_name, outliers):
    """
    Sends an email notification to all auditors about detected outliers.

    Args:
        submission_id (int): The ID of the submission.
        bank_name (str): The name of the bank.
        outliers (list): The list of outlier metrics.
    """
    try:
        # Fetch email addresses of all auditors
        auditors = User.query.filter_by(Role=UserRole.auditor).all()
        if not auditors:
            print("No auditors found in the database.")
            return

        auditor_emails = [auditor.Email for auditor in auditors]

        # Construct the email message
        subject = f"EcoChain: Outliers detected for {bank_name} submission (ID: {submission_id})"
        body = f"Outliers detected in the following metrics:\n\n{', '.join(outliers)}\n\nPlease review the submission on the auditor dashboard."

        # Send the email to all auditors
        msg = Message(subject, sender=('Ecochain', 'ecochain0@gmail.com'), recipients=auditor_emails)
        msg.body = body
        mail.send(msg)

    except Exception as e:
        print(f"Error sending email to auditors: {e}")



@app.route("/mint/<submission_id>", methods=["POST"])
@jwt_required()
def mint(submission_id):
    print("in server")

    submission = Submission.query.get(submission_id)
    
    # List of models to fetch data from
    models = [SocialMetrics, EnvironmentalMetrics, GovernanceMetrics]  # Updated models

    user_id = get_jwt_identity() # Get the user's ID from the JWT token

    # Fetch metrics and create a combined dictionary
    baas_tx_id = submission.BaaS_Tx_ID

    metric_metadata = {
        "baas_tx_id": baas_tx_id  # Correct dictionary syntax with colon
    }

    data = {}
    grouped_metrics = {}
    for model in models:
        model_name = model.__name__
        metric = model.query.filter_by(SubmissionID=submission_id).first()
        if metric:
            # Get the column names and values for the metric using introspection
            columns = {column.name: getattr(metric, column.name) for column in inspect(model).columns}
            data.update(columns)
            grouped_metrics[model_name] = columns


    private_key = ecochainPK
    my_address = ecochainAddress
    current_user = db.session.get(User, user_id)
    rec_address = current_user.AlgorandAddress
    rec_privateKey = current_user.AlgorandPrivateKey
    transamount = 0

    txid, confirmedTxn = first_transaction_example(private_key, my_address, rec_address, transamount, metric_metadata)

    # Check if confirmed_txn has the expected structure or keys
    if not confirmedTxn:
        return jsonify({
            "success": False,
            "message": "Failed to confirm the transaction"
        }), 500
    
    txidNFT, confirmed_txnNFT, created_asset = createASA(private_key, my_address, txid)


    if not confirmed_txnNFT:
        return jsonify({
        "success": False,
        "message": "Failed to confirm the transaction"
    }), 500


    signed_optin_txid, Opt_in_confirmed_txn = optinASA (rec_address,rec_privateKey,created_asset)

    if not Opt_in_confirmed_txn:
        return jsonify({
        "success": False,
        "message": "Failed to confirm the transaction"
    }), 500



    asa_receive_txid, user_recieved_confirm = transferASA (my_address, private_key, rec_address, created_asset)

    if not user_recieved_confirm:
        return jsonify({
        "success": False,
        "message": "Failed to confirm the transaction"
    }), 500



    NFTTransactionTransfer = asa_receive_txid
    AlgoTransaction = txid
    NFTTransactionMint = txidNFT
    NFTAsset = created_asset
    
    new_metric = Transaction(
            TransactionID=AlgoTransaction,
            NFTTransactionMintID=NFTTransactionMint,
            NFTTransactionTransferID = NFTTransactionTransfer,
            NFTAssetID=NFTAsset,
            SubmissionID=submission_id
    )
    
    try:
        db.session.add(new_metric)
        submission.Status = 3
        db.session.commit()
        user_email = current_user.Email 
        user_name = current_user.Name 
        user_algoadd = rec_address
        user_SRP = submission.StartPeriod
        user_ERP = submission.EndPeriod
        user_Date = submission.Date

        sendEmail(user_email, user_name, "EcoChain ESG Report", user_algoadd, AlgoTransaction, NFTAsset, grouped_metrics, user_SRP, user_ERP, user_Date)
        return jsonify({
            "success": True,  
            "message": "Transaction recorded successfully"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500
            
    
    
def send_data_to_baas(data, submission_id, user_id):


    url = 'https://blockapi.co.za/api/v1/blockchainTask'
    headers = {
        'accept': 'application/json',
        'X-API-KEY': '6t71phte5aahwbibthy3meqt6rdd6s',
        'Content-Type': 'application/json'
    }

    combined_data_id = f"{user_id}-{submission_id}"

    # Construct the payload using the submission_id as the dataId
    payload = {
        "dataSchemaName": "ESGSubmission",  
        "dataId": combined_data_id,
        "jsonPayload": data
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() 
        return {"success": True, "message": "Data sent to BaaS successfully"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error sending data to BaaS: {e}"}






# New route to handle the transaction complete webhook from BaaS
@app.route("/transaction_complete", methods=['POST'])
def transaction_complete_webhook():
    data = request.get_json()
    print(f"Webhook data received: {data}")

    combined_data_id = resolve_submission_id_from_baas_data(data) 

    if not combined_data_id:
        return jsonify({
            "success": False,
            "message": "Failed to resolve combined data ID from BaaS data"
        }), 400
    
    try:
        user_id, submission_id = combined_data_id.split('-')  # Decouple the IDs
        user_id = int(user_id)
        submission_id = int(submission_id)
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid combined data ID format"
        }), 400


    #Retrieve user information using the extracted user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            "success": False,
            "message": "User not found for this submission"
        }), 404

    #Fetch the submission record using submission_id 
    submission = Submission.query.get(submission_id)

    if not submission:
        return jsonify({
            "success": False,
            "message": "Submission not found"
        }), 404
    
    # Check if the BaaS transaction was successful
    if not data.get("BlockchainResults") or not data["BlockchainResults"][0].get("isSuccess"):
        # Handle BaaS transaction failure 
        submission.Status = 4  # Rejected at BaaS
        db.session.commit()

        return jsonify({
            "success": False,
            "message": "BaaS transaction failed."
        }), 500

    # BaaS transaction was successful

    # Extract transaction ID and other details from BaaS response 
    baas_tx_id = data["BlockchainResults"][0]["transactionId"]
    baas_tx_url = data["BlockchainResults"][0]["transactionExplorerUrl"]

    print(f"BaaS Transaction ID: {baas_tx_id}, BaaS Transaction URL: {baas_tx_url}")

    try:
        # Store BaaS transaction details in the Submission object
        submission.BaaS_Tx_ID = baas_tx_id
        submission.BaaS_Tx_URL = baas_tx_url

        db.session.commit()  # Commit the changes to the database

        return jsonify({
            "success": True,
            "message": "Transaction and NFT minting completed successfully",
            "baas_tx_id": baas_tx_id,
            "baas_tx_url": baas_tx_url
        }), 200

    except Exception as e:
        db.session.rollback()
        # Log the error for debugging
        print(f"Error processing webhook: {e}")
        return jsonify({
            "success": False,
            "message": "An error occurred while processing the webhook"
        }), 500

def resolve_submission_id_from_baas_data(data):
    return data.get("dataId")


# Use this protected decorator for all sensitive information
@app.route('/protected')
@jwt_required()
def protected_route():
    user_id = get_jwt_identity()
    current_user = db.session.get(User, user_id)
    return jsonify({
        "success": True,  
        "message": "You've successfully accessed a protected route",
        "id": current_user.UserID,
        "email" : current_user.Email
    }), 200

def sendEmail(recipient_email, recipient_name, subject, algoaddress, transaction_id, nft_id, metrics, startPeriod, endPeriod, reportSubDate):
    transaction_link = f"https://testnet.explorer.perawallet.app/tx/{transaction_id}"
    nft_link = f"https://testnet.explorer.perawallet.app/asset/{nft_id}"

    # Start constructing the email body
    body = f"Dear {recipient_name},\n\n"

    body += "Thank you for submitting your report. Below are the details of your submission and the metrics you provided:\n\n"
    body += f"Date of report submission: {reportSubDate}:\n"
    body += f"Reporting period start date: {startPeriod}:\n"
    body += f"Reporting period end date: {endPeriod}:\n\n"
    
    # Include the metrics in the email with headers
    for group, metric_data in metrics.items():
        body += f"{group}:\n"
        for key, value in metric_data.items():
            body += f"  - {key}: {value}\n"
        body += "\n"

    body += "\nAs part of our commitment to transparency and real-time verification, we have digital proofs available for your review. These are unique to your contribution and can be accessed anytime through the links provided below.\n\n"

    body += f"Your Unique Algorand Address:\n{algoaddress}\n"
    body += "(This address is unique to you, ensuring your contributions are securely recorded and accessible.)\n\n"

    body += f"Explore the specifics of your environmental, social, and governance (ESG) metrics that have been immutably recorded on the blockchain.\n{transaction_link}\n\n"

    body += f"Access your Non-Fungible Token (NFT), confirming your commitment to sustainable practices.\n{nft_link}\n\n"

    # Conclusion and sign-off
    body += "Your proactive steps towards sustainability are not just contributions; they are the building blocks of a greener, fairer, and more sustainable future for all. We are here to support and amplify your impact every step of the way.\n\n"

    body += "With sincere appreciation,\n\n"
    body += "The EcoChain Team\n"

    # Prepare and send the email
    msg = Message(subject, sender=('Ecochain', 'ecochain0@gmail.com'), recipients=[recipient_email])
    msg.body = body
    mail.send(msg)

    # You might want to handle the 'flash' messaging differently, based on where you call this function from.

def sendEmailBaaS(recipient_email, recipient_name, subject, algoaddress, nft_id, startPeriod, endPeriod, reportSubDate, baas_tx_id, baas_tx_url):
    nft_link = f"https://testnet.explorer.perawallet.app/asset/{nft_id}"

    # Start constructing the email body
    body = f"Dear {recipient_name},\n\n"

    body += "Thank you for submitting your report. Below are the details of your submission:\n\n"
    body += f"Date of report submission: {reportSubDate}:\n"
    body += f"Reporting period start date: {startPeriod}:\n"
    body += f"Reporting period end date: {endPeriod}:\n\n"

    body += "\nAs part of our commitment to transparency, we have securely stored your ESG metrics data on our Blockchain-as-a-Service (BaaS) platform and minted an NFT as a certificate of your submission. You can access the details through the links provided below.\n\n"

    body += f"Your Unique Algorand Address:\n{algoaddress}\n"
    body += "(This address is unique to you, ensuring your contributions are securely recorded and accessible.)\n\n"

    body += f"BaaS Transaction ID: {baas_tx_id}\n\n"  # Include BaaS transaction ID
    body += f"View the BaaS transaction that records your ESG metrics data on the blockchain:\n{baas_tx_url}\n\n"

    body += f"Access your Non-Fungible Token (NFT), serving as a certificate of your ESG commitment:\n{nft_link}\n\n"

    # Conclusion and sign-off 
    body += "Your proactive steps towards sustainability are valuable. We appreciate your contribution to a greener, fairer, and more sustainable future.\n\n"

    body += "With sincere appreciation,\n\n"
    body += "The EcoChain Team\n"

    # Prepare and send the email
    msg = Message(subject, sender=('Ecochain', 'ecochain0@gmail.com'), recipients=[recipient_email])
    msg.body = body
    mail.send(msg)

def send_email_to_bank(submission_id, decision, feedback=None):
    """
    Sends an email notification to the bank about the auditor's decision.

    Args:
        submission_id (int): The ID of the submission.
        decision (str): The auditor's decision ('approved' or 'rejected').
        feedback (str, optional): The auditor's feedback. Defaults to None.
    """
    try:
        # Fetch the bank's email address from the submission
        submission = Submission.query.get(submission_id)
        if not submission:
            print("Submission not found.")
            return

        user = User.query.get(submission.UserID)
        if not user:
            print("User not found for this submission.")
            return

        bank_email = user.Email

        # Construct the email message
        subject = f"EcoChain: Your submission (ID: {submission_id}) has been {decision}"
        body = f"Your submission (ID: {submission_id}) has been {decision} by the auditor."
        if feedback:
            body += f"\n\nAuditor's feedback:\n{feedback}"

        # Send the email (using your existing email sending mechanism)
        msg = Message(subject, sender=('Ecochain', 'ecochain0@gmail.com'), recipients=[bank_email])
        msg.body = body
        mail.send(msg)

    except Exception as e:
        print(f"Error sending email to bank: {e}")

   
@app.route('/get_reports')
@jwt_required()
def get_reports():
    if request.method == "GET":
        #return json object with report data for current_user.companyID
        user_id = get_jwt_identity()
        current_user = db.session.get(User, user_id)
        return jsonify({
            "success": True,  
            "message": "You've successfully accessed report data",
            "id": current_user.CompanyID
        }), 200

@app.route('/get_dashboard')
@jwt_required()    
def get_dashboard_data():
    if request.method == "GET":
        user_id = get_jwt_identity()
        current_user = db.session.get(User, user_id)
        subs = Submission.query.filter_by(UserID = user_id).all()

        serialized_subs = [sub.as_dict() for sub in subs]

        return jsonify({
            "success": True,
            "id": current_user.UserID,
            "email" : current_user.Email,
            "name": current_user.Name,
            "algo_add" : current_user.AlgorandAddress,
            "location": current_user.Location,
            "industry" : current_user.Industry,
            "size": current_user.Size,
            "description" : current_user.Description,
            "submissions": serialized_subs
        }), 200
    
@app.route('/get_submission/<int:submission_id>')
@jwt_required()    
def get_submission(submission_id):
    try:
        submission = Submission.query.filter_by(SubmissionID=submission_id).one()
        full_name = f"{submission.FirstName} {submission.LastName}"
        current_user = db.session.query(User).get(submission.UserID)

        return jsonify({
            "success": True,
            "company" : current_user.Name,
            "full_name": full_name,
            "start_period": submission.StartPeriod,
            "end_period": submission.EndPeriod,
        }), 200

    except NoResultFound:
        return jsonify({
            "success": False,
            "error": "Submission not found"
        }), 404
    
@app.route('/get_success_page/<int:submission_id>')
@jwt_required()    
def get_success_page(submission_id):
    if request.method == "GET":  
        user_id = get_jwt_identity()
        current_user = db.session.get(User, user_id)
        transaction = db.session.query(Transaction).filter(Transaction.SubmissionID == submission_id).first()

        if transaction:  # Check if transaction exists
            return jsonify({
                "success": True,
                "id": current_user.UserID,
                "transaction_id": transaction.TransactionID,
                "nft_id": transaction.NFTAssetID
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Transaction not found for this submission"
            }), 404


def generate_dummy_data():
    with app.app_context():
        
        admin_user = User(
            Email='admin@example.com',  
            Password=generate_password_hash('adminpassword'),  
            Name='Admin User',  
            Role=UserRole.admin
        )
        db.session.add(admin_user)

        # Create other regular users 
        users = []  # Initialize an empty list for regular users
        for _ in range(5): 
            user = User(
                Email=fake.email(),
                Password=generate_password_hash('password'),
                Name=fake.name()
            )
            db.session.add(user)
            users.append(user)  # Add the new user to the list

        db.session.commit()  # Commit the user creation

        # Add dummy submissions
        submissions = []
        for user in users:
            for _ in range(3):
                submission = Submission(
                    FirstName=fake.first_name(),
                    LastName=fake.last_name(),
                    Date=fake.date_this_decade(),
                    Year=fake.year(),
                    StartPeriod=fake.date_this_decade(),
                    EndPeriod=fake.date_this_decade(),
                    Score=random.uniform(0, 100), 
                    Status=random.choice([0, 1, 2]), 
                    UserID=user.UserID
                )
                db.session.add(submission)
                submissions.append(submission)
 
        db.session.commit()

        # Add dummy metrics (using new models)
        for sub in submissions:
            # Social Metrics
            db.session.add(SocialMetrics(
                CustomerComplaints=fake.random_int(min=0, max=100),
                CustomerSatisfactionScore=fake.pyfloat(min_value=0, max_value=100),

                # Human Capital Development
                PermanentEmployeesMale=fake.random_int(min=0, max=1000),
                PermanentEmployeesFemale=fake.random_int(min=0, max=1000),
                TemporaryEmployees=fake.random_int(min=0, max=500),
                FullTimeEmployeesMale=fake.random_int(min=0, max=1000),
                FullTimeEmployeesFemale=fake.random_int(min=0, max=1000),
                PartTimeEmployeesMale=fake.random_int(min=0, max=200),
                PartTimeEmployeesFemale=fake.random_int(min=0, max=200),
                EmployeeTurnoverRate=fake.pyfloat(min_value=0, max_value=100),
                TrainingAndDevelopmentSpendPerEmployee=fake.pyfloat(min_value=0, max_value=10000),
                LostTimeInjuryFrequencyRate=fake.pyfloat(min_value=0, max_value=10),
                EmployeeEngagementScore=fake.pyfloat(min_value=0, max_value=100),
                GenderPayGap=fake.word(),  # Assuming a categorical value (e.g., "No Gap", "Small Gap", etc.)

                # Training, Bursaries & Learnerships
                TotalTrainingSpend=fake.pyfloat(min_value=0, max_value=1000000),
                TotalTrainingSpendBasicPayroll=fake.pyfloat(min_value=0, max_value=100),
                TrainingSpendPerEmployee=fake.pyfloat(min_value=0, max_value=10000),
                TrainingBeneficiaries=fake.random_int(min=0, max=1000),
                AverageTrainingHours=fake.pyfloat(min_value=0, max_value=40),
                TrainingSpendBlackEmployees=fake.pyfloat(min_value=0, max_value=1000000),
                TrainingSpendBlackFemaleEmployees=fake.pyfloat(min_value=0, max_value=1000000),
                TrainingSpendBlackFemaleEmployeesWithDisabilities=fake.pyfloat(min_value=0, max_value=1000000),
                TrainingSpendFemaleEmployees=fake.pyfloat(min_value=0, max_value=1000000),
                TrainingSpendFemaleEmployeesWithDisabilities=fake.pyfloat(min_value=0, max_value=1000000),
                TotalInternalBursaries=fake.random_int(min=0, max=100),
                ActualPaymentOnBursaries=fake.pyfloat(min_value=0, max_value=1000000),
                LearnershipOfferedToUnemployedAndDisabled=fake.random_int(min=0, max=50),
                LearnershipsAndInternships=fake.random_int(min=0, max=100),
                LearnershipStudentsAdsorbedIntoEmployment=fake.random_int(min=0, max=50),
                NumberEmployeesAttendedManagementLeadership=fake.random_int(min=0, max=200),

                # Graduate Programme
                TotalGraduateProgramIntake=fake.random_int(min=0, max=50),
                GraduateProgramIntakeFemale=fake.random_int(min=0, max=50),
                TotalGraduateProgramAbsorption=fake.random_int(min=0, max=50),
                GraduateProgramAbsorptionRate=fake.pyfloat(min_value=0, max_value=100),

                # Employee Profile & Movements
                TotalNumberOfEmployeesBeginningYear=fake.random_int(min=1000, max=5000),
                TotalNumberOfEmployeesEndOfYear=fake.random_int(min=1000, max=5000),
                NewHiresPermanentEmployees=fake.random_int(min=0, max=200),
                NewHiresPermanentEmployeesWith3MonthsProbation=fake.random_int(min=0, max=200),
                TerminationsPermanentEmployees=fake.random_int(min=0, max=100),  # Added
                Resignations=fake.random_int(min=0, max=100),  # Added
                VoluntaryRetrenchments=fake.random_int(min=0, max=50),  # Added
                InvoluntaryRetrenchments=fake.random_int(min=0, max=50),  # Added
                Dismissals=fake.random_int(min=0, max=20),  # Added
                NonTemporaryEmployees=fake.random_int(min=800, max=4500),  # Added
                TotalEmployeeInternalTransfers=fake.random_int(min=0, max=100),  # Added
                VacanciesFilledByInternalCandidates=fake.random_int(min=0, max=100),  # Added
                InternalPromotionalSuccessRate=fake.pyfloat(min_value=0, max_value=100),  # Added (percentage)
                TotalEmployeePromotions=fake.random_int(min=0, max=100),  # Added
                NewHiresWomen=fake.random_int(min=0, max=100),

                # Per Region
                SouthAfricanEmployeesMale=fake.random_int(min=0, max=1000),
                SouthAfricanEmployeesFemale=fake.random_int(min=0, max=1000),
                InternationalEmployeesMale=fake.random_int(min=0, max=100),
                InternationalEmployeesFemale=fake.random_int(min=0, max=100),

                # Employee Equity Demographics
                BlackFemaleEmployees=fake.random_int(min=0, max=1000),
                ColouredEmployees=fake.random_int(min=0, max=500),
                IndianEmployees=fake.random_int(min=0, max=500),
                AsianEmployees=fake.random_int(min=0, max=200),
                WhiteEmployees=fake.random_int(min=0, max=1000),
                MaleEmployees=fake.random_int(min=0, max=2000),
                FemaleEmployees=fake.random_int(min=0, max=2000),
                DisabilityRepresentationNumberOfEmployees=fake.random_int(min=0, max=100),

                # Employee Age
                LessThan20YearsMale=fake.random_int(min=0, max=50),
                LessThan20YearsFemale=fake.random_int(min=0, max=50),
                Between20And29YearsMale=fake.random_int(min=0, max=500),
                Between20And29YearsFemale=fake.random_int(min=0, max=500),
                Between30And39YearsMale=fake.random_int(min=0, max=500),
                Between30And39YearsFemale=fake.random_int(min=0, max=500),
                Between40And49YearsMale=fake.random_int(min=0, max=300),
                Between40And49YearsFemale=fake.random_int(min=0, max=300),
                Between50And59YearsMale=fake.random_int(min=0, max=200),
                Between50And59YearsFemale=fake.random_int(min=0, max=200),
                Between60And69YearsMale=fake.random_int(min=0, max=100),
                Between60And69YearsFemale=fake.random_int(min=0, max=100),
                Over69YearsMale=fake.random_int(min=0, max=50),
                Over69YearsFemale=fake.random_int(min=0, max=50),

                # Employee Tenure
                TenureLessThan1Year=fake.random_int(min=0, max=200),
                Tenure1To3Years=fake.random_int(min=0, max=500),
                Tenure4To6Years=fake.random_int(min=0, max=300),
                Tenure7To9Years=fake.random_int(min=0, max=200),
                Tenure10To20Years=fake.random_int(min=0, max=300),
                Tenure21To30Years=fake.random_int(min=0, max=100),
                Tenure31To40Years=fake.random_int(min=0, max=50),
                TenureMoreThan40Years=fake.random_int(min=0, max=20),

                # Top Management
                TopManagementTotalNumber=fake.random_int(min=10, max=50),
                TopManagementMaleEmployees=fake.random_int(min=0, max=30),
                TopManagementFemaleEmployees=fake.random_int(min=0, max=20),
                TopManagementBlackMaleEmployees=fake.random_int(min=0, max=20),
                TopManagementBlackFemaleEmployees=fake.random_int(min=0, max=10),
                TopManagementAfricanEmployees=fake.random_int(min=0, max=30),
                TopManagementColouredEmployees=fake.random_int(min=0, max=10),
                TopManagementIndianEmployees=fake.random_int(min=0, max=10),
                TopManagementAsianEmployees=fake.random_int(min=0, max=5),
                TopManagementWhiteEmployees=fake.random_int(min=0, max=15),
                TopManagementDisabledEmployees=fake.random_int(min=0, max=5),

                # Senior Management
                SeniorManagementTotalNumber=fake.random_int(min=50, max=200),
                SeniorManagementMaleEmployees=fake.random_int(min=0, max=100),
                SeniorManagementFemaleEmployees=fake.random_int(min=0, max=100),
                SeniorManagementBlackMaleEmployees=fake.random_int(min=0, max=80),
                SeniorManagementBlackFemaleEmployees=fake.random_int(min=0, max=60),
                SeniorManagementACIEmployees=fake.random_int(min=0, max=100), 
                SeniorManagementColouredEmployees=fake.random_int(min=0, max=40),
                SeniorManagementIndianEmployees=fake.random_int(min=0, max=40),
                SeniorManagementAsianEmployees=fake.random_int(min=0, max=20),
                SeniorManagementWhiteEmployees=fake.random_int(min=0, max=60),
                SeniorManagementDisabledEmployees=fake.random_int(min=0, max=20),

                # Middle Management
                MiddleManagementTotalNumber=fake.random_int(min=200, max=500),
                MiddleManagementMaleEmployees=fake.random_int(min=100, max=300),
                MiddleManagementFemaleEmployees=fake.random_int(min=100, max=200),
                MiddleManagementBlackEmployees=fake.random_int(min=150, max=400),
                MiddleManagementACIEmployees=fake.random_int(min=50, max=100),
                MiddleManagementColouredEmployees=fake.random_int(min=20, max=60),
                MiddleManagementIndianEmployees=fake.random_int(min=20, max=60),
                MiddleManagementAsianEmployees=fake.random_int(min=10, max=30),
                MiddleManagementWhiteEmployees=fake.random_int(min=50, max=150),
                MiddleManagementDisabledEmployees=fake.random_int(min=10, max=50),

                # Junior Management
                JuniorManagementTotalNumber=fake.random_int(min=500, max=1000),
                JuniorManagementMaleEmployees=fake.random_int(min=200, max=500),
                JuniorManagementFemaleEmployees=fake.random_int(min=300, max=500),
                JuniorManagementBlackMaleEmployees=fake.random_int(min=150, max=400),
                JuniorManagementBlackFemaleEmployees=fake.random_int(min=200, max=400),
                JuniorManagementACIEmployees=fake.random_int(min=100, max=200),
                JuniorManagementColouredEmployees=fake.random_int(min=50, max=100),
                JuniorManagementIndianEmployees=fake.random_int(min=50, max=100),
                JuniorManagementAsianEmployees=fake.random_int(min=25, max=50),
                JuniorManagementWhiteEmployees=fake.random_int(min=100, max=200),
                JuniorManagementDisabledEmployees=fake.random_int(min=25, max=100),

                # Semi-Skilled
                SemiSkilledTotalNumber=fake.random_int(min=300, max=800),
                SemiSkilledFemaleEmployees=fake.random_int(min=100, max=400),
                SemiSkilledBlackMaleEmployees=fake.random_int(min=100, max=300),
                SemiSkilledBlackFemaleEmployees=fake.random_int(min=100, max=300),
                SemiSkilledACIEmployees=fake.random_int(min=50, max=150),
                SemiSkilledColouredEmployees=fake.random_int(min=30, max=80),
                SemiSkilledIndianEmployees=fake.random_int(min=30, max=80),
                SemiSkilledAsianEmployees=fake.random_int(min=15, max=40),
                SemiSkilledWhiteEmployees=fake.random_int(min=50, max=150),
                SemiSkilledDisabledEmployees=fake.random_int(min=15, max=40),

                # Unskilled
                UnskilledTotalNumber=fake.random_int(min=100, max=300),
                UnskilledFemaleEmployees=fake.random_int(min=50, max=150),
                UnskilledBlackMaleEmployees=fake.random_int(min=30, max=100),
                UnskilledBlackFemaleEmployees=fake.random_int(min=40, max=100),
                UnskilledACIEmployees=fake.random_int(min=20, max=60),
                UnskilledColouredEmployees=fake.random_int(min=10, max=30),
                UnskilledIndianEmployees=fake.random_int(min=10, max=30),
                UnskilledAsianEmployees=fake.random_int(min=5, max=15),
                UnskilledWhiteEmployees=fake.random_int(min=20, max=60),
                UnskilledDisabledEmployees=fake.random_int(min=5, max=15),


                # Financial Inclusion
                MortgageLoansGranted=fake.random_int(min=0, max=1000),
                MortgageLoansValueTotal=fake.pyfloat(min_value=0, max_value=100000000),  # Example: in Rands
                MortgageLoansAffordableHousingTotal=fake.random_int(min=0, max=500),
                MortgageLoansAffordableHousingValueTotal=fake.pyfloat(min_value=0, max_value=50000000),  # Example: in Rands

                # Physical Footprint
                Outlets=fake.random_int(min=10, max=100),
                ATMs=fake.random_int(min=50, max=500),
                POSDevices=fake.random_int(min=100, max=1000),
                TotalClients=fake.random_int(min=10000, max=1000000),
                DigitallyActiveClients=fake.random_int(min=5000, max=500000),

                # Suppliers
                TotalNumberSuppliers=fake.random_int(min=100, max=1000),
                TotalProcurementSpend=fake.pyfloat(min_value=1000000, max_value=100000000),  # Example: in Rands
                TotalProcurementSpendExemptMicroenterprises=fake.pyfloat(min_value=0, max_value=5000000),
                TotalProcurementSpendQualifyingSmallEnterprises=fake.pyfloat(min_value=0, max_value=10000000),
                TotalProcurementSpend51PercentBlackOwned=fake.pyfloat(min_value=0, max_value=50000000),
                TotalProcurementSpend30PercentBlackOwned=fake.pyfloat(min_value=0, max_value=20000000),
                LocalProcurementSpend=fake.pyfloat(min_value=0, max_value=80000000),

                # Regulators
                TotalEnvironmentalIncidents=fake.random_int(min=0, max=10),
                TotalEnvironmentalFines=fake.pyfloat(min_value=0, max_value=1000000),

                SubmissionID=sub.SubmissionID
            ))

            # Environmental Metrics
            db.session.add(EnvironmentalMetrics(
                TotalEnergyUse=fake.pyfloat(min_value=0, max_value=1000000),
                TotalRenewableEnergy=fake.pyfloat(min_value=0, max_value=1000000),
                TotalNonRenewableEnergy=fake.pyfloat(min_value=0, max_value=1000000),
                NonRenewableEnergySources=fake.sentence(nb_words=6),  # Example: comma-separated list of sources

                # Greenhouse gas emissions
                CarbonEmissions=fake.pyfloat(min_value=0, max_value=1000000),
                CarEmissions=fake.pyfloat(min_value=0, max_value=500000),
                RefrigerantGasEmissions=fake.pyfloat(min_value=0, max_value=100000),
                DieselGeneratorsEmissions=fake.pyfloat(min_value=0, max_value=50000),
                ElectricityEmissions=fake.pyfloat(min_value=0, max_value=800000),
                ATMEmissions=fake.pyfloat(min_value=0, max_value=100000),
                TotalIndirectEmissions=fake.pyfloat(min_value=0, max_value=500000),
                FlightEmissions=fake.pyfloat(min_value=0, max_value=200000),
                CashInTransitEmissions=fake.pyfloat(min_value=0, max_value=100000),
                CarRentalsEmissions=fake.pyfloat(min_value=0, max_value=50000),
                CloudComputingEmissions=fake.pyfloat(min_value=0, max_value=100000),
                CourierEmissions=fake.pyfloat(min_value=0, max_value=50000),
                PaperUsageEmissions=fake.pyfloat(min_value=0, max_value=20000),
                WasteDisposalEmissions=fake.pyfloat(min_value=0, max_value=50000),
                EmployeeCommutingEmissions=fake.pyfloat(min_value=0, max_value=200000),
                ElectricityTransmissionLossesEmissions=fake.pyfloat(min_value=0, max_value=100000),
                CarbonEmissionsPerMeterSquared=fake.pyfloat(min_value=0, max_value=100),
                Scope1=fake.pyfloat(min_value=0, max_value=100000),
                Scope2=fake.pyfloat(min_value=0, max_value=100000),
                Scope3=fake.pyfloat(min_value=0, max_value=100000),

                # Waste Management
                TotalWaste=fake.pyfloat(min_value=0, max_value=100000),  # Example: in kg
                RecycledWaste=fake.pyfloat(min_value=0, max_value=100000),
                WasteToLandfill=fake.pyfloat(min_value=0, max_value=100000),
                SubmissionID=sub.SubmissionID
            ))

            # Governance Metrics
            db.session.add(GovernanceMetrics(
                NumberOfBoardMembers=fake.random_int(min=5, max=20),
                IndependentNonExecutiveDirectors=fake.random_int(min=2, max=10),
                ExecutiveDirectors=fake.random_int(min=1, max=5),
                NonExecutiveDirectors=fake.random_int(min=3, max=15),
                IndependentBoardChairman=fake.random_element(elements=('Yes', 'No')),
                BlackACIExecutiveBoardMembers=fake.random_int(min=0, max=5),
                BlackACIWomenExecutiveBoardMembers=fake.random_int(min=0, max=3),
                BlackACIIndependentNonExecutiveBoardMembers=fake.random_int(min=0, max=8),

                TotalNumberOfBoardMeetings=fake.random_int(min=4, max=12),  # Assuming number of meetings per year
                BoardTrainingHours=fake.pyfloat(min_value=0, max_value=40),  # Assuming hours per year

                WhiteMales=fake.random_int(min=0, max=1000),
                WhiteFemales=fake.random_int(min=0, max=1000),
                ACIFemales=fake.random_int(min=0, max=1000),
                ACIMales=fake.random_int(min=0, max=1000),
                NonSABoardMembers=fake.random_int(min=0, max=5),

                BoardMembersLessThan1Year=fake.random_int(min=0, max=3),
                BoardMembers1To3Years=fake.random_int(min=0, max=5),
                BoardMembers4To6Years=fake.random_int(min=0, max=5),
                BoardMembers7To9Years=fake.random_int(min=0, max=3),
                BoardMembersMoreThan9Years=fake.random_int(min=0, max=2),
                BoardMembers40To49YearsAge=fake.random_int(min=0, max=5),
                BoardMembers50To59YearsAge=fake.random_int(min=0, max=8),
                BoardMembers60To69YearsAge=fake.random_int(min=0, max=5),
                BoardMembers70Plus=fake.random_int(min=0, max=2),

                TotalNumberOfExcoMembers=fake.random_int(min=5, max=20),
                ExecutiveDirectorsExco=fake.random_int(min=1, max=5),
                PrescribedOfficers=fake.random_int(min=1, max=8),
                ExOfficioMembers=fake.random_int(min=0, max=3),
                WomenExcoMembers=fake.random_int(min=0, max=10),  # Assuming a count
                ACIExcoMembers=fake.random_int(min=0, max=10),  # Assuming a count

                ExcoMembers0To3Years=fake.random_int(min=0, max=8),
                ExcoMembers4To6Years=fake.random_int(min=0, max=5),
                ExcoMembers7To9Years=fake.random_int(min=0, max=3),

                ExcoMembers0To10Years=fake.random_int(min=0, max=10),
                ExcoMembers11To20Years=fake.random_int(min=0, max=5),
                ExcoMembersMoreThan20Years=fake.random_int(min=0, max=2),

                ControllingShareholder=fake.random_element(elements=('Yes', 'No')),
                MultipleShareholderRights=fake.random_element(elements=('Yes', 'No')),

                BeneficialSharesDirectOwnershipCEO=fake.random_int(min=0, max=100000),
                BeneficialSharesIndirectOwnershipCEO=fake.random_int(min=0, max=50000),
                TotalSharesOwnedCEO=fake.random_int(min=0, max=150000),

                BeneficialSharesDirectOwnershipCFO=fake.random_int(min=0, max=50000),
                BeneficialSharesIndirectOwnershipCFO=fake.random_int(min=0, max=25000),
                TotalSharesOwnedCFO=fake.random_int(min=0, max=75000),

                BeneficialSharesDirectOwnershipCOO=fake.random_int(min=0, max=50000),
                BeneficialSharesIndirectOwnershipCOO=fake.random_int(min=0, max=25000),
                TotalSharesOwnedCOO=fake.random_int(min=0, max=75000),

                Auditors=fake.company(),  # You might want to use a list of actual auditing firms
                AuditorTenure=fake.random_int(min=1, max=10),  # Years
                AuditFees=fake.pyfloat(min_value=100000, max_value=10000000),  # Example: in Rands

                ExecutiveRemunerationLinkedToESG=fake.boolean(),

                CEOGuaranteedPackage=fake.pyfloat(min_value=1000000, max_value=10000000),
                CEOShortTermIncentive=fake.pyfloat(min_value=0, max_value=5000000),
                CEOLongTermIncentive=fake.pyfloat(min_value=0, max_value=5000000),
                CEOTotalRemuneration=fake.pyfloat(min_value=1000000, max_value=15000000),
                CEOSharePriceAsMultipleOfGuaranteedPackage=fake.pyfloat(min_value=0.5, max_value=3),

                CFOGuaranteedPackage=fake.pyfloat(min_value=500000, max_value=5000000),
                CFOShortTermIncentive=fake.pyfloat(min_value=0, max_value=2500000),
                CFOLongTermIncentive=fake.pyfloat(min_value=0, max_value=2500000),
                CFOTotalRemuneration=fake.pyfloat(min_value=500000, max_value=7500000),

                COOGuaranteedPackage=fake.pyfloat(min_value=500000, max_value=5000000),
                COOShortTermIncentive=fake.pyfloat(min_value=0, max_value=2500000),
                COOLongTermIncentive=fake.pyfloat(min_value=0, max_value=2500000),
                COOTotalRemuneration=fake.pyfloat(min_value=500000, max_value=7500000),

                EmployeesCompletedEthicsTraining=fake.random_int(min=500, max=5000),
                ContractorsCompletedEthicsTraining=fake.random_int(min=100, max=1000),
                SubsidiariesCompletedEthicsTraining=fake.random_int(min=10, max=50),
                ReportedCases=fake.random_int(min=0, max=50),
                CasesStillUnderInvestigation=fake.random_int(min=0, max=20),
                SubstantiatedCases=fake.random_int(min=0, max=30),
                UnsubstantiatedCases=fake.random_int(min=0, max=20),
                DisciplinaryCasesReported=fake.random_int(min=0, max=30),
                DisciplinaryCasesConcluded=fake.random_int(min=0, max=25),
                EthicalDisciplinaryCasesConcluded=fake.random_int(min=0, max=20),
                OngoingDisciplinaryCases=fake.random_int(min=0, max=10),

                SystemAvailability=fake.pyfloat(min_value=90, max_value=100),  # Assuming percentage
                PrivacyRelatedIncidents=fake.random_int(min=0, max=10),
                PrivacyRelatedIncidentsReportedToRegulator=fake.random_int(min=0, max=5),

                SubmissionID=sub.SubmissionID
            ))

        db.session.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the Flask app.")
    parser.add_argument('--init', action='store_true', help='Initialize the database tables.')
    args = parser.parse_args()

    
    if args.init:
        print(" * Initializating database tables")
        with app.app_context():
            db.create_all()
            generate_dummy_data()
    else:
        port = int(os.environ.get('PORT', 5000))  # Get port from environment or default to 5000
        app.run(debug=True, host='0.0.0.0', port=port)  # Bind to 0.0.0.0
        
