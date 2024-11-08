from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    user = 'user'
    admin = 'admin'
    auditor = 'auditor'

class User(db.Model, UserMixin):
    UserID = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(100), nullable=False, unique=True)
    Password = db.Column(db.String(80), nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    AlgorandPrivateKey = db.Column(db.String(100))
    AlgorandAddress = db.Column(db.String(100))
    Location = db.Column(db.String(100))
    Industry = db.Column(db.String(100))
    Size = db.Column(db.String(100))
    Description = db.Column(db.String())
    Role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.user)  # Use the Enum type
    

    def get_id(self):
        return str(self.UserID)

class Submission(db.Model):
    SubmissionID = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(100))
    LastName = db.Column(db.String(100))
    Date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    StartPeriod = db.Column(db.Date, nullable=True,default=datetime.utcnow )
    EndPeriod = db.Column(db.Date, nullable=True,default=datetime.utcnow)
    Year = db.Column(db.Integer)
    Score = db.Column(db.Double)
    Status = db.Column(db.Integer) # 0: in progress, 1: Pending, 2: Approved, 3: Complete, 4: Rejected
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID'))
    BaaS_Tx_ID = db.Column(db.String(100), nullable=True)  # Store BaaS transaction ID
    BaaS_Tx_URL = db.Column(db.String(255), nullable=True)  # Store BaaS transaction URL

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class SocialMetrics(db.Model):
    SocialMetricsID = db.Column(db.Integer, primary_key=True)
    SubmissionID = db.Column(db.Integer, db.ForeignKey('submission.SubmissionID'), nullable=False)

    # Customer Satisfaction
    CustomerComplaints = db.Column(db.Integer, nullable=True)
    CustomerSatisfactionScore = db.Column(db.Float, nullable=True)

    # Human Capital Development
    PermanentEmployeesMale = db.Column(db.Integer, nullable=True)
    PermanentEmployeesFemale = db.Column(db.Integer, nullable=True)
    TemporaryEmployees = db.Column(db.Integer, nullable=True)
    FullTimeEmployeesMale = db.Column(db.Integer, nullable=True)
    FullTimeEmployeesFemale = db.Column(db.Integer, nullable=True)
    PartTimeEmployeesMale = db.Column(db.Integer, nullable=True)
    PartTimeEmployeesFemale = db.Column(db.Integer, nullable=True)
    EmployeeTurnoverRate = db.Column(db.Float, nullable=True)  
    TrainingAndDevelopmentSpendPerEmployee = db.Column(db.Float, nullable=True) 
    LostTimeInjuryFrequencyRate = db.Column(db.Float, nullable=True) 
    EmployeeEngagementScore = db.Column(db.Float, nullable=True) 
    GenderPayGap = db.Column(db.String(100), nullable=True)  

    # Training, Bursaries & Learnerships
    TotalTrainingSpend = db.Column(db.Float, nullable=True)
    TotalTrainingSpendBasicPayroll = db.Column(db.Float, nullable=True)
    TrainingSpendPerEmployee = db.Column(db.Float, nullable=True)
    TrainingBeneficiaries = db.Column(db.Integer, nullable=True)
    AverageTrainingHours = db.Column(db.Float, nullable=True)
    TrainingSpendBlackEmployees = db.Column(db.Float, nullable=True)
    TrainingSpendBlackFemaleEmployees = db.Column(db.Float, nullable=True)
    TrainingSpendBlackFemaleEmployeesWithDisabilities = db.Column(db.Float, nullable=True)
    TrainingSpendFemaleEmployees = db.Column(db.Float, nullable=True)
    TrainingSpendFemaleEmployeesWithDisabilities = db.Column(db.Float, nullable=True)
    TotalInternalBursaries = db.Column(db.Integer, nullable=True)
    ActualPaymentOnBursaries = db.Column(db.Float, nullable=True)
    LearnershipOfferedToUnemployedAndDisabled = db.Column(db.Integer, nullable=True)
    LearnershipsAndInternships = db.Column(db.Integer, nullable=True)
    LearnershipStudentsAdsorbedIntoEmployment = db.Column(db.Integer, nullable=True)
    NumberEmployeesAttendedManagementLeadership = db.Column(db.Integer, nullable=True)

    # Graduate Program
    TotalGraduateProgramIntake = db.Column(db.Integer, nullable=True)
    GraduateProgramIntakeFemale = db.Column(db.Integer, nullable=True)
    TotalGraduateProgramAbsorption = db.Column(db.Integer, nullable=True)
    GraduateProgramAbsorptionRate = db.Column(db.Float, nullable=True) 

    # Employee Profile & Movements
    TotalNumberOfEmployeesBeginningYear = db.Column(db.Integer, nullable=True)
    TotalNumberOfEmployeesEndOfYear = db.Column(db.Integer, nullable=True)
    NewHiresPermanentEmployees = db.Column(db.Integer, nullable=True) 
    NewHiresPermanentEmployeesWith3MonthsProbation = db.Column(db.Integer, nullable=True) 
    TemporaryEmployees = db.Column(db.Integer, nullable=True) 
    TerminationsPermanentEmployees = db.Column(db.Integer, nullable=True) 
    Resignations = db.Column(db.Integer, nullable=True)
    VoluntaryRetrenchments = db.Column(db.Integer, nullable=True)
    InvoluntaryRetrenchments = db.Column(db.Integer, nullable=True) 
    Dismissals = db.Column(db.Integer, nullable=True)
    NonTemporaryEmployees = db.Column(db.Integer, nullable=True) 
    TotalEmployeeInternalTransfers = db.Column(db.Integer, nullable=True)
    VacanciesFilledByInternalCandidates = db.Column(db.Integer, nullable=True)
    InternalPromotionalSuccessRate = db.Column(db.Float, nullable=True)
    TotalEmployeePromotions = db.Column(db.Integer, nullable=True)
    NewHiresWomen = db.Column(db.Integer, nullable=True)

    # Per Region
    SouthAfricanEmployeesMale = db.Column(db.Integer, nullable=True)
    SouthAfricanEmployeesFemale = db.Column(db.Integer, nullable=True)
    InternationalEmployeesMale = db.Column(db.Integer, nullable=True)
    InternationalEmployeesFemale = db.Column(db.Integer, nullable=True)

    # Employee Equity Demographics
    BlackFemaleEmployees = db.Column(db.Integer, nullable=True)
    ColouredEmployees = db.Column(db.Integer, nullable=True)
    IndianEmployees = db.Column(db.Integer, nullable=True)
    AsianEmployees = db.Column(db.Integer, nullable=True)
    WhiteEmployees = db.Column(db.Integer, nullable=True)
    MaleEmployees = db.Column(db.Integer, nullable=True)
    FemaleEmployees = db.Column(db.Integer, nullable=True)
    DisabilityRepresentationNumberOfEmployees = db.Column(db.Integer, nullable=True)

    # Employee Age
    LessThan20YearsMale = db.Column(db.Integer, nullable=True)
    LessThan20YearsFemale = db.Column(db.Integer, nullable=True)
    Between20And29YearsMale = db.Column(db.Integer, nullable=True)
    Between20And29YearsFemale = db.Column(db.Integer, nullable=True)
    Between30And39YearsMale = db.Column(db.Integer, nullable=True)
    Between30And39YearsFemale = db.Column(db.Integer, nullable=True)
    Between40And49YearsMale = db.Column(db.Integer, nullable=True)
    Between40And49YearsFemale = db.Column(db.Integer, nullable=True)
    Between50And59YearsMale = db.Column(db.Integer, nullable=True)
    Between50And59YearsFemale = db.Column(db.Integer, nullable=True)
    Between60And69YearsMale = db.Column(db.Integer, nullable=True)
    Between60And69YearsFemale = db.Column(db.Integer, nullable=True)
    Over69YearsMale = db.Column(db.Integer, nullable=True)
    Over69YearsFemale = db.Column(db.Integer, nullable=True)

    # Employee Tenure
    TenureLessThan1Year = db.Column(db.Integer, nullable=True)
    Tenure1To3Years = db.Column(db.Integer, nullable=True)
    Tenure4To6Years = db.Column(db.Integer, nullable=True)
    Tenure7To9Years = db.Column(db.Integer, nullable=True)
    Tenure10To20Years = db.Column(db.Integer, nullable=True)
    Tenure21To30Years = db.Column(db.Integer, nullable=True)
    Tenure31To40Years = db.Column(db.Integer, nullable=True)
    TenureMoreThan40Years = db.Column(db.Integer, nullable=True)

    # Top Management
    TopManagementTotalNumber = db.Column(db.Integer, nullable=True)
    TopManagementMaleEmployees = db.Column(db.Integer, nullable=True)
    TopManagementFemaleEmployees = db.Column(db.Integer, nullable=True)
    TopManagementBlackMaleEmployees = db.Column(db.Integer, nullable=True)
    TopManagementBlackFemaleEmployees = db.Column(db.Integer, nullable=True)
    TopManagementAfricanEmployees = db.Column(db.Integer, nullable=True)
    TopManagementColouredEmployees = db.Column(db.Integer, nullable=True)
    TopManagementIndianEmployees = db.Column(db.Integer, nullable=True)
    TopManagementAsianEmployees = db.Column(db.Integer, nullable=True)
    TopManagementWhiteEmployees = db.Column(db.Integer, nullable=True)
    TopManagementDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Senior Management
    SeniorManagementTotalNumber = db.Column(db.Integer, nullable=True) 
    SeniorManagementMaleEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementFemaleEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementBlackMaleEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementBlackFemaleEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementACIEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementColouredEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementIndianEmployees = db.Column(db.Integer, nullable=True) 
    SeniorManagementAsianEmployees = db.Column(db.Integer, nullable=True)
    SeniorManagementWhiteEmployees = db.Column(db.Integer, nullable=True)
    SeniorManagementDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Middle Management
    MiddleManagementTotalNumber = db.Column(db.Integer, nullable=True) 
    MiddleManagementMaleEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementFemaleEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementBlackEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementACIEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementColouredEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementIndianEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementAsianEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementWhiteEmployees = db.Column(db.Integer, nullable=True)
    MiddleManagementDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Junior Management
    JuniorManagementTotalNumber = db.Column(db.Integer, nullable=True) 
    JuniorManagementMaleEmployees = db.Column(db.Integer, nullable=True) 
    JuniorManagementFemaleEmployees = db.Column(db.Integer, nullable=True) 
    JuniorManagementBlackMaleEmployees = db.Column(db.Integer, nullable=True) 
    JuniorManagementBlackFemaleEmployees = db.Column(db.Integer, nullable=True) 
    JuniorManagementACIEmployees = db.Column(db.Integer, nullable=True) 
    JuniorManagementColouredEmployees = db.Column(db.Integer, nullable=True)
    JuniorManagementIndianEmployees = db.Column(db.Integer, nullable=True)
    JuniorManagementAsianEmployees = db.Column(db.Integer, nullable=True)
    JuniorManagementWhiteEmployees = db.Column(db.Integer, nullable=True)
    JuniorManagementDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Semi-Skilled
    SemiSkilledTotalNumber = db.Column(db.Integer, nullable=True) 
    SemiSkilledFemaleEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledBlackMaleEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledBlackFemaleEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledACIEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledColouredEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledIndianEmployees = db.Column(db.Integer, nullable=True) 
    SemiSkilledAsianEmployees = db.Column(db.Integer, nullable=True)
    SemiSkilledWhiteEmployees = db.Column(db.Integer, nullable=True)
    SemiSkilledDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Unskilled
    UnskilledTotalNumber = db.Column(db.Integer, nullable=True)
    UnskilledFemaleEmployees = db.Column(db.Integer, nullable=True)
    UnskilledBlackMaleEmployees = db.Column(db.Integer, nullable=True)
    UnskilledBlackFemaleEmployees = db.Column(db.Integer, nullable=True)
    UnskilledACIEmployees = db.Column(db.Integer, nullable=True)
    UnskilledColouredEmployees = db.Column(db.Integer, nullable=True)
    UnskilledIndianEmployees = db.Column(db.Integer, nullable=True)
    UnskilledAsianEmployees = db.Column(db.Integer, nullable=True)
    UnskilledWhiteEmployees = db.Column(db.Integer, nullable=True)
    UnskilledDisabledEmployees = db.Column(db.Integer, nullable=True)

    # Additional Labor Statistics
    EmployeeCostsAndBenefits = db.Column(db.Float, nullable=True)
    TotalBasicPayrollRands = db.Column(db.Float, nullable=True)
    AnnualSalaryUnionizedEmployees = db.Column(db.Float, nullable=True)
    UnionizedEmployees = db.Column(db.Integer, nullable=True)
    RetrenchedIndividuals = db.Column(db.Integer, nullable=True)
    AverageAnnualLeaveDaysTaken = db.Column(db.Float, nullable=True) 
    AverageSickLeaveDaysTaken = db.Column(db.Float, nullable=True)

    # Incident Reporting
    EmployeeGrievances = db.Column(db.Integer, nullable=True)
    IncidentsOfMisconduct = db.Column(db.Integer, nullable=True)
    MedicalIncidents = db.Column(db.Integer, nullable=True)
    WorkmensCompensationClaims = db.Column(db.Integer, nullable=True)
    NumberInjured = db.Column(db.Integer, nullable=True)
    NumberofFatalitiesBankMembers = db.Column(db.Integer, nullable=True)
    NumberofFatalitiesNonBankMembers = db.Column(db.Integer, nullable=True)

    # Financial Inclusion
    MortgageLoansGranted = db.Column(db.Integer, nullable=True)
    MortgageLoansValueTotal = db.Column(db.Float, nullable=True)
    MortgageLoansAffordableHousingTotal = db.Column(db.Integer, nullable=True)
    MortgageLoansAffordableHousingValueTotal = db.Column(db.Float, nullable=True)

    # Physical Footprint
    Outlets = db.Column(db.Integer, nullable=True)
    ATMs = db.Column(db.Integer, nullable=True)
    POSDevices = db.Column(db.Integer, nullable=True)
    TotalClients = db.Column(db.Integer, nullable=True)
    DigitallyActiveClients = db.Column(db.Integer, nullable=True)

    # Suppliers
    TotalNumberSuppliers = db.Column(db.Integer, nullable=True)
    TotalProcurementSpend = db.Column(db.Float, nullable=True) 
    TotalProcurementSpendExemptMicroenterprises = db.Column(db.Float, nullable=True)
    TotalProcurementSpendQualifyingSmallEnterprises = db.Column(db.Float, nullable=True)
    TotalProcurementSpend51PercentBlackOwned = db.Column(db.Float, nullable=True)
    TotalProcurementSpend30PercentBlackOwned = db.Column(db.Float, nullable=True)
    LocalProcurementSpend = db.Column(db.Float, nullable=True)  

    # Regulators
    TotalEnvironmentalIncidents = db.Column(db.Integer, nullable=True) 
    TotalEnvironmentalFines = db.Column(db.Integer, nullable=True)



class EnvironmentalMetrics(db.Model):
    EnvironmentalMetricsID = db.Column(db.Integer, primary_key=True)
    SubmissionID = db.Column(db.Integer, db.ForeignKey('submission.SubmissionID'), nullable=False)

    # Energy Use
    TotalEnergyUse = db.Column(db.Float, nullable=True)
    TotalRenewableEnergy = db.Column(db.Float, nullable=True) 
    TotalNonRenewableEnergy = db.Column(db.Float, nullable=True) 
    NonRenewableEnergySources = db.Column(db.String, nullable=True)  

    # Greenhouse gas emissions
    CarbonEmissions = db.Column(db.Float, nullable=True)
    CarEmissions = db.Column(db.Float, nullable=True)
    RefrigerantGasEmissions = db.Column(db.Float, nullable=True) 
    DieselGeneratorsEmissions = db.Column(db.Float, nullable=True)
    ElectricityEmissions = db.Column(db.Float, nullable=True) 
    ATMEmissions = db.Column(db.Float, nullable=True)
    TotalIndirectEmissions = db.Column(db.Float, nullable=True) 
    FlightEmissions = db.Column(db.Float, nullable=True) 
    CashInTransitEmissions = db.Column(db.Float, nullable=True) 
    CarRentalsEmissions = db.Column(db.Float, nullable=True) 
    CloudComputingEmissions = db.Column(db.Float, nullable=True) 
    CourierEmissions = db.Column(db.Float, nullable=True) 
    PaperUsageEmissions = db.Column(db.Float, nullable=True) 
    WasteDisposalEmissions = db.Column(db.Float, nullable=True) 
    EmployeeCommutingEmissions = db.Column(db.Float, nullable=True) 
    ElectricityTransmissionLossesEmissions = db.Column(db.Float, nullable=True) 
    CarbonEmissionsPerMeterSquared = db.Column(db.Float, nullable=True)

    # Waste Management
    TotalWaste = db.Column(db.Float, nullable=True) 
    RecycledWaste = db.Column(db.Float, nullable=True)  
    WasteToLandfill = db.Column(db.Float, nullable=True)


class GovernanceMetrics(db.Model):
    GovernanceMetricsID = db.Column(db.Integer, primary_key=True)
    SubmissionID = db.Column(db.Integer, db.ForeignKey('submission.SubmissionID'), nullable=False)

    # Board composition & diversity
    NumberOfBoardMembers = db.Column(db.Integer, nullable=True) 
    IndependentNonExecutiveDirectors = db.Column(db.Integer, nullable=True) 
    ExecutiveDirectors = db.Column(db.Integer, nullable=True)
    NonExecutiveDirectors = db.Column(db.Integer, nullable=True)
    IndependentBoardChairman = db.Column(db.String(50), nullable=True)  
    BlackACIExecutiveBoardMembers = db.Column(db.Integer, nullable=True) 
    BlackACIWomenExecutiveBoardMembers = db.Column(db.Integer, nullable=True)
    BlackACIIndependentNonExecutiveBoardMembers = db.Column(db.Integer, nullable=True)

    # Board Effectiveness 
    TotalNumberOfBoardMeetings = db.Column(db.Integer, nullable=True) 
    BoardTrainingHours = db.Column(db.Float, nullable=True)

    # Workforce Diversity
    WhiteMales = db.Column(db.Integer, nullable=True) 
    WhiteFemales = db.Column(db.Integer, nullable=True) 
    ACIFemales = db.Column(db.Integer, nullable=True)  
    ACIMales = db.Column(db.Integer, nullable=True)  
    NonSABoardMembers = db.Column(db.Integer, nullable=True) 

    # Board Member Tenure and Age
    BoardMembersLessThan1Year = db.Column(db.Integer, nullable=True) 
    BoardMembers1To3Years = db.Column(db.Integer, nullable=True) 
    BoardMembers4To6Years = db.Column(db.Integer, nullable=True) 
    BoardMembers7To9Years = db.Column(db.Integer, nullable=True) 
    BoardMembersMoreThan9Years = db.Column(db.Integer, nullable=True) 
    BoardMembers40To49YearsAge = db.Column(db.Integer, nullable=True) 
    BoardMembers50To59YearsAge = db.Column(db.Integer, nullable=True) 
    BoardMembers60To69YearsAge = db.Column(db.Integer, nullable=True) 
    BoardMembers70Plus = db.Column(db.Integer, nullable=True) 

    # Executive Management 
    TotalNumberOfExcoMembers = db.Column(db.Integer, nullable=True)
    ExecutiveDirectorsExco = db.Column(db.Integer, nullable=True)
    PrescribedOfficers = db.Column(db.Integer, nullable=True)
    ExOfficioMembers = db.Column(db.Integer, nullable=True)
    WomenExcoMembers = db.Column(db.Integer, nullable=True)
    ACIExcoMembers = db.Column(db.Integer, nullable=True)

    # Executive Management Tenure
    ExcoMembers0To3Years = db.Column(db.Integer, nullable=True)
    ExcoMembers4To6Years = db.Column(db.Integer, nullable=True)
    ExcoMembers7To9Years = db.Column(db.Integer, nullable=True)

    # Executive Management Bank Tenure 
    ExcoMembers0To10Years = db.Column(db.Integer, nullable=True)
    ExcoMembers11To20Years = db.Column(db.Integer, nullable=True)
    ExcoMembersMoreThan20Years = db.Column(db.Integer, nullable=True)

    # Shareholder Rights
    ControllingShareholder = db.Column(db.String(50), nullable=True) 
    MultipleShareholderRights = db.Column(db.String(50), nullable=True)  

    # CEO Shareholding
    BeneficialSharesDirectOwnershipCEO = db.Column(db.Integer, nullable=True)
    BeneficialSharesIndirectOwnershipCEO = db.Column(db.Integer, nullable=True)
    TotalSharesOwnedCEO = db.Column(db.Integer, nullable=True)

    # CFO Shareholding
    BeneficialSharesDirectOwnershipCFO = db.Column(db.Integer, nullable=True)
    BeneficialSharesIndirectOwnershipCFO = db.Column(db.Integer, nullable=True)
    TotalSharesOwnedCFO = db.Column(db.Integer, nullable=True)

    # COO Shareholding
    BeneficialSharesDirectOwnershipCOO = db.Column(db.Integer, nullable=True)
    BeneficialSharesIndirectOwnershipCOO = db.Column(db.Integer, nullable=True)
    TotalSharesOwnedCOO = db.Column(db.Integer, nullable=True)

    # Audit
    Auditors = db.Column(db.String(100), nullable=True) 
    AuditorTenure = db.Column(db.Integer, nullable=True)  
    AuditFees = db.Column(db.Float, nullable=True)  

    # Executive Remuneration 
    ExecutiveRemunerationLinkedToESG = db.Column(db.Boolean, nullable=True) 

    # CEO Remuneration
    CEOGuaranteedPackage = db.Column(db.Float, nullable=True)  
    CEOShortTermIncentive = db.Column(db.Float, nullable=True)  
    CEOLongTermIncentive = db.Column(db.Float, nullable=True)  
    CEOTotalRemuneration = db.Column(db.Float, nullable=True)  
    CEOSharePriceAsMultipleOfGuaranteedPackage = db.Column(db.Float, nullable=True) 

    # CFO Remuneration
    CFOGuaranteedPackage = db.Column(db.Float, nullable=True)  
    CFOShortTermIncentive = db.Column(db.Float, nullable=True)  
    CFOLongTermIncentive = db.Column(db.Float, nullable=True)  
    CFOTotalRemuneration = db.Column(db.Float, nullable=True)

    # COO Remuneration
    COOGuaranteedPackage = db.Column(db.Float, nullable=True) 
    COOShortTermIncentive = db.Column(db.Float, nullable=True)
    COOLongTermIncentive = db.Column(db.Float, nullable=True)
    COOTotalRemuneration = db.Column(db.Float, nullable=True) 

    # Ethics and integrity (additional metrics)
    EmployeesCompletedEthicsTraining = db.Column(db.Integer, nullable=True) 
    ContractorsCompletedEthicsTraining = db.Column(db.Integer, nullable=True)
    SubsidiariesCompletedEthicsTraining = db.Column(db.Integer, nullable=True)
    ReportedCases = db.Column(db.Integer, nullable=True)
    CasesStillUnderInvestigation = db.Column(db.Integer, nullable=True)
    SubstantiatedCases = db.Column(db.Integer, nullable=True) 
    UnsubstantiatedCases = db.Column(db.Integer, nullable=True)
    DisciplinaryCasesReported = db.Column(db.Integer, nullable=True)
    DisciplinaryCasesConcluded = db.Column(db.Integer, nullable=True)
    EthicalDisciplinaryCasesConcluded = db.Column(db.Integer, nullable=True)
    OngoingDisciplinaryCases = db.Column(db.Integer, nullable=True)

    # Additional Metrics (from the image, category unclear)
    SystemAvailability = db.Column(db.Float, nullable=True) 
    PrivacyRelatedIncidents = db.Column(db.Integer, nullable=True)
    PrivacyRelatedIncidentsReportedToRegulator = db.Column(db.Integer, nullable=True)


class Transaction(db.Model):
    TransactionID = db.Column(db.String(100), primary_key=True)
    NFTTransactionMintID = db.Column(db.String(100))
    NFTTransactionTransferID = db.Column(db.String(100))
    NFTAssetID = db.Column(db.String(100))
    SubmissionID = db.Column(db.Integer, db.ForeignKey('submission.SubmissionID'))

class Report(db.Model):
    ReportID = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(50))
    LastName = db.Column(db.String(50))
    ReportPeriod = db.Column(db.String(100))
    CreatedDate = db.Column(db.DateTime)
    CreatedByID = db.Column(db.Integer, db.ForeignKey('user.UserID'))

    # Update foreign keys to reference the new metrics models
    SocialMetricsID = db.Column(db.Integer, db.ForeignKey('social_metrics.SocialMetricsID'))
    EnvironmentalMetricsID = db.Column(db.Integer, db.ForeignKey('environmental_metrics.EnvironmentalMetricsID'))
    GovernanceMetricsID = db.Column(db.Integer, db.ForeignKey('governance_metrics.GovernanceMetricsID'))

    Status = db.Column(db.String(100))