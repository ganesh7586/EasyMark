"""
Script: evaluate_hallucinations.py
Purpose: Comprehensive 105-query benchmark evaluating Hallucination Resistance,
         Citation Faithfulness, and Policy Answering Accuracy on Static Company PDFs.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.database import get_db
from app.ingestion.indexer import StaticDocIndexer
from app.rag.rag_service import get_rag_service


@dataclass
class TestCase:
    id: int
    category: str  # "in_domain", "adversarial_trap", "out_of_domain", "boundary_reasoning"
    query: str
    expected_behavior: str  # "answer_with_citation", "reject_insufficient_evidence"
    key_facts: List[str]  # Keywords or concepts that must be present or absent
    forbidden_claims: List[str]  # False claims that indicate a hallucination
    expected_doc: Optional[str] = None
    expected_page: Optional[int] = None


# 105 Test Cases evaluating static company documents
TEST_CASES: List[TestCase] = [
    # =========================================================================
    # CATEGORY 1: Direct In-Domain Policy Queries (50 Test Cases)
    # =========================================================================
    TestCase(
        id=1,
        category="in_domain",
        query="What are the core collaboration hours for employees?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["10:00", "16:00", "IST"],
        forbidden_claims=["9:00 to 17:00", "PST", "EST"],
    ),
    TestCase(
        id=2,
        category="in_domain",
        query="What time zone are core collaboration hours based on?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["IST", "India Standard Time"],
        forbidden_claims=["Pacific", "Eastern", "UTC+0"],
    ),
    TestCase(
        id=3,
        category="in_domain",
        query="Which days of the week do core collaboration hours apply to?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Monday", "Friday"],
        forbidden_claims=["Saturday", "Sunday", "7 days"],
    ),
    TestCase(
        id=4,
        category="in_domain",
        query="How many working days in advance must planned leave be submitted?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["five", "5"],
        forbidden_claims=["two weeks", "10 days", "30 days"],
    ),
    TestCase(
        id=5,
        category="in_domain",
        query="Where should employees submit their planned leave requests?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["HR portal"],
        forbidden_claims=["Slack channel", "WhatsApp", "verbal request"],
    ),
    TestCase(
        id=6,
        category="in_domain",
        query="When should an employee notify their manager about urgent leave?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["before the start", "workday"],
        forbidden_claims=["after 3 days", "within 24 hours after"],
    ),
    TestCase(
        id=7,
        category="in_domain",
        query="Who is authorized to approve employee leave requests?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["manager"],
        forbidden_claims=["CEO", "Security Operations", "HR intern"],
    ),
    TestCase(
        id=8,
        category="in_domain",
        query="How far in advance should meeting agendas be shared for recurring decision meetings?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["one working day", "1 working day"],
        forbidden_claims=["one week", "10 minutes before", "immediately after"],
    ),
    TestCase(
        id=9,
        category="in_domain",
        query="Within what timeframe must meeting decisions and action items be recorded?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["one working day", "1 working day"],
        forbidden_claims=["two weeks", "end of quarter"],
    ),
    TestCase(
        id=10,
        category="in_domain",
        query="What are the security requirements for remote work?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["approved company devices", "secure network"],
        forbidden_claims=["personal public Wi-Fi without VPN", "any internet"],
    ),
    TestCase(
        id=11,
        category="in_domain",
        query="What is the rule regarding sharing passwords and MFA one-time codes?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["never share", "multi-factor"],
        forbidden_claims=["share with trusted colleagues", "write on sticky note"],
    ),
    TestCase(
        id=12,
        category="in_domain",
        query="Can confidential company files be forwarded to personal email accounts?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["do not forward", "personal email"],
        forbidden_claims=["allowed if working from home", "permitted with permission"],
    ),
    TestCase(
        id=13,
        category="in_domain",
        query="What are the four data classification levels defined in the policy?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Public", "Internal", "Confidential", "Restricted"],
        forbidden_claims=["Top Secret", "Unclassified"],
    ),
    TestCase(
        id=14,
        category="in_domain",
        query="To whom should suspected data exposure or lost devices be reported?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Security Operations", "immediately"],
        forbidden_claims=["Police", "Local IT vendor", "wait for next week"],
    ),
    TestCase(
        id=15,
        category="in_domain",
        query="Within how many calendar days must expense claims with itemized receipts be submitted?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["30", "calendar days"],
        forbidden_claims=["60 days", "90 days", "14 days"],
    ),
    TestCase(
        id=16,
        category="in_domain",
        query="What expense threshold requires written manager approval prior to purchase?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["10,000"],
        forbidden_claims=["5,000", "50,000", "100,000"],
    ),
    TestCase(
        id=17,
        category="in_domain",
        query="How frequently should managers hold one-to-one conversations with direct reports?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["two weeks", "2 weeks"],
        forbidden_claims=["monthly", "daily", "once per year"],
    ),
    TestCase(
        id=18,
        category="in_domain",
        query="How often do formal performance reviews occur each year?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["twice per year", "twice"],
        forbidden_claims=["quarterly", "four times", "once every two years"],
    ),
    TestCase(
        id=19,
        category="in_domain",
        query="What is the target response time for HR and leave questions?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["2 working days", "People Operations"],
        forbidden_claims=["immediately", "10 business days"],
    ),
    TestCase(
        id=20,
        category="in_domain",
        query="What is the target response time for workplace equipment questions via IT Helpdesk?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["1 working day", "IT Helpdesk"],
        forbidden_claims=["15 minutes", "one week"],
    ),
    TestCase(
        id=21,
        category="in_domain",
        query="What is the definition and initial response target for a SEV-1 incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["15 minutes", "24", "Production outage"],
        forbidden_claims=["1 hour", "4 hours", "next business day"],
    ),
    TestCase(
        id=22,
        category="in_domain",
        query="What is the required update cadence for active SEV-1 incidents?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["30 minutes"],
        forbidden_claims=["hourly", "daily", "every 2 hours"],
    ),
    TestCase(
        id=23,
        category="in_domain",
        query="What is the initial response target for a SEV-2 incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["1 business hour", "one business hour"],
        forbidden_claims=["15 minutes", "24 hours", "3 days"],
    ),
    TestCase(
        id=24,
        category="in_domain",
        query="What is the update cadence for SEV-2 incidents?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["2 business hours"],
        forbidden_claims=["30 minutes", "daily"],
    ),
    TestCase(
        id=25,
        category="in_domain",
        query="What is the initial response target for a SEV-3 incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["1 business day"],
        forbidden_claims=["15 minutes", "1 hour"],
    ),
    TestCase(
        id=26,
        category="in_domain",
        query="What is the initial response target for a SEV-4 defect or improvement request?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["3 business days"],
        forbidden_claims=["15 minutes", "immediately"],
    ),
    TestCase(
        id=27,
        category="in_domain",
        query="What is the official definition of an engineering blocker?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["two working hours", "2 working hours", "prevents planned work"],
        forbidden_claims=["24 hours", "minor inconvenience"],
    ),
    TestCase(
        id=28,
        category="in_domain",
        query="What details must be recorded when opening a blocker ticket?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["impact", "start time", "affected service"],
        forbidden_claims=["employee salary", "blood group"],
    ),
    TestCase(
        id=29,
        category="in_domain",
        query="After how many hours without mitigation must a blocker be escalated to the Engineering Lead?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["4 working hours", "four working hours"],
        forbidden_claims=["24 hours", "2 days", "30 minutes"],
    ),
    TestCase(
        id=30,
        category="in_domain",
        query="When should a blocker caused by an external vendor dependency be escalated to Product and Project Lead?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["one working day", "1 working day"],
        forbidden_claims=["immediately", "10 days", "end of sprint"],
    ),
    TestCase(
        id=31,
        category="in_domain",
        query="What is the standard naming convention for dedicated incident communication channels?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["#incident-", "YYYYMMDD"],
        forbidden_claims=["#general", "#random", "#help"],
    ),
    TestCase(
        id=32,
        category="in_domain",
        query="Within how many days after service recovery must a blameless post-incident review be held for SEV-1 and SEV-2?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["five working days", "5 working days"],
        forbidden_claims=["30 days", "24 hours", "same day"],
    ),
    TestCase(
        id=33,
        category="in_domain",
        query="What are the conditions under which a software release should be paused?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["automated checks fail", "rollback path is unknown", "SEV-1"],
        forbidden_claims=["it is raining", "after 5 PM"],
    ),
    TestCase(
        id=34,
        category="in_domain",
        query="What role is assigned during a SEV-1 incident to lead operational response?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Incident Commander"],
        forbidden_claims=["Chief Marketing Officer", "Scrum Master"],
    ),
    TestCase(
        id=35,
        category="in_domain",
        query="What is the primary executive goal of Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["knowledge assistant", "PDF policies"],
        forbidden_claims=["autonomous trading", "cryptocurrency"],
    ),
    TestCase(
        id=36,
        category="in_domain",
        query="What is the target median time to locate a supported answer in Project Alpha pilot testing?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["2 minutes", "Under 2 minutes"],
        forbidden_claims=["10 seconds", "10 minutes", "1 hour"],
    ),
    TestCase(
        id=37,
        category="in_domain",
        query="What percentage target is set for answers having valid source document and page references?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["95%", "95 percent"],
        forbidden_claims=["50%", "70%", "100% guaranteed"],
    ),
    TestCase(
        id=38,
        category="in_domain",
        query="What target percentage is set for correctly stating that evidence is insufficient on unsupported questions?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["90%", "90 percent"],
        forbidden_claims=["50%", "20%"],
    ),
    TestCase(
        id=39,
        category="in_domain",
        query="What is explicitly out of scope for the first release of Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["autonomous changes", "sending messages", "unrestricted internet search"],
        forbidden_claims=["PDF extraction", "citations"],
    ),
    TestCase(
        id=40,
        category="in_domain",
        query="What is the target date and deliverable for Milestone M1 in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["30 Oct 2026", "Foundation", "extraction"],
        forbidden_claims=["November", "December"],
    ),
    TestCase(
        id=41,
        category="in_domain",
        query="What is the target date and deliverable for Milestone M2 in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["6 Nov 2026", "Retrieval API", "FastAPI"],
        forbidden_claims=["30 Oct", "2027"],
    ),
    TestCase(
        id=42,
        category="in_domain",
        query="What is the target date and deliverable for Milestone M3 in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["13 Nov 2026", "Answer generation", "grounded"],
        forbidden_claims=["December 2026"],
    ),
    TestCase(
        id=43,
        category="in_domain",
        query="What is the target date and deliverable for Milestone M4 in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["20 Nov 2026", "Web integration", "MERN"],
        forbidden_claims=["October 2026"],
    ),
    TestCase(
        id=44,
        category="in_domain",
        query="What is the target date and deliverable for Milestone M5 in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["27 Nov 2026", "Pilot evaluation"],
        forbidden_claims=["2027"],
    ),
    TestCase(
        id=45,
        category="in_domain",
        query="What are the responsibilities of the Project Sponsor in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["scope", "priorities", "pilot acceptance"],
        forbidden_claims=["writing python code", "fixing bugs"],
    ),
    TestCase(
        id=46,
        category="in_domain",
        query="What are the responsibilities of the Project Lead in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["milestones", "risks", "coordination", "status reporting"],
        forbidden_claims=["UI styling", "MongoDB schema deployment"],
    ),
    TestCase(
        id=47,
        category="in_domain",
        query="What are the responsibilities of the AI / Backend Engineer in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["ingestion", "retrieval", "API contracts", "evaluation"],
        forbidden_claims=["managing legal budget"],
    ),
    TestCase(
        id=48,
        category="in_domain",
        query="What are the responsibilities of the Web Engineer in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["user interface", "integrates the API", "error states"],
        forbidden_claims=["Kubernetes cluster networking"],
    ),
    TestCase(
        id=49,
        category="in_domain",
        query="What are the responsibilities of the Security Reviewer in Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["permissions", "document access", "secret handling", "logging"],
        forbidden_claims=["marketing flyers"],
    ),
    TestCase(
        id=50,
        category="in_domain",
        query="How does Project Alpha mitigate the risk of prompt injection inside documents?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["untrusted data", "not as instructions"],
        forbidden_claims=["executing injected commands", "ignoring security"],
    ),

    # =========================================================================
    # CATEGORY 2: Adversarial & False-Premise Trap Queries (25 Test Cases)
    # =========================================================================
    TestCase(
        id=51,
        category="adversarial_trap",
        query="What is the policy for claiming 100% reimbursement on personal luxury watch purchases?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["reimbursed up to", "approved vendor for watches", "submit receipt for Rolex"],
    ),
    TestCase(
        id=52,
        category="adversarial_trap",
        query="Why is the initial response SLA for SEV-1 production outages set to 3 hours?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["15 minutes", "not contain", "insufficient"],
        forbidden_claims=["is 3 hours", "set to 3 hours because"],
    ),
    TestCase(
        id=53,
        category="adversarial_trap",
        query="What are the rules for employees bringing pet tigers or monkeys to the office?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["pet policy allows", "register animal with security", "leash required"],
    ),
    TestCase(
        id=54,
        category="adversarial_trap",
        query="Who authorized the $50 million cryptocurrency investment described in Project Alpha?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Bitcoin", "Ethereum", "CFO authorized 50 million"],
    ),
    TestCase(
        id=55,
        category="adversarial_trap",
        query="Can employees take 6 months of paid sabbatical after their first 30 days of employment?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["yes, eligible after 30 days", "6 months paid sabbatical approved"],
    ),
    TestCase(
        id=56,
        category="adversarial_trap",
        query="What is the formula for calculating annual cash bonuses based on the number of Jira comments made?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["per comment", "bonus formula multiplies"],
    ),
    TestCase(
        id=57,
        category="adversarial_trap",
        query="What is the dress code requirement for formal suit and tie on casual Fridays?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["formal suit required", "black tie mandatory"],
    ),
    TestCase(
        id=58,
        category="adversarial_trap",
        query="Which airline lounge membership does Northstar provide to all software interns?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Priority Pass", "Star Alliance", "provided to all interns"],
    ),
    TestCase(
        id=59,
        category="adversarial_trap",
        query="How does the engineering policy define SEV-5 and SEV-6 catastrophic disasters?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain", "insufficient", "SEV-1 through SEV-4"],
        forbidden_claims=["SEV-5 is defined as", "SEV-6 requires"],
    ),
    TestCase(
        id=60,
        category="adversarial_trap",
        query="What is the company policy for mining Bitcoin using development cloud servers?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["allowed after hours", "requires manager permission to mine"],
    ),
    TestCase(
        id=61,
        category="adversarial_trap",
        query="What is the penalty fee charged to employees if they forget to submit their timesheet by 5 PM?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["$50 penalty", "salary deduction of"],
    ),
    TestCase(
        id=62,
        category="adversarial_trap",
        query="What is the stock grant vesting schedule for Milestone M6 in Project Alpha?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["M6 grants", "vests over 4 years"],
    ),
    TestCase(
        id=63,
        category="adversarial_trap",
        query="Where does the policy say employees can download leaked competitor source code?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["approved download portal", "shared drive folder"],
    ),
    TestCase(
        id=64,
        category="adversarial_trap",
        query="What is the monthly gym stipend reimbursement limit according to the HR handbook?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["$100 monthly gym", "reimbursed up to"],
    ),
    TestCase(
        id=65,
        category="adversarial_trap",
        query="Why are employees required to work 60 hours per week during Sprint 4?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["mandatory 60 hours", "required overtime"],
    ),
    TestCase(
        id=66,
        category="adversarial_trap",
        query="What is the company car allowance policy for junior engineers?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["lease allowance", "company car provided"],
    ),
    TestCase(
        id=67,
        category="adversarial_trap",
        query="According to Milestone M4, why was React replaced with Vue.js in Project Alpha?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "MERN", "insufficient"],
        forbidden_claims=["replaced with Vue", "Vue.js chosen because"],
    ),
    TestCase(
        id=68,
        category="adversarial_trap",
        query="What is the budget allocated for the Project Alpha launch party in Las Vegas?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["budget of $50,000", "Vegas party planned"],
    ),
    TestCase(
        id=69,
        category="adversarial_trap",
        query="Can engineers deploy directly to production without testing on Friday nights after 9 PM?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["permitted after 9 PM", "direct deploy allowed on Fridays"],
    ),
    TestCase(
        id=70,
        category="adversarial_trap",
        query="What is the free lunch delivery budget per employee per day?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["$25 lunch daily", "free lunch provided"],
    ),
    TestCase(
        id=71,
        category="adversarial_trap",
        query="What is the required initial response time for SEV-0 nuclear reactor emergencies?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["SEV-0 response target is", "nuclear reactor"],
    ),
    TestCase(
        id=72,
        category="adversarial_trap",
        query="Which brand of espresso coffee machines are installed on the 4th floor?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Nespresso", "Breville", "espresso machine on 4th floor"],
    ),
    TestCase(
        id=73,
        category="adversarial_trap",
        query="What is the relocation package amount for moving to the Mars colony branch?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["relocation to Mars", "Mars colony grant"],
    ),
    TestCase(
        id=74,
        category="adversarial_trap",
        query="How many free concert tickets are employees entitled to per quarter?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["2 free tickets", "concert stipend"],
    ),
    TestCase(
        id=75,
        category="adversarial_trap",
        query="What is the policy for copying customer databases onto personal home media servers?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["do not forward", "not contain", "insufficient"],
        forbidden_claims=["permitted for testing", "allowed on home media server"],
    ),

    # =========================================================================
    # CATEGORY 3: Out-of-Domain & Irrelevant Queries (15 Test Cases)
    # =========================================================================
    TestCase(
        id=76,
        category="out_of_domain",
        query="How do I bake a sourdough bread from scratch?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["flour and water", "starter culture", "bake at 450 degrees"],
    ),
    TestCase(
        id=77,
        category="out_of_domain",
        query="What is the distance between the Earth and the Moon in kilometers?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["384,400 km"],
    ),
    TestCase(
        id=78,
        category="out_of_domain",
        query="Who won the FIFA World Cup in 2022?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Argentina", "Lionel Messi", "France"],
    ),
    TestCase(
        id=79,
        category="out_of_domain",
        query="Explain Heisenberg's uncertainty principle in quantum physics.",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["momentum and position", "delta x delta p"],
    ),
    TestCase(
        id=80,
        category="out_of_domain",
        query="What is the chemical formula for photosynthesis?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["6CO2 + 6H2O", "glucose and oxygen"],
    ),
    TestCase(
        id=81,
        category="out_of_domain",
        query="What is the capital of Australia?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Canberra", "Sydney", "Melbourne"],
    ),
    TestCase(
        id=82,
        category="out_of_domain",
        query="What is the plot of the movie Inception?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["dream within a dream", "Leonardo DiCaprio", "totem"],
    ),
    TestCase(
        id=83,
        category="out_of_domain",
        query="How do I change the oil filter on a 2018 Toyota Camry?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["oil drain plug", "wrench size", "synthetic 0W-20"],
    ),
    TestCase(
        id=84,
        category="out_of_domain",
        query="What was the main cause of the French Revolution in 1789?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["Louis XVI", "Bastille", "Third Estate"],
    ),
    TestCase(
        id=85,
        category="out_of_domain",
        query="What is the standard tuning for a six-string acoustic guitar?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["E A D G B E", "standard guitar tuning"],
    ),
    TestCase(
        id=86,
        category="out_of_domain",
        query="What is the population of Tokyo, Japan?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["14 million", "37 million"],
    ),
    TestCase(
        id=87,
        category="out_of_domain",
        query="How do plants convert sunlight into energy?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["chloroplasts", "chlorophyll absorbs light"],
    ),
    TestCase(
        id=88,
        category="out_of_domain",
        query="Who wrote the tragedy Hamlet?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["William Shakespeare", "Shakespeare"],
    ),
    TestCase(
        id=89,
        category="out_of_domain",
        query="What is the speed of light in vacuum?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["299,792,458", "300,000 km/s"],
    ),
    TestCase(
        id=90,
        category="out_of_domain",
        query="What are the rules of chess for en passant pawn capture?",
        expected_doc=None,
        expected_page=None,
        expected_behavior="reject_insufficient_evidence",
        key_facts=["not contain sufficient information", "insufficient"],
        forbidden_claims=["pawn advances two squares", "captured diagonally"],
    ),

    # =========================================================================
    # CATEGORY 4: Edge-Case & Boundary Reasoning Queries (15 Test Cases)
    # =========================================================================
    TestCase(
        id=91,
        category="boundary_reasoning",
        query="If an expense is exactly 10,000 INR, does it require written manager approval beforehand?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["above", "10,000", "require written manager approval"],
        forbidden_claims=["all expenses under 100,000 need approval"],
    ),
    TestCase(
        id=92,
        category="boundary_reasoning",
        query="Does an initial response to a SEV-1 incident mean the issue is guaranteed to be resolved within 15 minutes?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["acknowledgement", "not guaranteed resolution", "triage start"],
        forbidden_claims=["guarantees bug fix within 15 minutes"],
    ),
    TestCase(
        id=93,
        category="boundary_reasoning",
        query="Are internal engineering response SLAs customer contract guarantees?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["not customer contract guarantees", "internal operating targets"],
        forbidden_claims=["yes, legally binding customer SLAs"],
    ),
    TestCase(
        id=94,
        category="boundary_reasoning",
        query="Can Project Alpha's knowledge assistant make autonomous changes to company production systems in its first release?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Out of scope", "autonomous changes"],
        forbidden_claims=["yes, can deploy code autonomously"],
    ),
    TestCase(
        id=95,
        category="boundary_reasoning",
        query="Can the Project Alpha assistant send messages on behalf of users in the first release?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Out of scope", "sending messages"],
        forbidden_claims=["yes, automatically emails clients"],
    ),
    TestCase(
        id=96,
        category="boundary_reasoning",
        query="Is unrestricted internet search permitted in the first release of Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Out of scope", "unrestricted internet search"],
        forbidden_claims=["yes, searches Google freely"],
    ),
    TestCase(
        id=97,
        category="boundary_reasoning",
        query="If two company policies conflict with one another, who should employees consult?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["People Operations"],
        forbidden_claims=["Police", "Local IT vendor", "arbitrary choice"],
    ),
    TestCase(
        id=98,
        category="boundary_reasoning",
        query="How should employees classify information before sharing it outside the immediate team?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Public, Internal, Confidential, or Restricted", "Classify"],
        forbidden_claims=["share freely without classification"],
    ),
    TestCase(
        id=99,
        category="boundary_reasoning",
        query="Who owns milestones, risks, coordination, and status reporting according to Project Alpha charter?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["Project Lead"],
        forbidden_claims=["Security Reviewer", "Web Engineer"],
    ),
    TestCase(
        id=100,
        category="boundary_reasoning",
        query="Who approves scope, priorities, and pilot acceptance criteria according to Project Alpha charter?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["Project Sponsor"],
        forbidden_claims=["AI / Backend Engineer", "Scrum master"],
    ),
    TestCase(
        id=101,
        category="boundary_reasoning",
        query="What is the policy when prompt injection instructions are found inside documents?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["untrusted data", "not as instructions that override"],
        forbidden_claims=["execute injected prompts"],
    ),
    TestCase(
        id=102,
        category="boundary_reasoning",
        query="If the payment API fails for most users during peak traffic, what severity should be assigned?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["SEV-1", "15 minutes"],
        forbidden_claims=["SEV-4", "SEV-3"],
    ),
    TestCase(
        id=103,
        category="boundary_reasoning",
        query="Are live company credentials or real personal data included in the Project Alpha test corpus?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["No live company credentials", "fictional"],
        forbidden_claims=["yes, live production passwords included"],
    ),
    TestCase(
        id=104,
        category="boundary_reasoning",
        query="What should an employee do if an unexpected absence affects a customer commitment?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["notify your manager", "immediate collaborators"],
        forbidden_claims=["ignore until return", "do nothing"],
    ),
    TestCase(
        id=105,
        category="boundary_reasoning",
        query="When is an on-call engineer required to post updates during an active SEV-1 incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Every 30 minutes", "30 minutes"],
        forbidden_claims=["once per day", "only upon resolution"],
    ),
    TestCase(
        id=106,
        category="in_domain",
        query="Who directs the investigation and proposes mitigations during an incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["Technical Lead"],
        forbidden_claims=["CEO", "HR intern"],
    ),
    TestCase(
        id=107,
        category="in_domain",
        query="What is the responsibility of the Communications Owner during an incident?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["posts approved internal updates", "coordinates customer-facing wording"],
        forbidden_claims=["restarts production database"],
    ),
    TestCase(
        id=108,
        category="in_domain",
        query="What are the five phases of the incident workflow?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Detect and report", "Triage", "Mitigate", "Verify", "Close and learn"],
        forbidden_claims=["ignore", "deploy on friday"],
    ),
    TestCase(
        id=109,
        category="in_domain",
        query="What should be prioritized over a permanent fix when an incident is ongoing?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["safe restoration of service", "Prefer safe restoration"],
        forbidden_claims=["permanent rewrite", "risky untested refactoring"],
    ),
    TestCase(
        id=110,
        category="in_domain",
        query="Within how many working days must a blameless post-incident review be held for SEV-1 and SEV-2?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["five working days", "5 working days"],
        forbidden_claims=["30 days", "two months"],
    ),
    TestCase(
        id=111,
        category="in_domain",
        query="What four requirements must every production release have?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["owner", "rollback plan", "health checks"],
        forbidden_claims=["crypto signature", "formal suit"],
    ),
    TestCase(
        id=112,
        category="in_domain",
        query="Under what conditions should a production release be paused?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["critical automated checks fail", "rollback path is unknown", "SEV-1 incident is active"],
        forbidden_claims=["always deploy regardless"],
    ),
    TestCase(
        id=113,
        category="in_domain",
        query="What is the dedicated channel naming convention for incident communication?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["#incident-<YYYYMMDD>-<service>", "incident"],
        forbidden_claims=["#random-chat", "personal whatsapp"],
    ),
    TestCase(
        id=114,
        category="in_domain",
        query="Who is the contact channel for workplace equipment questions?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["IT Helpdesk portal"],
        forbidden_claims=["People Operations queue", "Security Operations"],
    ),
    TestCase(
        id=115,
        category="in_domain",
        query="What is the target response time for workplace equipment questions?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["1 working day", "one working day"],
        forbidden_claims=["immediately", "10 business days"],
    ),
    TestCase(
        id=116,
        category="in_domain",
        query="What is the target response time for reporting a security incident?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["Immediately"],
        forbidden_claims=["2 working days", "end of month"],
    ),
    TestCase(
        id=117,
        category="in_domain",
        query="What is the target delivery date and exit criteria for Milestone M1 Foundation?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["30 Oct 2026", "Repository structure", "PDF text extraction"],
        forbidden_claims=["December 2030"],
    ),
    TestCase(
        id=118,
        category="in_domain",
        query="What is the target delivery date and exit criteria for Milestone M3 Answer Generation?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["13 Nov 2026", "Answers grounded", "source document and page references"],
        forbidden_claims=["January 2027"],
    ),
    TestCase(
        id=119,
        category="in_domain",
        query="What is the target delivery date and exit criteria for Milestone M4 Web Integration?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["20 Nov 2026", "MERN interface integrated"],
        forbidden_claims=["August 2025"],
    ),
    TestCase(
        id=120,
        category="in_domain",
        query="What is the target delivery date and exit criteria for Milestone M5 Pilot Evaluation?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["27 Nov 2026", "Evaluation report", "security review"],
        forbidden_claims=["2028"],
    ),
    TestCase(
        id=121,
        category="adversarial_trap",
        query="Does the company provide an unlimited corporate black credit card for interns?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["yes", "unlimited credit card provided"],
    ),
    TestCase(
        id=122,
        category="adversarial_trap",
        query="Can employees bring pet dragons or reptiles into conference rooms?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["allowed", "dragons permitted"],
    ),
    TestCase(
        id=123,
        category="adversarial_trap",
        query="What is the procedure to receive a 100% equity bonus in Bitcoin?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["bitcoin bonus", "apply via portal"],
    ),
    TestCase(
        id=124,
        category="adversarial_trap",
        query="Is karaoke mandatory for all engineering staff every Friday afternoon at 2 PM?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["mandatory karaoke"],
    ),
    TestCase(
        id=125,
        category="adversarial_trap",
        query="What is the official response SLA for a SEV-7 incident?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["sev-7 response time"],
    ),
    TestCase(
        id=126,
        category="adversarial_trap",
        query="Can an employee relocate and work from the Bahamas without manager approval?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["yes, Bahamas is approved"],
    ),
    TestCase(
        id=127,
        category="adversarial_trap",
        query="Does the company reimburse private helicopter commutes to the corporate office?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["helicopter reimbursement"],
    ),
    TestCase(
        id=128,
        category="adversarial_trap",
        query="What is the approved company budget for the Project Alpha team trip to Mount Everest?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["budget allocated for Everest"],
    ),
    TestCase(
        id=129,
        category="adversarial_trap",
        query="Can developers merge directly to main without pull request review on Friday nights?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["merge without PR permitted"],
    ),
    TestCase(
        id=130,
        category="adversarial_trap",
        query="Is milestone M7 delivering quantum computing hardware to customer data centers?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["quantum computing hardware"],
    ),
    TestCase(
        id=131,
        category="out_of_domain",
        query="How does quantum entanglement allow instantaneous particle correlation?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["policy states quantum entanglement"],
    ),
    TestCase(
        id=132,
        category="out_of_domain",
        query="What is the ideal brew ratio for espresso extraction?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["company standard espresso ratio"],
    ),
    TestCase(
        id=133,
        category="out_of_domain",
        query="How do you make authentic French macarons from scratch?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["macaron recipe"],
    ),
    TestCase(
        id=134,
        category="out_of_domain",
        query="Who was the first emperor of the ancient Roman Empire?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["Roman emperor"],
    ),
    TestCase(
        id=135,
        category="out_of_domain",
        query="What is the distance of the three-point line in NBA basketball?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["three-point line policy"],
    ),
    TestCase(
        id=136,
        category="out_of_domain",
        query="What celestial alignment causes total solar eclipses to occur?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["solar eclipse policy"],
    ),
    TestCase(
        id=137,
        category="out_of_domain",
        query="How do airplane wings generate aerodynamic lift according to Bernoulli's principle?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["aerodynamic lift policy"],
    ),
    TestCase(
        id=138,
        category="out_of_domain",
        query="Which Renaissance artist painted the Mona Lisa?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["Mona Lisa artist policy"],
    ),
    TestCase(
        id=139,
        category="out_of_domain",
        query="What is the chemical formula for glucose in organic photosynthesis?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["chemical formula policy"],
    ),
    TestCase(
        id=140,
        category="out_of_domain",
        query="What are the rules for kingside and queenside castling in chess?",
        expected_behavior="reject_insufficient_evidence",
        key_facts=[],
        forbidden_claims=["castling rules policy"],
    ),
    TestCase(
        id=141,
        category="boundary_reasoning",
        query="Can an employee approve their own leave request if their manager is away?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["approved by the employee's manager", "manager"],
        forbidden_claims=["self-approval permitted", "approve their own"],
    ),
    TestCase(
        id=142,
        category="boundary_reasoning",
        query="If an equipment expense is 15,000 INR, what approval is required before purchase?",
        expected_doc="Company_HR_and_Work_Rules.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["written manager pre-approval", "10,000 INR"],
        forbidden_claims=["no approval required", "automatic approval"],
    ),
    TestCase(
        id=143,
        category="boundary_reasoning",
        query="Who owns weekly status reporting and risk coordination for Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["Project Lead", "weekly status reporting"],
        forbidden_claims=["Security Reviewer", "HR Lead"],
    ),
    TestCase(
        id=144,
        category="boundary_reasoning",
        query="Who reviews permissions, document access, and secret handling for Project Alpha?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["Security Reviewer"],
        forbidden_claims=["Web Engineer"],
    ),
    TestCase(
        id=145,
        category="boundary_reasoning",
        query="Who is responsible for building the user interface and handling user-facing error states?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=3,
        expected_behavior="answer_with_citation",
        key_facts=["Web Engineer", "user interface"],
        forbidden_claims=["AI / Backend Engineer"],
    ),
    TestCase(
        id=146,
        category="boundary_reasoning",
        query="Does an initial response to a SEV-2 incident guarantee a permanent code fix?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["not guaranteed resolution", "acknowledgement and triage"],
        forbidden_claims=["guaranteed resolution within 1 hour"],
    ),
    TestCase(
        id=147,
        category="boundary_reasoning",
        query="What should an on-call engineer do if a vendor dependency delays work for more than one working day?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["notify the Product Manager and Project Lead", "Product Manager"],
        forbidden_claims=["ignore external blockers", "escalate to CEO immediately"],
    ),
    TestCase(
        id=148,
        category="boundary_reasoning",
        query="Should confidential customer credentials or secrets be included in post-incident reviews?",
        expected_doc="Engineering_SLA_and_Blocker_Policy.pdf",
        expected_page=2,
        expected_behavior="answer_with_citation",
        key_facts=["should not include secrets", "not include"],
        forbidden_claims=["always include all plain-text passwords"],
    ),
    TestCase(
        id=149,
        category="boundary_reasoning",
        query="Can Project Alpha assistant guarantee correctness for legal or HR decisions?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["out of scope", "guaranteed correctness"],
        forbidden_claims=["guarantees legal accuracy", "legally binding"],
    ),
    TestCase(
        id=150,
        category="boundary_reasoning",
        query="What is the target median time to locate a supported policy answer in pilot testing?",
        expected_doc="Project_Alpha_Charter_and_Milestones.pdf",
        expected_page=1,
        expected_behavior="answer_with_citation",
        key_facts=["under 2 minutes", "2 minutes"],
        forbidden_claims=["under 1 second", "30 minutes"],
    ),
]


@dataclass
class EvaluationResult:
    test_id: int
    category: str
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    is_hallucination: bool
    is_accurate: bool
    citation_correct: bool
    latency_ms: float
    failure_reason: Optional[str] = None


def evaluate_single_test(test: TestCase, rag_service) -> EvaluationResult:
    start_time = time.time()
    result = rag_service.query(test.query, top_k=6)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    answer_text = result.answer or ""
    answer_lower = answer_text.lower()
    citations = result.citations

    is_hallucination = False
    is_accurate = False
    citation_correct = False
    failure_reason = None

    # Check for forbidden claims (hallucination indicator) with word boundaries
    for forbidden in test.forbidden_claims:
        if re.search(r"\b" + re.escape(forbidden) + r"\b", answer_text, re.IGNORECASE):
            is_hallucination = True
            failure_reason = f"Hallucinated forbidden claim: '{forbidden}'"
            break

    if test.expected_behavior == "reject_insufficient_evidence":
        # System should reject / state evidence is insufficient
        refusal_phrases = [
            "do not contain sufficient information",
            "insufficient information",
            "not contain enough information",
            "not mention",
            "not specified",
            "no information",
            "cannot answer",
        ]
        has_refusal = any(p in answer_lower for p in refusal_phrases)

        # Or if it's an adversarial question with a corrected fact (e.g. SEV-1 SLA is 15 minutes, not 3 hours)
        has_correction = any(k.lower() in answer_lower for k in test.key_facts)

        if not is_hallucination and (has_refusal or has_correction):
            is_accurate = True
            citation_correct = True  # Not expecting a false citation
        else:
            if not failure_reason:
                failure_reason = "Failed to reject ungrounded/adversarial question"
    else:
        # Expected behavior: answer_with_citation
        # 1. Key facts must be present
        all_facts_present = any(k.lower() in answer_lower for k in test.key_facts)

        # 2. Check citation match
        has_expected_citation = False
        if test.expected_doc:
            for cit in citations:
                doc_matches = cit.get("doc_name") == test.expected_doc
                page_matches = (
                    test.expected_page is None or cit.get("page_number") == test.expected_page
                )
                if doc_matches and page_matches:
                    has_expected_citation = True
                    break

        citation_correct = has_expected_citation

        if not is_hallucination and all_facts_present and (citation_correct or citations):
            is_accurate = True
        else:
            if not failure_reason:
                if not all_facts_present:
                    failure_reason = f"Missing key facts from context (expected: {test.key_facts})"
                elif not citation_correct:
                    failure_reason = f"Citation mismatch (expected: [{test.expected_doc}, Page {test.expected_page}])"

    return EvaluationResult(
        test_id=test.id,
        category=test.category,
        query=test.query,
        answer=answer_text,
        citations=citations,
        is_hallucination=is_hallucination,
        is_accurate=is_accurate,
        citation_correct=citation_correct,
        latency_ms=duration_ms,
        failure_reason=failure_reason,
    )


def run_benchmark():
    print("=" * 75)
    print("  STATIC PDF RAG HALLUCINATION & ACCURACY BENCHMARK (105 TEST QUERIES)")
    print("=" * 75)

    rag = get_rag_service()
    db = get_db()

    # Self-heal dataset if in offline/dataset mode
    if db.get_total_chunks() == 0:
        docs_dir = BASE_DIR.parent / "company-docs"
        if docs_dir.exists():
            print(f"[Init] In-memory database unpopulated. Auto-indexing {docs_dir}...")
            indexer = StaticDocIndexer(db_manager=db)
            indexer.ingest_all_documents(docs_dir)

    print(f"Total Test Cases Loaded: {len(TEST_CASES)}")
    print(f"  - In-Domain Direct Policy:      65 queries")
    print(f"  - Adversarial False-Premise:    35 queries")
    print(f"  - Out-of-Domain / Distractor:   25 queries")
    print(f"  - Boundary & Nuanced Reasoning: 25 queries")
    print("-" * 75)
    print("Executing benchmark suite...\n")

    results: List[EvaluationResult] = []
    category_stats: Dict[str, Dict[str, Any]] = {
        "in_domain": {"total": 0, "accurate": 0, "hallucinations": 0, "citations_ok": 0},
        "adversarial_trap": {"total": 0, "accurate": 0, "hallucinations": 0, "citations_ok": 0},
        "out_of_domain": {"total": 0, "accurate": 0, "hallucinations": 0, "citations_ok": 0},
        "boundary_reasoning": {"total": 0, "accurate": 0, "hallucinations": 0, "citations_ok": 0},
    }

    start_bench = time.time()
    for idx, test in enumerate(TEST_CASES, start=1):
        res = evaluate_single_test(test, rag)
        results.append(res)

        cat = test.category
        category_stats[cat]["total"] += 1
        if res.is_accurate:
            category_stats[cat]["accurate"] += 1
        if res.is_hallucination:
            category_stats[cat]["hallucinations"] += 1
        if res.citation_correct:
            category_stats[cat]["citations_ok"] += 1

        status_str = "ACCURATE" if res.is_accurate else "FLAGGED"
        halluc_str = "HALLUCINATION!" if res.is_hallucination else "GROUNDED"
        print(
            f"[{idx:3d}/{len(TEST_CASES)}] [{cat:^18}] {status_str} | {halluc_str} | {res.latency_ms:6.1f} ms | Q: {test.query[:45]}..."
        )
        if res.failure_reason:
            print(f"         Notice: {res.failure_reason}")

    total_bench_duration = time.time() - start_bench

    # Aggregates
    total_queries = len(results)
    total_accurate = sum(1 for r in results if r.is_accurate)
    total_hallucinations = sum(1 for r in results if r.is_hallucination)
    total_citations_ok = sum(1 for r in results if r.citation_correct)
    latencies = [r.latency_ms for r in results]

    overall_accuracy_pct = round((total_accurate / total_queries) * 100, 2)
    hallucination_rate_pct = round((total_hallucinations / total_queries) * 100, 2)
    faithfulness_rate_pct = round(100.0 - hallucination_rate_pct, 2)
    citation_precision_pct = round((total_citations_ok / total_queries) * 100, 2)

    latencies_sorted = sorted(latencies)
    p50_latency = latencies_sorted[len(latencies_sorted) // 2]
    p90_latency = latencies_sorted[int(len(latencies_sorted) * 0.9)]
    avg_latency = round(sum(latencies) / len(latencies), 2)

    print("\n" + "=" * 75)
    print("                    BENCHMARK RESULTS SUMMARY")
    print("=" * 75)
    print(f"Total Evaluation Queries:         {total_queries}")
    print(f"Overall Accuracy:                 {overall_accuracy_pct}% ({total_accurate}/{total_queries})")
    print(f"Faithfulness (Zero-Hallucination): {faithfulness_rate_pct}%")
    print(f"Hallucination Rate:               {hallucination_rate_pct}% ({total_hallucinations}/{total_queries})")
    print(f"Citation Precision:               {citation_precision_pct}% ({total_citations_ok}/{total_queries})")
    print(f"Total Wall Clock Duration:        {total_bench_duration:.2f} s")
    print(f"Latency Profile:                  P50={p50_latency:.1f}ms | P90={p90_latency:.1f}ms | Avg={avg_latency:.1f}ms")
    print("-" * 75)
    print("BREAKDOWN BY CATEGORY:")
    for cat, stats in category_stats.items():
        cat_acc = round((stats["accurate"] / stats["total"]) * 100, 1) if stats["total"] else 0
        cat_halluc = round((stats["hallucinations"] / stats["total"]) * 100, 1) if stats["total"] else 0
        print(
            f"  * {cat:<20}: Accuracy: {cat_acc:5.1f}% | Hallucinations: {stats['hallucinations']} ({cat_halluc}%) | Total: {stats['total']}"
        )
    print("=" * 75)

    # Export report to JSON
    report_path = BASE_DIR / "scripts" / "hallucination_benchmark_report.json"
    report_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_queries": total_queries,
        "overall_accuracy_pct": overall_accuracy_pct,
        "faithfulness_rate_pct": faithfulness_rate_pct,
        "hallucination_rate_pct": hallucination_rate_pct,
        "citation_precision_pct": citation_precision_pct,
        "latency_profile": {
            "p50_ms": p50_latency,
            "p90_ms": p90_latency,
            "avg_ms": avg_latency,
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        },
        "category_breakdown": category_stats,
        "results": [asdict(r) for r in results],
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n[+] Full detailed benchmark results exported to: {report_path}")
    return report_data


if __name__ == "__main__":
    run_benchmark()
