"""Build the explicitly curated scheme cards against exact archived passage IDs.

These records are research annotations, not activated rules. Re-run after a crawl;
the build fails if a referenced source line changes or disappears.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "research"
passages = json.loads((ROOT / "passages.json").read_text())
by_source = {(p["source_id"], int(p["id"].split(":")[-1])): p for p in passages}


def field(value, *refs):
    ids = []
    for source, line in refs:
        passage = by_source.get((source, line))
        if passage is None:
            raise ValueError(f"Missing citation {source}:{line}; review the changed source before rebuilding")
        ids.append(passage["id"])
    return {"value": value, "passages": ids}


COMMON = {"department": "Directorate of Social Security and Pensions, Revenue Department", "review_status": "pending independent rule and order review", "assessment_enabled": False, "source_version_policy": "Web page and listed orders need independent comparison before activation"}

records = [
    dict(COMMON, id="ka-ignoaps", name="Indira Gandhi National Old Age Pension Scheme", name_kn="ಇಂದಿರಾ ಗಾಂಧಿ ರಾಷ್ಟ್ರೀಯ ವೃದ್ಧಾಪ್ಯ ವೇತನ ಯೋಜನೆ", primary_url="https://dssp.karnataka.gov.in/dssp/IndiraGandhiPension.aspx", eligibility=[
        field("Age 60 years or older", ("dssp-ignoaps", 4)),
        field("Below poverty line (BPL)", ("dssp-ignoaps", 4)),
        field("Annual income below ₹32,000", ("dssp-ignoaps", 6)),
        field("Must not receive another public or private pension, including widow, disability or Sandhya Suraksha pension", ("dssp-ignoaps", 8)),
    ], exceptions=[field("Having adult sons does not exclude a person if they do not support the applicant", ("dssp-ignoaps", 10))], benefits=[field("The page lists ₹600 for ages 60–64 and ₹1,200 for ages 65 and above; current applicability needs order review", ("dssp-ignoaps", 24), ("dssp-ignoaps", 27))], application_documents=[field("Residence certificate", ("dssp-ignoaps", 15)), field("Proof of age", ("dssp-ignoaps", 17)), field("Bank or postal account details", ("dssp-ignoaps", 19)), field("Aadhaar card", ("dssp-ignoaps", 21))], application=[field("Apply through the Atalji Janasnehi Kendra for the applicant's place of residence", ("dssp-ignoaps", 29))], unresolved=["Effective date and supersession of all eligibility clauses need review against linked orders", "BPL determination and pension exclusion are not supported by the current OCR fact schema"]),
    dict(COMMON, id="ka-sandhya", name="Sandhya Suraksha Yojana", name_kn="ಸಂಧ್ಯಾ ಸುರಕ್ಷಾ ಯೋಜನೆ", primary_url="https://dssp.karnataka.gov.in/dssp/Sandhya_Suraksha.aspx", eligibility=[
        field("Age 65 years or older", ("dssp-sandhya", 1)),
        field("Applicant is in one of the listed occupations: small or marginal farmer, agricultural labourer, weaver, fisher or unorganised worker", ("dssp-sandhya", 3), ("dssp-sandhya", 5), ("dssp-sandhya", 7), ("dssp-sandhya", 11), ("dssp-sandhya", 13)),
        field("Combined annual income of applicant and spouse must not exceed ₹32,000", ("dssp-sandhya", 16)),
        field("Combined deposits of applicant and spouse must not exceed ₹10,000", ("dssp-sandhya", 18)),
        field("No pension from a public or private source", ("dssp-sandhya", 20)),
    ], exceptions=[field("Certain construction workers and those receiving pension under the cited construction-workers law are excluded", ("dssp-sandhya", 13)), field("Sons who do not support the applicant do not automatically exclude the applicant", ("dssp-sandhya", 22))], benefits=[field("The page lists a pension amount of ₹1,200; current applicability needs order review", ("dssp-sandhya", 34))], application_documents=[field("Residence certificate", ("dssp-sandhya", 25)), field("Proof of age", ("dssp-sandhya", 27)), field("Bank or postal account details", ("dssp-sandhya", 29)), field("Aadhaar card", ("dssp-sandhya", 31)), field("Ration card number", ("dssp-sandhya", 33))], application=[field("Apply through the Atalji Janasnehi Kendra for the applicant's place of residence", ("dssp-sandhya", 35))], unresolved=["The 2021 government order is archived but its Kannada text extraction is unusable; independent review needed", "Occupation, combined deposits and pension exclusions are not supported by current OCR fact schema"]),
    dict(COMMON, id="ka-widow", name="Widow Pension Scheme", name_kn="ವಿಧವಾ ವೇತನ ಯೋಜನೆ", primary_url="https://dssp.karnataka.gov.in/dssp/Widow_Scheme.aspx", eligibility=[field("Widow aged 18 to 64 and below poverty line", ("dssp-widow", 1)), field("Annual income below ₹32,000", ("dssp-widow", 6)), field("Widowhood as described on the official page", ("dssp-widow", 4))], exceptions=[field("Pension ceases on remarriage or on employment with income above the prescribed annual limit", ("dssp-widow", 8))], benefits=[field("The page lists a pension amount of ₹800; current applicability needs order review", ("dssp-widow", 18))], application_documents=[field("Residence certificate", ("dssp-widow", 11)), field("Proof of age", ("dssp-widow", 13)), field("Bank or postal account details", ("dssp-widow", 15)), field("Aadhaar card", ("dssp-widow", 17))], application=[field("Apply through the Atalji Janasnehi Kendra for the applicant's place of residence", ("dssp-widow", 19))], unresolved=["Linked government orders and current supersession need independent review", "Widowhood, remarriage and BPL status are not supported by current OCR fact schema"]),
]

(ROOT / "schemes.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {len(records)} source-linked scheme records")
