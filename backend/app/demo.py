"""Fictional test specification. These thresholds are NOT government rules."""

from copy import deepcopy


def demo_rule(scheme_id="demo-silver", version=1):
    conditions = [
        dict(
            id="age",
            description="Age is at least 60 years",
            description_kn="ವಯಸ್ಸು ಕನಿಷ್ಠ 60 ವರ್ಷಗಳು",
            fact="age",
            op="gte",
            value=60,
            datatype="number",
            unit="years",
            evidence_types=["age_proof"],
            clause="demo:age",
        ),
        dict(
            id="residence",
            description="Residence is Karnataka",
            description_kn="ಕರ್ನಾಟಕದಲ್ಲಿ ವಾಸ",
            fact="state",
            op="eq",
            value="Karnataka",
            datatype="string",
            unit="text",
            evidence_types=["residence"],
            clause="demo:residence",
        ),
        dict(
            id="income",
            description="Annual income is at most ₹50,000",
            description_kn="ವಾರ್ಷಿಕ ಆದಾಯ ₹50,000 ಮೀರಬಾರದು",
            fact="annual_income",
            op="lte",
            value=50000,
            datatype="number",
            unit="INR/year",
            evidence_types=["income"],
            clause="demo:income",
            max_age_days=366,
        ),
    ]
    return dict(
        scheme_id=scheme_id,
        version=version,
        mode="DEMO",
        effective_from="2020-01-01",
        effective_to=None,
        conditions=deepcopy(conditions),
        root={"op": "AND", "args": ["age", "residence", "income"]},
        clauses={
            "demo:age": "FICTIONAL clause A: applicant must be aged 60 or above.",
            "demo:residence": "FICTIONAL clause B: applicant must reside in Karnataka.",
            "demo:income": "FICTIONAL clause C: annual income at most INR 50,000, evidenced within 366 days.",
        },
        application_documents=["bank_account_details"],
    )


SCHEMES = [
    {
        "id": "demo-silver",
        "name": "Silver Years Support · Fictional demo",
        "name_kn": "ಹಿರಿಯರ ನೆರವು · ಕಾಲ್ಪನಿಕ ಮಾದರಿ",
        "category": "Financial assistance",
        "department": "Fictional demonstration office",
        "description": "A synthetic learning example for document-backed assessment. No benefits or applications exist.",
        "mode": "DEMO",
        "status": "approved",
    },
    {
        "id": "demo-care",
        "name": "Community Care · Fictional demo",
        "name_kn": "ಸಮುದಾಯ ಆರೈಕೆ · ಕಾಲ್ಪನಿಕ ಮಾದರಿ",
        "category": "Care support",
        "department": "Fictional demonstration office",
        "description": "A second fictional example using the same independently specified demonstration conditions.",
        "mode": "DEMO",
        "status": "approved",
    },
    {
        "id": "ka-sandhya",
        "name": "Sandhya Suraksha Yojana",
        "name_kn": "ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆ",
        "category": "Pension",
        "department": "Government of Karnataka",
        "description": "Official source linked research card available. Government orders and full rules need independent review before assessment.",
        "mode": "REVIEWED",
        "status": "unavailable",
        "source_url": "https://dssp.karnataka.gov.in/dssp/Sandhya_Suraksha.aspx",
    },
    {
        "id": "ka-ignoaps",
        "name": "Indira Gandhi National Old Age Pension Scheme",
        "name_kn": "ಇಂದಿರಾ ಗಾಂಧಿ ರಾಷ್ಟ್ರೀಯ ವೃದ್ಧಾಪ್ಯ ವೇತನ ಯೋಜನೆ",
        "category": "Pension",
        "department": "Government of Karnataka",
        "description": "Official source linked research card available. Full rule and order review is required before assessment.",
        "mode": "REVIEWED",
        "status": "unavailable",
        "source_url": "https://dssp.karnataka.gov.in/dssp/IndiraGandhiPension.aspx",
    },
    {
        "id": "ka-widow",
        "name": "Widow Pension Scheme",
        "name_kn": "ವಿಧವಾ ವೇತನ ಯೋಜನೆ",
        "category": "Pension",
        "department": "Government of Karnataka",
        "description": "Official source linked research card available. Full rule and order review is required before assessment.",
        "mode": "REVIEWED",
        "status": "unavailable",
        "source_url": "https://dssp.karnataka.gov.in/dssp/Widow_Scheme.aspx",
    },
]
