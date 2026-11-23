"""Shared report vocabulary. Source clauses retain their source language."""

KN = {
    "LIKELY_ELIGIBLE": "ಅರ್ಹರಾಗಿರುವ ಸಾಧ್ಯತೆ",
    "NEEDS_EVIDENCE": "ಹೆಚ್ಚಿನ ದಾಖಲೆ ಬೇಕು",
    "NOT_ELIGIBLE": "ಅರ್ಹರಲ್ಲ",
    "SATISFIED": "ಷರತ್ತು ಪೂರೈಸಿದೆ",
    "NOT_SATISFIED": "ಷರತ್ತು ಪೂರೈಸಿಲ್ಲ",
    "INSUFFICIENT_EVIDENCE": "ಸಾಕಷ್ಟು ದಾಖಲೆ ಇಲ್ಲ",
    "CONDITION_MET": "ದಾಖಲೆ ಈ ಷರತ್ತನ್ನು ಪೂರೈಸುತ್ತದೆ",
    "CONDITION_NOT_MET": "ದಾಖಲೆ ಈ ಷರತ್ತನ್ನು ಪೂರೈಸುವುದಿಲ್ಲ",
    "MISSING_DOCUMENT": "ಅಗತ್ಯವಾದ ದಾಖಲೆ ಸೇರಿಸಿ",
    "MISSING_FIELD": "ಅಗತ್ಯವಾದ ಮಾಹಿತಿ ಕಂಡುಬಂದಿಲ್ಲ",
    "UNCONFIRMED_FIELD": "ಮಾಹಿತಿಯನ್ನು ಪರಿಶೀಲಿಸಿ ದೃಢೀಕರಿಸಿ",
    "UNVERIFIED_CORRECTION": "ತಿದ್ದುಪಡಿಗೆ ಬದಲಿ ದಾಖಲೆ ಬೇಕು",
    "LOW_OCR_CONFIDENCE": "ಸ್ಪಷ್ಟ ದಾಖಲೆ ಸೇರಿಸಿ",
    "CONFLICTING_EVIDENCE": "ದಾಖಲೆಗಳಲ್ಲಿ ವ್ಯತ್ಯಾಸವಿದೆ",
    "EXPIRED_DOCUMENT": "ಈಗಿನ ಮಾನ್ಯ ದಾಖಲೆ ಒದಗಿಸಿ",
    "UNSUPPORTED_DOCUMENT": "ದಾಖಲೆಯ ವಿಧ ಹೊಂದುವುದಿಲ್ಲ",
    "AMBIGUOUS_VALUE": "ಮೌಲ್ಯ ಸ್ಪಷ್ಟವಿಲ್ಲ",
    "UNREADABLE": "ಓದಬಹುದಾದ ದಾಖಲೆ ಸೇರಿಸಿ",
    "RULE_NOT_EFFECTIVE": "ಈ ದಿನಾಂಕಕ್ಕೆ ನಿಯಮ ಅನ್ವಯಿಸುವುದಿಲ್ಲ",
    "age_proof": "ವಯಸ್ಸಿನ ಪುರಾವೆ",
    "income": "ಆದಾಯ ಪ್ರಮಾಣಪತ್ರ",
    "residence": "ವಾಸಸ್ಥಳದ ಪುರಾವೆ",
    "bank_account_details": "ಬ್ಯಾಂಕ್ ಖಾತೆ ವಿವರ",
    "provided": "ಒದಗಿಸಿದ ದಾಖಲೆ",
    "required": "ಇನ್ನೂ ಬೇಕಾದ ದಾಖಲೆ",
    "clarification": "ಸ್ಪಷ್ಟೀಕರಣ ಬೇಕು",
    "conflicting_or_outdated": "ವಿರುದ್ಧ ಅಥವಾ ಹಳೆಯ ದಾಖಲೆ",
    "application": "ಅಂತಿಮ ಅರ್ಜಿಯ ಹೆಚ್ಚುವರಿ ದಾಖಲೆ",
}


def translate(value, language):
    return KN.get(value, value) if language == "kn" else value.replace("_", " ").capitalize()
