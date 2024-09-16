from flask import Flask, request, redirect, url_for, flash, jsonify, session, send_from_directory, render_template_string  
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash, check_password_hash
import argparse
from models import db, User, Transaction, Submission, Peoplemetrics, Planetmetrics, Prosperitymetrics, Governancemetrics
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
from modelsBanks import db, User, Transaction, Submission, SocialMetrics, EnvironmentalMetrics, GovernanceMetrics

ecochainPK = "4pGX12svaEoBYqBX7WfriGIhUB3VjkeUofm6IM3Y+6b69JOah+47V6+PX/KeLfpDMv683zGwQ2R83pkdj7FwCA=="
ecochainAddress = "7L2JHGUH5Y5VPL4PL7ZJ4LP2IMZP5PG7GGYEGZD432MR3D5ROAEDKWFGRU"
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
            access_token = create_access_token(identity=user.UserID)
            print("Access token created: ", access_token)
            return jsonify(access_token=access_token, success=True), 200
        
        return jsonify({
            "success": False, 
            "message": "Invalid email or password"
            }), 401

@app.route("/register", methods=["POST"])
def register():
    if request.method == "POST":
        email = request.json.get("email")
        password = request.json.get("password")
        name = request.json.get("name")

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

    # Extract and process social metrics data from the request
    social_metrics_data = {
    'CustomerComplaints': data.get('CustomerComplaints'),
    'CustomerSatisfactionScore': data.get('CustomerSatisfactionScore'),

    'PermanentEmployeesMale': data.get('PermanentEmployeesMale'),
    'PermanentEmployeesFemale': data.get('PermanentEmployeesFemale'),
    'TemporaryEmployees': data.get('TemporaryEmployees'),
    'FullTimeEmployeesMale': data.get('FullTimeEmployeesMale'),
    'FullTimeEmployeesFemale': data.get('FullTimeEmployeesFemale'),
    'PartTimeEmployeesMale': data.get('PartTimeEmployeesMale'),
    'PartTimeEmployeesFemale': data.get('PartTimeEmployeesFemale'),
    'EmployeeTurnoverRate': data.get('EmployeeTurnoverRate'),
    'TrainingAndDevelopmentSpendPerEmployee': data.get('TrainingAndDevelopmentSpendPerEmployee'),
    'LostTimeInjuryFrequencyRate': data.get('LostTimeInjuryFrequencyRate'),
    'EmployeeEngagementScore': data.get('EmployeeEngagementScore'),
    'GenderPayGap': data.get('GenderPayGap'),

    'TotalTrainingSpend': data.get('TotalTrainingSpend'),
    'TotalTrainingSpendBasicPayroll': data.get('TotalTrainingSpendBasicPayroll'),
    'TrainingSpendPerEmployee': data.get('TrainingSpendPerEmployee'),
    'TrainingBeneficiaries': data.get('TrainingBeneficiaries'),
    'AverageTrainingHours': data.get('AverageTrainingHours'),
    'TrainingSpendBlackEmployees': data.get('TrainingSpendBlackEmployees'),
    'TrainingSpendBlackFemaleEmployees': data.get('TrainingSpendBlackFemaleEmployees'),
    'TrainingSpendBlackFemaleEmployeesWithDisabilities': data.get('TrainingSpendBlackFemaleEmployeesWithDisabilities'),
    'TrainingSpendFemaleEmployees': data.get('TrainingSpendFemaleEmployees'),
    'TrainingSpendFemaleEmployeesWithDisabilities': data.get('TrainingSpendFemaleEmployeesWithDisabilities'),
    'TotalInternalBursaries': data.get('TotalInternalBursaries'),
    'ActualPaymentOnBursaries': data.get('ActualPaymentOnBursaries'),
    'LearnershipOfferedToUnemployedAndDisabled': data.get('LearnershipOfferedToUnemployedAndDisabled'),
    'LearnershipsAndInternships': data.get('LearnershipsAndInternships'),
    'LearnershipStudentsAdsorbedIntoEmployment': data.get('LearnershipStudentsAdsorbedIntoEmployment'),
    'NumberEmployeesAttendedManagementLeadership': data.get('NumberEmployeesAttendedManagementLeadership'),

    'TotalGraduateProgramIntake': data.get('TotalGraduateProgramIntake'),
    'GraduateProgramIntakeFemale': data.get('GraduateProgramIntakeFemale'),
    'TotalGraduateProgramAbsorption': data.get('TotalGraduateProgramAbsorption'),
    'GraduateProgramAbsorptionRate': data.get('GraduateProgramAbsorptionRate'),

    'SouthAfricanEmployeesMale': data.get('SouthAfricanEmployeesMale'),
    'SouthAfricanEmployeesFemale': data.get('SouthAfricanEmployeesFemale'),
    'InternationalEmployeesMale': data.get('InternationalEmployeesMale'),
    'InternationalEmployeesFemale': data.get('InternationalEmployeesFemale'),

    'BlackFemaleEmployees': data.get('BlackFemaleEmployees'),
    'ColouredEmployees': data.get('ColouredEmployees'),
    'IndianEmployees': data.get('IndianEmployees'),
    'AsianEmployees': data.get('AsianEmployees'),
    'WhiteEmployees': data.get('WhiteEmployees'),
    'MaleEmployees': data.get('MaleEmployees'),
    'FemaleEmployees': data.get('FemaleEmployees'),
    'DisabilityRepresentationNumberOfEmployees': data.get('DisabilityRepresentationNumberOfEmployees'),

    'LessThan20YearsMale': data.get('LessThan20YearsMale'),
    'LessThan20YearsFemale': data.get('LessThan20YearsFemale'),
    'Between20And29YearsMale': data.get('Between20And29YearsMale'),
    'Between20And29YearsFemale': data.get('Between20And29YearsFemale'),
    'Between30And39YearsMale': data.get('Between30And39YearsMale'),
    'Between30And39YearsFemale': data.get('Between30And39YearsFemale'),
    'Between40And49YearsMale': data.get('Between40And49YearsMale'),
    'Between40And49YearsFemale': data.get('Between40And49YearsFemale'),
    'Between50And59YearsMale': data.get('Between50And59YearsMale'),
    'Between50And59YearsFemale': data.get('Between50And59YearsFemale'),
    'Between60And69YearsMale': data.get('Between60And69YearsMale'),
    'Between60And69YearsFemale': data.get('Between60And69YearsFemale'),
    'Over69YearsMale': data.get('Over69YearsMale'),
    'Over69YearsFemale': data.get('Over69YearsFemale'),

    'TenureLessThan1Year': data.get('TenureLessThan1Year'),
    'Tenure1To3Years': data.get('Tenure1To3Years'),
    'Tenure4To6Years': data.get('Tenure4To6Years'),
    'Tenure7To9Years': data.get('Tenure7To9Years'),
    'Tenure10To20Years': data.get('Tenure10To20Years'),
    'Tenure21To30Years': data.get('Tenure21To30Years'),
    'Tenure31To40Years': data.get('Tenure31To40Years'),
    'TenureMoreThan40Years': data.get('TenureMoreThan40Years'),

    # Top Management
    'TopManagementTotalNumber': data.get('TopManagementTotalNumber'),
    'TopManagementMaleEmployees': data.get('TopManagementMaleEmployees'),
    'TopManagementFemaleEmployees': data.get('TopManagementFemaleEmployees'),
    'TopManagementBlackMaleEmployees': data.get('TopManagementBlackMaleEmployees'),
    'TopManagementBlackFemaleEmployees': data.get('TopManagementBlackFemaleEmployees'),
    'TopManagementAfricanEmployees': data.get('TopManagementAfricanEmployees'),
    'TopManagementColouredEmployees': data.get('TopManagementColouredEmployees'),
    'TopManagementIndianEmployees': data.get('TopManagementIndianEmployees'),
    'TopManagementAsianEmployees': data.get('TopManagementAsianEmployees'),
    'TopManagementWhiteEmployees': data.get('TopManagementWhiteEmployees'),
    'TopManagementDisabledEmployees': data.get('TopManagementDisabledEmployees'),

    # Senior Management
    'SeniorManagementTotalNumber': data.get('SeniorManagementTotalNumber'),
    'SeniorManagementMaleEmployees': data.get('SeniorManagementMaleEmployees'),
    'SeniorManagementFemaleEmployees': data.get('SeniorManagementFemaleEmployees'),
    'SeniorManagementBlackMaleEmployees': data.get('SeniorManagementBlackMaleEmployees'),
    'SeniorManagementBlackFemaleEmployees': data.get('SeniorManagementBlackFemaleEmployees'),
    'SeniorManagementACIEmployees': data.get('SeniorManagementACIEmployees'),
    'SeniorManagementColouredEmployees': data.get('SeniorManagementColouredEmployees'),
    'SeniorManagementIndianEmployees': data.get('SeniorManagementIndianEmployees'),
    'SeniorManagementAsianEmployees': data.get('SeniorManagementAsianEmployees'),
    'SeniorManagementWhiteEmployees': data.get('SeniorManagementWhiteEmployees'),
    'SeniorManagementDisabledEmployees': data.get('SeniorManagementDisabledEmployees'),

    # Middle Management
    'MiddleManagementTotalNumber': data.get('MiddleManagementTotalNumber'),
    'MiddleManagementMaleEmployees': data.get('MiddleManagementMaleEmployees'),
    'MiddleManagementFemaleEmployees': data.get('MiddleManagementFemaleEmployees'),
    'MiddleManagementBlackEmployees': data.get('MiddleManagementBlackEmployees'),
    'MiddleManagementACIEmployees': data.get('MiddleManagementACIEmployees'),
    'MiddleManagementColouredEmployees': data.get('MiddleManagementColouredEmployees'),
    'MiddleManagementIndianEmployees': data.get('MiddleManagementIndianEmployees'),
    'MiddleManagementAsianEmployees': data.get('MiddleManagementAsianEmployees'),
    'MiddleManagementWhiteEmployees': data.get('MiddleManagementWhiteEmployees'),
    'MiddleManagementDisabledEmployees': data.get('MiddleManagementDisabledEmployees'),

    # Junior Management
    'JuniorManagementTotalNumber': data.get('JuniorManagementTotalNumber'), 
    'JuniorManagementMaleEmployees': data.get('JuniorManagementMaleEmployees'), 
    'JuniorManagementFemaleEmployees': data.get('JuniorManagementFemaleEmployees'), 
    'JuniorManagementBlackMaleEmployees': data.get('JuniorManagementBlackMaleEmployees'), 
    'JuniorManagementBlackFemaleEmployees': data.get('JuniorManagementBlackFemaleEmployees'), 
    'JuniorManagementColouredEmployees': data.get('JuniorManagementColouredEmployees'),
    'JuniorManagementIndianEmployees': data.get('JuniorManagementIndianEmployees'),
    'JuniorManagementAsianEmployees': data.get('JuniorManagementAsianEmployees'),
    'JuniorManagementWhiteEmployees': data.get('JuniorManagementWhiteEmployees'),
    'JuniorManagementDisabledEmployees': data.get('JuniorManagementDisabledEmployees'),

    # Semi-Skilled
    'SemiSkilledTotalNumber': data.get('SemiSkilledTotalNumber'), 
    'SemiSkilledFemaleEmployees': data.get('SemiSkilledFemaleEmployees'), 
    'SemiSkilledBlackMaleEmployees': data.get('SemiSkilledBlackMaleEmployees'), 
    'SemiSkilledBlackFemaleEmployees': data.get('SemiSkilledBlackFemaleEmployees'), 
    'SemiSkilledACIEmployees': data.get('SemiSkilledACIEmployees'), 
    'SemiSkilledColouredEmployees': data.get('SemiSkilledColouredEmployees'), 
    'SemiSkilledIndianEmployees': data.get('SemiSkilledIndianEmployees'), 
    'SemiSkilledAsianEmployees': data.get('SemiSkilledAsianEmployees'),
    'SemiSkilledWhiteEmployees': data.get('SemiSkilledWhiteEmployees'),
    'SemiSkilledDisabledEmployees': data.get('SemiSkilledDisabledEmployees'),

    # Unskilled
    'UnskilledTotalNumber': data.get('UnskilledTotalNumber'),
    'UnskilledFemaleEmployees': data.get('UnskilledFemaleEmployees'),
    'UnskilledBlackMaleEmployees': data.get('UnskilledBlackMaleEmployees'),
    'UnskilledBlackFemaleEmployees': data.get('UnskilledBlackFemaleEmployees'),
    'UnskilledACIEmployees': data.get('UnskilledACIEmployees'),
    'UnskilledColouredEmployees': data.get('UnskilledColouredEmployees'),
    'UnskilledIndianEmployees': data.get('UnskilledIndianEmployees'),
    'UnskilledAsianEmployees': data.get('UnskilledAsianEmployees'),
    'UnskilledWhiteEmployees': data.get('UnskilledWhiteEmployees'),
    'UnskilledDisabledEmployees': data.get('UnskilledDisabledEmployees'),

    # Per Disability Type
    'SensoryDisability': data.get('SensoryDisability'),
    'PhysicalDisability': data.get('PhysicalDisability'),
    'MentalDisability': data.get('MentalDisability'),
    'MultipleDisabilities': data.get('MultipleDisabilities'),

    # Financial Inclusion
    'MortgageLoansGranted': data.get('MortgageLoansGranted'),
    'MortgageLoansValueTotal': data.get('MortgageLoansValueTotal'),
    'MortgageLoansAffordableHousingTotal': data.get('MortgageLoansAffordableHousingTotal'),
    'MortgageLoansAffordableHousingValueTotal': data.get('MortgageLoansAffordableHousingValueTotal'),

    # Physical Footprint
    'Outlets': data.get('Outlets'),
    'ATMs': data.get('ATMs'),
    'POSDevices': data.get('POSDevices'),
    'TotalClients': data.get('TotalClients'),
    'DigitallyActiveClients': data.get('DigitallyActiveClients'),

    # Digital Footprint
    # 'DigitallyActiveClients': data.get('DigitallyActiveClients'),  # Already included above

    # Suppliers
    'TotalNumberSuppliers': data.get('TotalNumberSuppliers'),
    'TotalProcurementSpend': data.get('TotalProcurementSpend'),
    'TotalProcurementSpendExemptMicroenterprises': data.get('TotalProcurementSpendExemptMicroenterprises'),
    'TotalProcurementSpendQualifyingSmallEnterprises': data.get('TotalProcurementSpendQualifyingSmallEnterprises'),
    'TotalProcurementSpend51PercentBlackOwned': data.get('TotalProcurementSpend51PercentBlackOwned'),
    'TotalProcurementSpend30PercentBlackOwned': data.get('TotalProcurementSpend30PercentBlackOwned'),
    'LocalProcurementSpend': data.get('LocalProcurementSpend'),

    # Regulators
    'TotalEnvironmentalIncidents': data.get('TotalEnvironmentalIncidents'),
    'TotalEnvironmentalFines': data.get('TotalEnvironmentalFines')
    }

    # Apply nullify_empty_string to all values
    social_metrics_data = {k: nullify_empty_string(v) for k, v in social_metrics_data.items()}

    existing_metric = SocialMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        # Update existing metrics
        for key, value in social_metrics_data.items():
            setattr(existing_metric, key, value)
    else:
        # Create new metrics record
        new_metric = SocialMetrics(**social_metrics_data, SubmissionID=submission_id)
        db.session.add(new_metric)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Social metrics added/updated successfully"
        }), 201  # Created or Updated
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

    # Extract and process environmental metrics data
    environmental_metrics_data = {
    'TotalEnergyUse': data.get('TotalEnergyUse'),
    'TotalRenewableEnergy': data.get('TotalRenewableEnergy'),
    'TotalNonRenewableEnergy': data.get('TotalNonRenewableEnergy'),
    'NonRenewableEnergySources': data.get('NonRenewableEnergySources'),

    'CarbonEmissions': data.get('CarbonEmissions'),
    'CarEmissions': data.get('CarEmissions'),
    'RefrigerantGasEmissions': data.get('RefrigerantGasEmissions'),
    'DieselGeneratorsEmissions': data.get('DieselGeneratorsEmissions'),
    'ElectricityEmissions': data.get('ElectricityEmissions'),
    'ATMEmissions': data.get('ATMEmissions'),
    'TotalIndirectEmissions': data.get('TotalIndirectEmissions'),
    'FlightEmissions': data.get('FlightEmissions'),
    'CashInTransitEmissions': data.get('CashInTransitEmissions'),
    'CarRentalsEmissions': data.get('CarRentalsEmissions'),
    'CloudComputingEmissions': data.get('CloudComputingEmissions'),
    'CourierEmissions': data.get('CourierEmissions'),
    'PaperUsageEmissions': data.get('PaperUsageEmissions'),
    'WasteDisposalEmissions': data.get('WasteDisposalEmissions'),
    'EmployeeCommutingEmissions': data.get('EmployeeCommutingEmissions'),
    'ElectricityTransmissionLossesEmissions': data.get('ElectricityTransmissionLossesEmissions'),
    'CarbonEmissionsPerMeterSquared': data.get('CarbonEmissionsPerMeterSquared'),

    'TotalWaste': data.get('TotalWaste'),
    'RecycledWaste': data.get('RecycledWaste'),
    'WasteToLandfill': data.get('WasteToLandfill')
}

    # Apply nullify_empty_string to all values
    environmental_metrics_data = {k: nullify_empty_string(v) for k, v in environmental_metrics_data.items()}

    existing_metric = EnvironmentalMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        for key, value in environmental_metrics_data.items():
            setattr(existing_metric, key, value)
    else:
        new_metric = EnvironmentalMetrics(**environmental_metrics_data, SubmissionID=submission_id)
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

    governance_metrics_data = {
    'NumberOfBoardMembers': data.get('NumberOfBoardMembers'),
    'IndependentNonExecutiveDirectors': data.get('IndependentNonExecutiveDirectors'),
    'ExecutiveDirectors': data.get('ExecutiveDirectors'),
    'NonExecutiveDirectors': data.get('NonExecutiveDirectors'),
    'IndependentBoardChairman': data.get('IndependentBoardChairman'),
    'BlackACIExecutiveBoardMembers': data.get('BlackACIExecutiveBoardMembers'),
    'BlackACIWomenExecutiveBoardMembers': data.get('BlackACIWomenExecutiveBoardMembers'),
    'BlackACIIndependentNonExecutiveBoardMembers': data.get('BlackACIIndependentNonExecutiveBoardMembers'),

    'TotalNumberOfBoardMeetings': data.get('TotalNumberOfBoardMeetings'),
    'BoardTrainingHours': data.get('BoardTrainingHours'),

    'WhiteMales': data.get('WhiteMales'),
    'WhiteFemales': data.get('WhiteFemales'),
    'ACIFemales': data.get('ACIFemales'),
    'ACIMales': data.get('ACIMales'),
    'NonSABoardMembers': data.get('NonSABoardMembers'),

    'BoardMembersLessThan1Year': data.get('BoardMembersLessThan1Year'),
    'BoardMembers1To3Years': data.get('BoardMembers1To3Years'),
    'BoardMembers4To6Years': data.get('BoardMembers4To6Years'),
    'BoardMembers7To9Years': data.get('BoardMembers7To9Years'),
    'BoardMembersMoreThan9Years': data.get('BoardMembersMoreThan9Years'),
    'BoardMembers40To49YearsAge': data.get('BoardMembers40To49YearsAge'),
    'BoardMembers50To59YearsAge': data.get('BoardMembers50To59YearsAge'),
    'BoardMembers60To69YearsAge': data.get('BoardMembers60To69YearsAge'),
    'BoardMembers70Plus': data.get('BoardMembers70Plus'),

    'TotalNumberOfExcoMembers': data.get('TotalNumberOfExcoMembers'),
    'ExecutiveDirectorsExco': data.get('ExecutiveDirectorsExco'),
    'PrescribedOfficers': data.get('PrescribedOfficers'),
    'ExOfficioMembers': data.get('ExOfficioMembers'),
    'WomenExcoMembers': data.get('WomenExcoMembers'),
    'ACIExcoMembers': data.get('ACIExcoMembers'),

    'ExcoMembers0To3Years': data.get('ExcoMembers0To3Years'),
    'ExcoMembers4To6Years': data.get('ExcoMembers4To6Years'),
    'ExcoMembers7To9Years': data.get('ExcoMembers7To9Years'),

    'ExcoMembers0To10Years': data.get('ExcoMembers0To10Years'),
    'ExcoMembers11To20Years': data.get('ExcoMembers11To20Years'),
    'ExcoMembersMoreThan20Years': data.get('ExcoMembersMoreThan20Years'),

    'ControllingShareholder': data.get('ControllingShareholder'),
    'MultipleShareholderRights': data.get('MultipleShareholderRights'),

    'BeneficialSharesDirectOwnershipCEO': data.get('BeneficialSharesDirectOwnershipCEO'),
    'BeneficialSharesIndirectOwnershipCEO': data.get('BeneficialSharesIndirectOwnershipCEO'),
    'TotalSharesOwnedCEO': data.get('TotalSharesOwnedCEO'),

    'BeneficialSharesDirectOwnershipCFO': data.get('BeneficialSharesDirectOwnershipCFO'),
    'BeneficialSharesIndirectOwnershipCFO': data.get('BeneficialSharesIndirectOwnershipCFO'),
    'TotalSharesOwnedCFO': data.get('TotalSharesOwnedCFO'),

    'BeneficialSharesDirectOwnershipCOO': data.get('BeneficialSharesDirectOwnershipCOO'),
    'BeneficialSharesIndirectOwnershipCOO': data.get('BeneficialSharesIndirectOwnershipCOO'),
    'TotalSharesOwnedCOO': data.get('TotalSharesOwnedCOO'),

    'Auditors': data.get('Auditors'),
    'AuditorTenure': data.get('AuditorTenure'),
    'AuditFees': data.get('AuditFees'),

    'ExecutiveRemunerationLinkedToESG': data.get('ExecutiveRemunerationLinkedToESG'),

    'CEOGuaranteedPackage': data.get('CEOGuaranteedPackage'),
    'CEOShortTermIncentive': data.get('CEOShortTermIncentive'),
    'CEOLongTermIncentive': data.get('CEOLongTermIncentive'),
    'CEOTotalRemuneration': data.get('CEOTotalRemuneration'),
    'CEOSharePriceAsMultipleOfGuaranteedPackage': data.get('CEOSharePriceAsMultipleOfGuaranteedPackage'),

    'CFOGuaranteedPackage': data.get('CFOGuaranteedPackage'),
    'CFOShortTermIncentive': data.get('CFOShortTermIncentive'),
    'CFOLongTermIncentive': data.get('CFOLongTermIncentive'),
    'CFOTotalRemuneration': data.get('CFOTotalRemuneration'),

    'COOGuaranteedPackage': data.get('COOGuaranteedPackage'),
    'COOShortTermIncentive': data.get('COOShortTermIncentive'),
    'COOLongTermIncentive': data.get('COOLongTermIncentive'),
    'COOTotalRemuneration': data.get('COOTotalRemuneration'),

    'EmployeesCompletedEthicsTraining': data.get('EmployeesCompletedEthicsTraining'),
    'ContractorsCompletedEthicsTraining': data.get('ContractorsCompletedEthicsTraining'),
    'SubsidiariesCompletedEthicsTraining': data.get('SubsidiariesCompletedEthicsTraining'),
    'ReportedCases': data.get('ReportedCases'),
    'CasesStillUnderInvestigation': data.get('CasesStillUnderInvestigation'),
    'SubstantiatedCases': data.get('SubstantiatedCases'),
    'UnsubstantiatedCases': data.get('UnsubstantiatedCases'),
    'DisciplinaryCasesReported': data.get('DisciplinaryCasesReported'),
    'DisciplinaryCasesConcluded': data.get('DisciplinaryCasesConcluded'),
    'EthicalDisciplinaryCasesConcluded': data.get('EthicalDisciplinaryCasesConcluded'),
    'OngoingDisciplinaryCases': data.get('OngoingDisciplinaryCases'),

    'SystemAvailability': data.get('SystemAvailability'),
    'PrivacyRelatedIncidents': data.get('PrivacyRelatedIncidents'),
    'PrivacyRelatedIncidentsReportedToRegulator': data.get('PrivacyRelatedIncidentsReportedToRegulator')
}

    # Apply nullify_empty_string to all values
    governance_metrics_data = {k: nullify_empty_string(v) for k, v in governance_metrics_data.items()}

    existing_metric = GovernanceMetrics.query.filter_by(SubmissionID=submission_id).first()

    if existing_metric:
        for key, value in governance_metrics_data.items():
            setattr(existing_metric, key, value)
    else:
        new_metric = GovernanceMetrics(**governance_metrics_data, SubmissionID=submission_id)
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



# @app.route("/input_peoplemetrics/<submission_id>", methods=["POST"])
# @jwt_required()
# def input_peoplemetrics(submission_id):
   
#     # verify that subimissionid is valid 
#     print(submission_id)
#     data = request.get_json()
#     diversity_inclusion = nullify_empty_string(data.get("DiversityAndInclusion"))
#     pay_equality = nullify_empty_string(data.get("PayEquality"))
#     wage_level = nullify_empty_string(data.get("WageLevel"))
#     health_safety_level = nullify_empty_string(data.get("HealthAndSafetyLevel"))
    
#     existing_metric = Peoplemetrics.query.filter_by(SubmissionID=submission_id).first()
    
#     if existing_metric:
#         existing_metric.DiversityAndInclusion = diversity_inclusion
#         existing_metric.PayEquality = pay_equality
#         existing_metric.WageLevel = wage_level
#         existing_metric.HealthAndSafetyLevel = health_safety_level
#     else:
#         new_metric = Peoplemetrics(
#             DiversityAndInclusion=diversity_inclusion,
#             PayEquality=pay_equality,
#             WageLevel=wage_level,
#             HealthAndSafetyLevel=health_safety_level,
#             SubmissionID=submission_id
#         )
#         db.session.add(new_metric)
    
#     try:
#         db.session.commit()
#         return jsonify({
#             "success": True, 
#             "message": "Metrics added successfully"
#         }), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500
    
# @app.route("/input_planetmetrics/<submission_id>", methods=["POST"])
# @jwt_required()
# def input_planetmetrics(submission_id):
#     data = request.get_json()
#     print(data)

#     greenhouse_gas_emission = nullify_empty_string(data.get("GreenhouseGasEmission"))
#     water_consumption = nullify_empty_string(data.get("WaterConsumption"))
#     land_use = nullify_empty_string(data.get("LandUse"))

#     existing_metric = Planetmetrics.query.filter_by(SubmissionID=submission_id).first()

#     if existing_metric:
#         existing_metric.GreenhouseGasEmission = greenhouse_gas_emission
#         existing_metric.WaterConsumption = water_consumption
#         existing_metric.LandUse = land_use
#     else:
#         new_metric = Planetmetrics(
#             GreenhouseGasEmission=greenhouse_gas_emission,
#             WaterConsumption=water_consumption,
#             LandUse=land_use,
#             SubmissionID=submission_id
#         )
#         db.session.add(new_metric)

#     try:
#         db.session.commit()
#         return jsonify({
#             "success": True, 
#             "message": "Planet metrics added successfully"
#         }), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500
    
# @app.route("/input_prosperitymetrics/<submission_id>", methods=["POST"])
# @jwt_required()
# def input_prosperitymetrics(submission_id):
  
#     data = request.get_json()
#     print(data)
#     total_tax_paid = nullify_empty_string(data.get("TotalTaxPaid"))
#     abs_number_of_new_emps = nullify_empty_string(data.get("AbsNumberOfNewEmps"))
#     abs_number_of_new_emp_turnover = nullify_empty_string(data.get("AbsNumberOfNewEmpTurnover"))
#     economic_contribution = nullify_empty_string(data.get("EconomicContribution"))
#     total_rnd_expenses = nullify_empty_string(data.get("TotalRNDExpenses"))
#     total_capital_expenditures = nullify_empty_string(data.get("TotalCapitalExpenditures"))
#     share_buybacks_and_dividend_payments = nullify_empty_string(data.get("ShareBuyBacksAndDividendPayments"))

#     # Check if an entry with the submission_id already exists
#     existing_metric = Prosperitymetrics.query.filter_by(SubmissionID=submission_id).first()

#     if existing_metric:
#         # Update the existing entry
#         existing_metric.TotalTaxPaid = total_tax_paid
#         existing_metric.AbsNumberOfNewEmps = abs_number_of_new_emps
#         existing_metric.AbsNumberOfNewEmpTurnover = abs_number_of_new_emp_turnover
#         existing_metric.EconomicContribution = economic_contribution
#         existing_metric.TotalRNDExpenses = total_rnd_expenses
#         existing_metric.TotalCapitalExpenditures = total_capital_expenditures
#         existing_metric.ShareBuyBacksAndDividendPayments = share_buybacks_and_dividend_payments
#     else:
#         # Create a new entry
#         new_metric = Prosperitymetrics(
#             TotalTaxPaid=total_tax_paid,
#             AbsNumberOfNewEmps=abs_number_of_new_emps,
#             AbsNumberOfNewEmpTurnover=abs_number_of_new_emp_turnover,
#             EconomicContribution=economic_contribution,
#             TotalRNDExpenses=total_rnd_expenses,
#             TotalCapitalExpenditures=total_capital_expenditures,
#             ShareBuyBacksAndDividendPayments=share_buybacks_and_dividend_payments,
#             SubmissionID=submission_id
#         )
#         db.session.add(new_metric)
        
#     try:
#         db.session.commit()
#         return jsonify({
#             "success": True, 
#             "message": "Prosperity metrics added successfully"
#         }), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500

# @app.route("/input_governancemetrics/<submission_id>", methods=["POST"])
# @jwt_required()
# def input_governancemetrics(submission_id):

#     data = request.get_json()
#     print(data)
#     anti_corruption_training = nullify_empty_string(data.get("AntiCorruptionTraining"))
#     confirmed_corruption_incident_prev = nullify_empty_string(data.get("ConfirmedCorruptionIncidentPrev"))
#     confirmed_corruption_incident_current = nullify_empty_string(data.get("ConfirmedCorruptionIncidentCurrent"))

#     existing_metric = Governancemetrics.query.filter_by(SubmissionID=submission_id).first()

#     if existing_metric:
#         existing_metric.AntiCorruptionTraining = anti_corruption_training
#         existing_metric.ConfirmedCorruptionIncidentPrev = confirmed_corruption_incident_prev
#         existing_metric.ConfirmedCorruptionIncidentCurrent = confirmed_corruption_incident_current
#     else:
#         new_metric = Governancemetrics(
#             AntiCorruptionTraining=anti_corruption_training,
#             ConfirmedCorruptionIncidentPrev=confirmed_corruption_incident_prev,
#             ConfirmedCorruptionIncidentCurrent=confirmed_corruption_incident_current,
#             SubmissionID=submission_id
#         )
#         db.session.add(new_metric)


#     try:
#         db.session.commit()
#         return jsonify({
#             "success": True, 
#             "message": "Governance metrics added successfully"
#         }), 201
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500

@app.route("/trans/<submission_id>", methods=["POST"])
@jwt_required()
def trans(submission_id):
    print("in server")

    submission = Submission.query.get(submission_id)
    
    # # List of models to fetch data from
    # models = [Peoplemetrics, Planetmetrics, Prosperitymetrics, Governancemetrics]

    # List of models to fetch data from
    models = [SocialMetrics, EnvironmentalMetrics, GovernanceMetrics]  # Updated models


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

    submission.Status = 1  # Pending (or another suitable value)
    db.session.commit()
    
    # Send data to BaaS platform 
    baas_response = send_data_to_baas(data, submission_id, user_id) 
    if not baas_response["success"]:
        return jsonify({
            "success": False,
            "message": "Failed to send data to BaaS platform"
            }), 500
    
    # Create webhook to receive BaaS notification (Implementation details will depend on your setup)
    create_transaction_complete_webhook(submission_id)

    # return jsonify({
    # "success": True,
    # "message": "Data sent to BaaS platform. Waiting for blockchain confirmation."
    # }), 200
    
    # Fetch metrics and create a combined dictionary
    nftData = {}
    grouped_metrics = {}
    for model in models:
        model_name = model.__name__
        metric = model.query.filter_by(SubmissionID=submission_id).first()
        if metric:
            # Get the column names and values for the metric using introspection
            columns = {column.name: getattr(metric, column.name) for column in inspect(model).columns}
            nftData.update(columns)
            grouped_metrics[model_name] = columns

    # Remove the SubmissionID key as it's common and not needed in the output
    nftData.pop('SubmissionID', None)

    private_key = ecochainPK
    my_address = ecochainAddress
    current_user = db.session.get(User, user_id)
    rec_address = current_user.AlgorandAddress
    rec_privateKey = current_user.AlgorandPrivateKey
    transamount = 0

    txid, confirmedTxn = first_transaction_example(private_key, my_address, rec_address, transamount,  nftData)

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
        submission.Status = 2
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


def create_transaction_complete_webhook(submission_id):
    
    """
    For development with ngrok, we don't need to explicitly create a webhook. 
    Just log the submission_id for tracking purposes.
    """

    print(f"Webhook created for submission ID: {submission_id}") 
    # You might want to store this association in a database or in-memory data structure if needed



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
        # ... (update submission status, mint NFT, send email, etc.)

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

        # return jsonify({
        #     "success": True,
        #     "id": current_user.UserID,
        #     "transaction_id": transaction.TransactionID,
        #     "nft_id": transaction.NFTAssetID
        # }), 200

def generate_dummy_data():
    with app.app_context():
        users = User.query.all()

        # Add dummy submissions
        submissions = []
        for user in users:
            for _ in range(3):
                submission = Submission(
                    FirstName=fake.first_name(),
                    LastName=fake.last_name(),
                    Date=fake.date_this_decade(),
                    Year=fake.year(),  # Generate a year
                    StartPeriod=fake.date_this_decade(),
                    EndPeriod=fake.date_this_decade(),
                    Score=random.uniform(0, 100),  # Generate a random score between 0 and 100
                    Status=random.choice([0, 1, 2]),  # Randomly choose a status
                    UserID=user.UserID
                )
                db.session.add(submission)
                submissions.append(submission)

        db.session.commit()

        # Add dummy metrics
        for sub in submissions:
            db.session.add(Peoplemetrics(
                DiversityAndInclusion=fake.random_number(digits=2),
                PayEquality=fake.random_number(digits=2),
                WageLevel=fake.random_number(digits=2),
                HealthAndSafetyLevel=fake.random_number(digits=2),
                SubmissionID=sub.SubmissionID
            ))

            db.session.add(Planetmetrics(
                GreenhouseGasEmission=fake.random_number(digits=2),
                WaterConsumption=fake.random_number(digits=2),
                LandUse=fake.random_number(digits=2),
                SubmissionID=sub.SubmissionID
            ))
            
            db.session.add(Prosperitymetrics(
                TotalTaxPaid=fake.random_number(digits=2),
                AbsNumberOfNewEmps=fake.random_number(digits=2),
                AbsNumberOfNewEmpTurnover=fake.random_number(digits=2),
                EconomicContribution=fake.random_number(digits=2),
                TotalRNDExpenses=fake.random_number(digits=2),
                TotalCapitalExpenditures=fake.random_number(digits=2),
                ShareBuyBacksAndDividendPayments=fake.random_number(digits=2),
                SubmissionID=sub.SubmissionID
            ))
            
            db.session.add(Governancemetrics(
                AntiCorruptionTraining=fake.random_number(digits=2),
                ConfirmedCorruptionIncidentPrev=fake.random_number(digits=2),
                ConfirmedCorruptionIncidentCurrent=fake.random_number(digits=2),
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
        
