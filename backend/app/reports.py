import html
import pymupdf as fitz
from .translations import translate


def report_pdf(profile_name, evaluation, language="en"):
    """MuPDF Story uses HarfBuzz shaping and bundled fallback fonts for Kannada."""
    esc = html.escape
    kn = language == "kn"
    heading = "ಪ್ರಾಥಮಿಕ ಮೌಲ್ಯಮಾಪನ" if kn else "Preliminary assessment"
    disclaimer = (
        "ಕಾಲ್ಪನಿಕ ಪರೀಕ್ಷಾ ಮಾಹಿತಿ. ಸರ್ಕಾರಿ ನಿರ್ಧಾರವಲ್ಲ."
        if kn
        else "Fictional test data. This is not a government decision or benefit approval."
    )
    parts = [
        f"<h1>FormFlow AI</h1><h2>{heading}</h2><p>{disclaimer}</p><p>{esc(profile_name)} | {evaluation.created_at.date()}</p>"
    ]
    for index, result in enumerate(evaluation.results):
        if index:
            parts.append('<div style="page-break-before: always;"></div>')
        parts.append(
            f"<h2>{esc(result.get('name_kn' if kn else 'name', result['scheme_id']))}</h2><p>{esc(translate(result['verdict'], language))} | {'ನಿಯಮ ಆವೃತ್ತಿ' if kn else 'Rule version'} {result['version']}</p>"
        )
        for c in result["conditions"]:
            parts.append(
                f"<h3>{esc(c['description_kn'] if kn else c['description'])}</h3><p>{esc(translate(c['status'], language))} / {esc(translate(c['reason'], language))}</p><p>{esc(c['clause_id'])}: {esc(c['clause_text'])}</p>"
            )
        parts.append("<h3>ದಾಖಲೆಗಳ ಪಟ್ಟಿ / Document checklist</h3><ul>")
        for item in result["checklist"]:
            parts.append(
                f"<li>{esc(translate(item['document_type'], language))} - {esc(translate(item['group'], language))}</li>"
            )
        parts.append("</ul>")
        parts.append(
            "<p>ಅರ್ಜಿಯ ಹೆಚ್ಚುವರಿ ದಾಖಲೆಗಳು ಅರ್ಹತೆಯ ಸಾಕ್ಷ್ಯದಿಂದ ಪ್ರತ್ಯೇಕ. ಕಾಲ್ಪನಿಕ ಯೋಜನೆಗಳಿಗೆ ನಿಜವಾದ ಅರ್ಜಿ ಮಾರ್ಗವಿಲ್ಲ.</p>"
            if kn
            else "<p>Final application documents are separate from eligibility evidence. Fictional schemes have no actual application channel.</p>"
        )
    story = fitz.Story(
        html="".join(parts),
        user_css="body {font-family: sans-serif; font-size: 11pt; color: #183c32;} h1 {font-size: 26pt;} h2 {font-size: 16pt;} h3 {font-size: 12pt;} p {line-height: 1.5;}",
    )
    import io

    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    rect = fitz.paper_rect("a4")
    more = True
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect + (45, 45, -45, -45))
        story.draw(dev)
        writer.end_page()
    writer.close()
    document = fitz.open(stream=buffer.getvalue(), filetype="pdf")
    for index, page in enumerate(document):
        page.insert_text(
            (45, page.rect.height - 24),
            f"FormFlow AI | FICTIONAL TEST DATA | {index + 1} / {len(document)}",
            fontsize=8,
            color=(0.3, 0.4, 0.3),
        )
    result = document.tobytes()
    document.close()
    return result
