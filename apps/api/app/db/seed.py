from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.enums import ActionPlanStatus, AuditStatus, CoverageStatus, RiskRating, RoleCode
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    ActionPlan,
    ActionPlanRevision,
    Audit,
    AuditEscalation,
    AuditPlan,
    BusinessInitiative,
    City,
    Company,
    ControlPerformanceIndicator,
    Country,
    Designation,
    ERMRisk,
    Impact,
    KnowledgeLibraryItem,
    Location,
    ObservationGrading,
    OverallAssessment,
    Process,
    ProcessLocationMapping,
    ProcessRiskMapping,
    Recommendation,
    ReportConsideration,
    RiskType,
    RootCause,
    State,
    TaskSwapRule,
    TrialBalance,
)
from app.schemas.user import UserCreate
from app.services.activity_log import activity_log_service
from app.services.user import user_service


def _get_or_create(db, model, defaults: dict | None = None, **filters):
    entity = db.scalar(select(model).filter_by(**filters))
    if entity:
        return entity
    payload = {**filters, **(defaults or {})}
    entity = model(**payload)
    db.add(entity)
    db.flush()
    return entity


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user_service.ensure_roles_seeded(db)
        if db.scalar(select(Audit.id).limit(1)):
            db.commit()
            return

        india = _get_or_create(db, Country, defaults={"name": "India", "description": "India", "created_by": "seed", "updated_by": "seed"}, code="IN")
        uk = _get_or_create(db, Country, defaults={"name": "United Kingdom", "description": "UK", "created_by": "seed", "updated_by": "seed"}, code="UK")
        karnataka = _get_or_create(db, State, defaults={"name": "Karnataka", "country_id": india.id, "created_by": "seed", "updated_by": "seed"}, code="KA")
        maharashtra = _get_or_create(db, State, defaults={"name": "Maharashtra", "country_id": india.id, "created_by": "seed", "updated_by": "seed"}, code="MH")
        london_state = _get_or_create(db, State, defaults={"name": "London", "country_id": uk.id, "created_by": "seed", "updated_by": "seed"}, code="LDN")
        bengaluru = _get_or_create(db, City, defaults={"name": "Bengaluru", "state_id": karnataka.id, "created_by": "seed", "updated_by": "seed"}, code="BLR")
        mumbai = _get_or_create(db, City, defaults={"name": "Mumbai", "state_id": maharashtra.id, "created_by": "seed", "updated_by": "seed"}, code="MUM")
        london = _get_or_create(db, City, defaults={"name": "London", "state_id": london_state.id, "created_by": "seed", "updated_by": "seed"}, code="LON")

        nhl = _get_or_create(
            db,
            Company,
            defaults={
                "country_id": india.id,
                "state_id": karnataka.id,
                "city_id": bengaluru.id,
                "pan": "AAACN1234Q",
                "gst_no": "29AAACN1234Q1Z2",
                "created_by": "seed",
                "updated_by": "seed",
            },
            name="NHL Limited",
        )
        abc = _get_or_create(
            db,
            Company,
            defaults={
                "country_id": india.id,
                "state_id": maharashtra.id,
                "city_id": mumbai.id,
                "pan": "AAACA0000A",
                "gst_no": "27AAACA0000A1Z3",
                "created_by": "seed",
                "updated_by": "seed",
            },
            name="ABC Ltd",
        )

        designations = {
            "HEAD_AUDIT": _get_or_create(db, Designation, defaults={"title": "Head of Internal Audit", "created_by": "seed", "updated_by": "seed"}, code="HEAD_AUDIT"),
            "AUDITOR": _get_or_create(db, Designation, defaults={"title": "Lead Auditor", "created_by": "seed", "updated_by": "seed"}, code="AUDITOR"),
            "FIN_MANAGER": _get_or_create(db, Designation, defaults={"title": "Finance Manager", "created_by": "seed", "updated_by": "seed"}, code="FIN_MANAGER"),
        }

        loc_blr = _get_or_create(
            db,
            Location,
            defaults={
                "sector": "Healthcare",
                "country_id": india.id,
                "state_id": karnataka.id,
                "city_id": bengaluru.id,
                "company_id": nhl.id,
                "risk_index": RiskRating.HIGH.value,
                "description": "Bengaluru Shared Services",
                "created_by": "seed",
                "updated_by": "seed",
            },
            location_code="002",
        )
        loc_mum = _get_or_create(
            db,
            Location,
            defaults={
                "sector": "Manufacturing",
                "country_id": india.id,
                "state_id": maharashtra.id,
                "city_id": mumbai.id,
                "company_id": abc.id,
                "risk_index": RiskRating.MEDIUM.value,
                "description": "Mumbai Plant",
                "created_by": "seed",
                "updated_by": "seed",
            },
            location_code="1102",
        )
        loc_lon = _get_or_create(
            db,
            Location,
            defaults={
                "sector": "Banking & Finance",
                "country_id": uk.id,
                "state_id": london_state.id,
                "city_id": london.id,
                "company_id": abc.id,
                "risk_index": RiskRating.LOW.value,
                "description": "London Treasury Hub",
                "created_by": "seed",
                "updated_by": "seed",
            },
            location_code="01",
        )

        processes = {
            "BILLING": _get_or_create(
                db,
                Process,
                defaults={"sector": "Healthcare", "business_cycle": "Order to Cash", "name": "Billing and Revenue", "created_by": "seed", "updated_by": "seed"},
                code="BILLING",
            ),
            "PAYROLL": _get_or_create(
                db,
                Process,
                defaults={"sector": "Shared Services", "business_cycle": "Hire to Retire", "name": "HR Payroll", "created_by": "seed", "updated_by": "seed"},
                code="PAYROLL",
            ),
            "INVENTORY": _get_or_create(
                db,
                Process,
                defaults={"sector": "Manufacturing", "business_cycle": "Procure to Pay", "name": "Inventory Management", "created_by": "seed", "updated_by": "seed"},
                code="INVENTORY",
            ),
        }

        tb_billing = _get_or_create(db, TrialBalance, defaults={"name": "Revenue Accounts", "company_id": nhl.id, "amount": 15000000, "created_by": "seed", "updated_by": "seed"}, code="TB-REV")
        tb_inventory = _get_or_create(db, TrialBalance, defaults={"name": "Inventory", "company_id": abc.id, "amount": 8200000, "created_by": "seed", "updated_by": "seed"}, code="TB-INV")

        plm_billing = _get_or_create(
            db,
            ProcessLocationMapping,
            defaults={
                "audit_name": "Key Account Review_2026",
                "process_id": processes["BILLING"].id,
                "location_id": loc_blr.id,
                "company_id": nhl.id,
                "trial_balance_id": tb_billing.id,
                "created_by": "seed",
                "updated_by": "seed",
            },
            code="PLM-BILL",
        )
        plm_inventory = _get_or_create(
            db,
            ProcessLocationMapping,
            defaults={
                "audit_name": "Inventory Management",
                "process_id": processes["INVENTORY"].id,
                "location_id": loc_mum.id,
                "company_id": abc.id,
                "trial_balance_id": tb_inventory.id,
                "created_by": "seed",
                "updated_by": "seed",
            },
            code="PLM-INV",
        )

        risk_types = {
            "OPER": _get_or_create(db, RiskType, defaults={"name": "Operational", "created_by": "seed", "updated_by": "seed"}, code="OPER"),
            "FIN": _get_or_create(db, RiskType, defaults={"name": "Financial", "created_by": "seed", "updated_by": "seed"}, code="FIN"),
            "COMP": _get_or_create(db, RiskType, defaults={"name": "Compliance", "created_by": "seed", "updated_by": "seed"}, code="COMP"),
        }
        root_causes = {
            "DESIGN": _get_or_create(db, RootCause, defaults={"name": "Control Design Gap", "created_by": "seed", "updated_by": "seed"}, code="DESIGN"),
            "MONITOR": _get_or_create(db, RootCause, defaults={"name": "Insufficient Monitoring", "created_by": "seed", "updated_by": "seed"}, code="MONITOR"),
        }
        _get_or_create(db, Impact, defaults={"name": "Financial Exposure", "created_by": "seed", "updated_by": "seed"}, code="FIN")
        _get_or_create(db, Recommendation, defaults={"name": "Automate Control", "created_by": "seed", "updated_by": "seed"}, code="AUTO")
        _get_or_create(db, ReportConsideration, defaults={"name": "Statutory Reporting", "created_by": "seed", "updated_by": "seed"}, code="STAT")
        gradings = {
            "CRIT": _get_or_create(db, ObservationGrading, defaults={"name": "Critical", "severity_rank": 1, "created_by": "seed", "updated_by": "seed"}, code="CRIT"),
            "HIGH": _get_or_create(db, ObservationGrading, defaults={"name": "High", "severity_rank": 2, "created_by": "seed", "updated_by": "seed"}, code="HIGH"),
            "MED": _get_or_create(db, ObservationGrading, defaults={"name": "Medium", "severity_rank": 3, "created_by": "seed", "updated_by": "seed"}, code="MED"),
            "LOW": _get_or_create(db, ObservationGrading, defaults={"name": "Low", "severity_rank": 4, "created_by": "seed", "updated_by": "seed"}, code="LOW"),
        }
        _get_or_create(db, AuditEscalation, defaults={"name": "Management Escalation", "escalation_days": 30, "created_by": "seed", "updated_by": "seed"}, code="ESC-30")
        _get_or_create(db, ControlPerformanceIndicator, defaults={"name": "Timely Closure Rate", "threshold": ">= 90%", "created_by": "seed", "updated_by": "seed"}, code="CPI-01")
        _get_or_create(db, TaskSwapRule, defaults={"source_designation_id": designations["AUDITOR"].id, "target_designation_id": designations["HEAD_AUDIT"].id, "max_tasks": 3, "created_by": "seed", "updated_by": "seed"}, code="SWAP-01")

        users = {
            "superadmin": user_service.create_user(
                db,
                UserCreate(
                    username="superadmin",
                    email="superadmin@example.com",
                    full_name="Super Admin",
                    password="Password@123",
                    phone="9999999991",
                    designation_id=designations["HEAD_AUDIT"].id,
                    company_id=nhl.id,
                    location_id=loc_blr.id,
                    role_codes=[RoleCode.SUPER_ADMIN.value],
                ),
                "seed",
            ),
            "auditor": user_service.create_user(
                db,
                UserCreate(
                    username="auditoruser1",
                    email="auditor@example.com",
                    full_name="Auditor User 1",
                    password="Password@123",
                    phone="9999999992",
                    designation_id=designations["AUDITOR"].id,
                    company_id=nhl.id,
                    location_id=loc_blr.id,
                    role_codes=[RoleCode.AUDITOR.value],
                ),
                "seed",
            ),
            "head_auditor": user_service.create_user(
                db,
                UserCreate(
                    username="headauditor1",
                    email="headauditor@example.com",
                    full_name="Head Auditor 1",
                    password="Password@123",
                    phone="9999999994",
                    designation_id=designations["HEAD_AUDIT"].id,
                    company_id=nhl.id,
                    location_id=loc_blr.id,
                    role_codes=[RoleCode.HEAD_AUDITOR.value],
                ),
                "seed",
            ),
            "management": user_service.create_user(
                db,
                UserCreate(
                    username="management1",
                    email="management@example.com",
                    full_name="Management Reviewer 1",
                    password="Password@123",
                    phone="9999999995",
                    designation_id=designations["FIN_MANAGER"].id,
                    company_id=nhl.id,
                    location_id=loc_blr.id,
                    role_codes=[RoleCode.MANAGEMENT.value],
                ),
                "seed",
            ),
            "auditee": user_service.create_user(
                db,
                UserCreate(
                    username="auditeeuser1",
                    email="auditee@example.com",
                    full_name="Auditee User 1",
                    password="Password@123",
                    phone="9999999993",
                    designation_id=designations["FIN_MANAGER"].id,
                    company_id=abc.id,
                    location_id=loc_mum.id,
                    role_codes=[RoleCode.AUDITEE.value],
                ),
                "seed",
            ),
        }
        db.flush()

        plan1 = AuditPlan(
            audit_name="Key Account Review_2026",
            company_id=nhl.id,
            location_id=loc_blr.id,
            quarter="Q1",
            period_type="Quarterly",
            period_value="Q1",
            fiscal_year="2026-2027",
            start_date=date.today() - timedelta(days=15),
            end_date=date.today() + timedelta(days=20),
            planned_flag=True,
            criticality=RiskRating.HIGH.value,
            audit_owner_id=users["auditor"].id,
            remarks="Priority revenue assurance coverage",
            created_by="seed",
            updated_by="seed",
        )
        plan2 = AuditPlan(
            audit_name="Inventory Management",
            company_id=abc.id,
            location_id=loc_mum.id,
            quarter="Q2",
            period_type="Quarterly",
            period_value="Q2",
            fiscal_year="2026-2027",
            start_date=date.today() + timedelta(days=15),
            end_date=date.today() + timedelta(days=45),
            planned_flag=True,
            criticality=RiskRating.MEDIUM.value,
            audit_owner_id=users["auditor"].id,
            remarks="Plant control maturity review",
            created_by="seed",
            updated_by="seed",
        )
        plan3 = AuditPlan(
            audit_name="Treasury Controls Deep Dive",
            company_id=abc.id,
            location_id=loc_lon.id,
            quarter="Q3",
            period_type="Quarterly",
            period_value="Q3",
            fiscal_year="2026-2027",
            start_date=date.today() - timedelta(days=100),
            end_date=date.today() - timedelta(days=45),
            planned_flag=False,
            criticality=RiskRating.CRITICAL.value,
            audit_owner_id=users["auditor"].id,
            remarks="Unplanned thematic review",
            created_by="seed",
            updated_by="seed",
        )
        db.add_all([plan1, plan2, plan3])
        db.flush()

        audits = [
            Audit(
                audit_plan_id=plan1.id,
                audit_name=plan1.audit_name,
                company_id=plan1.company_id,
                location_id=plan1.location_id,
                quarter=plan1.quarter,
                period_type=plan1.period_type,
                period_value=plan1.period_value,
                fiscal_year=plan1.fiscal_year,
                start_date=plan1.start_date,
                end_date=plan1.end_date,
                status=AuditStatus.IN_PROGRESS.value,
                planned_flag=plan1.planned_flag,
                criticality=plan1.criticality,
                audit_owner_id=users["auditor"].id,
                remarks=plan1.remarks,
                history_timeline=[
                    {"status": AuditStatus.TO_BE_INITIATED.value, "date": (date.today() - timedelta(days=20)).isoformat()},
                    {"status": AuditStatus.IN_PROGRESS.value, "date": (date.today() - timedelta(days=10)).isoformat()},
                ],
                created_by="seed",
                updated_by="seed",
            ),
            Audit(
                audit_plan_id=plan2.id,
                audit_name=plan2.audit_name,
                company_id=plan2.company_id,
                location_id=plan2.location_id,
                quarter=plan2.quarter,
                period_type=plan2.period_type,
                period_value=plan2.period_value,
                fiscal_year=plan2.fiscal_year,
                start_date=plan2.start_date,
                end_date=plan2.end_date,
                status=AuditStatus.TO_BE_INITIATED.value,
                planned_flag=plan2.planned_flag,
                criticality=plan2.criticality,
                audit_owner_id=users["auditor"].id,
                remarks=plan2.remarks,
                history_timeline=[{"status": AuditStatus.TO_BE_INITIATED.value, "date": date.today().isoformat()}],
                created_by="seed",
                updated_by="seed",
            ),
            Audit(
                audit_plan_id=plan3.id,
                audit_name=plan3.audit_name,
                company_id=plan3.company_id,
                location_id=plan3.location_id,
                quarter=plan3.quarter,
                period_type=plan3.period_type,
                period_value=plan3.period_value,
                fiscal_year=plan3.fiscal_year,
                start_date=plan3.start_date,
                end_date=plan3.end_date,
                status=AuditStatus.OVERDUE.value,
                planned_flag=plan3.planned_flag,
                criticality=plan3.criticality,
                audit_owner_id=users["auditor"].id,
                remarks=plan3.remarks,
                history_timeline=[
                    {"status": AuditStatus.UNPLANNED.value, "date": (date.today() - timedelta(days=110)).isoformat()},
                    {"status": AuditStatus.OVERDUE.value, "date": (date.today() - timedelta(days=5)).isoformat()},
                ],
                created_by="seed",
                updated_by="seed",
            ),
        ]
        db.add_all(audits)
        db.flush()

        db.add_all(
            [
                ProcessRiskMapping(
                    audit_plan_id=plan1.id,
                    process_location_mapping_id=plm_billing.id,
                    trial_balance_id=tb_billing.id,
                    quantitative_assessment=RiskRating.HIGH.value,
                    qualitative_assessment=RiskRating.HIGH.value,
                    final_process_rating=RiskRating.HIGH.value,
                    created_by="seed",
                    updated_by="seed",
                ),
                ProcessRiskMapping(
                    audit_plan_id=plan2.id,
                    process_location_mapping_id=plm_inventory.id,
                    trial_balance_id=tb_inventory.id,
                    quantitative_assessment=RiskRating.MEDIUM.value,
                    qualitative_assessment=RiskRating.MEDIUM.value,
                    final_process_rating=RiskRating.HIGH.value,
                    created_by="seed",
                    updated_by="seed",
                ),
                ERMRisk(
                    audit_plan_id=plan1.id,
                    erm_risk_code="ERM-001",
                    erm_risk_title="Revenue leakage",
                    description="Manual discounts are not consistently approved.",
                    rating=RiskRating.HIGH.value,
                    process_id=processes["BILLING"].id,
                    created_by="seed",
                    updated_by="seed",
                ),
                ERMRisk(
                    audit_plan_id=plan2.id,
                    erm_risk_code="ERM-008",
                    erm_risk_title="Inventory aging",
                    description="Slow-moving inventory review is not timely.",
                    rating=RiskRating.MEDIUM.value,
                    process_id=processes["INVENTORY"].id,
                    created_by="seed",
                    updated_by="seed",
                ),
                BusinessInitiative(
                    audit_plan_id=plan1.id,
                    initiative_code="KBI-001",
                    title="Revenue process digitization",
                    description="ERP controls redesign for discount approvals.",
                    impact=RiskRating.HIGH.value,
                    owner_user_id=users["auditor"].id,
                    timeline="Apr 2026 - Aug 2026",
                    created_by="seed",
                    updated_by="seed",
                ),
                OverallAssessment(
                    audit_plan_id=plan1.id,
                    location_id=loc_blr.id,
                    overall_risk=RiskRating.HIGH.value,
                    coverage_status=CoverageStatus.COVERED.value,
                    justification="Revenue streams contribute material financial exposure.",
                    last_audited_date=date.today() - timedelta(days=390),
                    created_by="seed",
                    updated_by="seed",
                ),
                OverallAssessment(
                    audit_plan_id=plan3.id,
                    location_id=loc_lon.id,
                    overall_risk=RiskRating.CRITICAL.value,
                    coverage_status=CoverageStatus.NOT_COVERED.value,
                    justification="Assumed design: outside approved annual plan until committee sign-off.",
                    last_audited_date=date.today() - timedelta(days=700),
                    created_by="seed",
                    updated_by="seed",
                ),
            ]
        )
        db.flush()

        action_plans = [
            ActionPlan(
                audit_id=audits[0].id,
                audit_number=audits[0].audit_number,
                location_id=loc_blr.id,
                root_cause_id=root_causes["DESIGN"].id,
                observation_heading="Discount approvals bypassed",
                observation_grading_id=gradings["HIGH"].id,
                detailed_observation="Manual price overrides above threshold were processed without approver evidence.",
                risk_type_id=risk_types["FIN"].id,
                agreed_timeline=date.today() + timedelta(days=12),
                auditor_status=ActionPlanStatus.IN_PROGRESS.value,
                auditee_status=ActionPlanStatus.IN_PROGRESS.value,
                review_quarter="Q1",
                responsibility_department="Commercial Finance",
                auditor_implementation_remarks="Initial remediation plan accepted.",
                management_response="Workflow control is being configured in ERP.",
                agreed_action_plan="Introduce maker-checker and approval matrix.",
                implementation_owner_user_id=users["auditee"].id,
                assigned_auditor_user_id=users["auditor"].id,
                revised_date=date.today(),
                revision_count=1,
                management_implementation_remarks="Configuration in progress.",
                metadata_json={"assumed_design": False},
                created_by="seed",
                updated_by="seed",
            ),
            ActionPlan(
                audit_id=audits[0].id,
                audit_number=audits[0].audit_number,
                location_id=loc_blr.id,
                root_cause_id=root_causes["MONITOR"].id,
                observation_heading="Aging review not evidenced",
                observation_grading_id=gradings["MED"].id,
                detailed_observation="Periodic review of unmatched invoices lacked retained sign-off.",
                risk_type_id=risk_types["OPER"].id,
                agreed_timeline=date.today() - timedelta(days=8),
                auditor_status=ActionPlanStatus.REOPENED.value,
                auditee_status=ActionPlanStatus.REOPENED.value,
                review_quarter="Q1",
                responsibility_department="Order to Cash",
                auditor_implementation_remarks="Previous evidence incomplete; reopened.",
                management_response="Team will upload revised evidence.",
                agreed_action_plan="Standardize review checklist and archive approvals.",
                implementation_owner_user_id=users["auditee"].id,
                assigned_auditor_user_id=users["auditor"].id,
                revised_date=date.today() - timedelta(days=2),
                revision_count=2,
                management_implementation_remarks="Revised evidence compilation underway.",
                metadata_json={"assumed_design": False},
                created_by="seed",
                updated_by="seed",
            ),
            ActionPlan(
                audit_id=audits[2].id,
                audit_number=audits[2].audit_number,
                location_id=loc_lon.id,
                root_cause_id=root_causes["DESIGN"].id,
                observation_heading="Treasury approvals fully automated",
                observation_grading_id=gradings["LOW"].id,
                detailed_observation="Control enhancement delivered and tested.",
                risk_type_id=risk_types["COMP"].id,
                agreed_timeline=date.today() - timedelta(days=20),
                auditor_status=ActionPlanStatus.COMPLETED.value,
                auditee_status=ActionPlanStatus.COMPLETED.value,
                review_quarter="Q3",
                responsibility_department="Treasury",
                auditor_implementation_remarks="Validated during closure walkthrough.",
                management_response="Deployment completed.",
                agreed_action_plan="Maintain quarterly monitoring.",
                implementation_owner_user_id=users["auditee"].id,
                assigned_auditor_user_id=users["auditor"].id,
                revised_date=date.today() - timedelta(days=25),
                revision_count=0,
                management_implementation_remarks="Evidence archived.",
                completed_at=datetime.now(UTC) - timedelta(days=10),
                last_response_at=datetime.now(UTC) - timedelta(days=20),
                last_review_at=datetime.now(UTC) - timedelta(days=10),
                metadata_json={"assumed_design": True, "note": "Completed closure flow assumed from observed form fields."},
                created_by="seed",
                updated_by="seed",
            ),
        ]
        db.add_all(action_plans)
        db.flush()

        db.add_all(
            [
                ActionPlanRevision(
                    action_plan_id=action_plans[0].id,
                    revision_number=1,
                    management_implementation_remarks="ERP workflow config ready for UAT.",
                    revised_date=date.today(),
                    updated_by_user_id=users["auditee"].id,
                    status_snapshot={"auditor_status": ActionPlanStatus.IN_PROGRESS.value, "auditee_status": ActionPlanStatus.IN_PROGRESS.value},
                    created_by="seed",
                    updated_by="seed",
                ),
                ActionPlanRevision(
                    action_plan_id=action_plans[1].id,
                    revision_number=2,
                    management_implementation_remarks="Auditor requested evidence refresh.",
                    revised_date=date.today() - timedelta(days=2),
                    updated_by_user_id=users["auditor"].id,
                    status_snapshot={"auditor_status": ActionPlanStatus.REOPENED.value, "auditee_status": ActionPlanStatus.REOPENED.value},
                    created_by="seed",
                    updated_by="seed",
                ),
            ]
        )

        db.add_all(
            [
                KnowledgeLibraryItem(
                    item_type="process_universe",
                    title="Healthcare Process Universe",
                    description="Process universe for healthcare operations and shared services.",
                    category="Healthcare",
                    tags=["process", "sector", "healthcare"],
                    approved_for_auditee=True,
                    created_by="seed",
                    updated_by="seed",
                ),
                KnowledgeLibraryItem(
                    item_type="racm",
                    title="Order to Cash RACM Template",
                    description="Baseline RACM with preventive and detective control examples.",
                    category="RACM",
                    tags=["racm", "controls"],
                    approved_for_auditee=True,
                    created_by="seed",
                    updated_by="seed",
                ),
                KnowledgeLibraryItem(
                    item_type="benchmark",
                    title="Benchmark Metrics for Revenue Assurance",
                    description="Benchmark cycle times and segregation ratios.",
                    category="Benchmarks",
                    tags=["benchmark", "revenue"],
                    approved_for_auditee=True,
                    created_by="seed",
                    updated_by="seed",
                ),
                KnowledgeLibraryItem(
                    item_type="initial_data_request",
                    title="Initial Data Request Checklist",
                    description="Assumed design: dedicated IDR library entry built to replace the broken route seen in the source tool.",
                    category="Templates",
                    tags=["idr", "template", "assumed design"],
                    approved_for_auditee=True,
                    created_by="seed",
                    updated_by="seed",
                ),
            ]
        )

        activity_log_service.log(
            db,
            actor_user_id=users["superadmin"].id,
            actor_name=users["superadmin"].full_name,
            role=RoleCode.SUPER_ADMIN.value,
            module="seed",
            entity_type="system",
            entity_id="demo",
            action_type="create",
            new_values={"message": "Demo seed completed"},
        )
        activity_log_service.notify(
            db,
            user_id=users["auditor"].id,
            title="Seeded demo ready",
            message="Demo data includes in-progress, reopened, overdue, and completed action plans.",
        )

        db.commit()


if __name__ == "__main__":
    seed()
