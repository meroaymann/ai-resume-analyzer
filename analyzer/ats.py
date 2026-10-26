import re

MONTHS = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
          r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
YEAR = r"(?:19|20)\d{2}"
END = rf"(?:{YEAR}|present|current|now|today|ongoing|date)"

DATE_PATTERN = re.compile(
    rf"\b{MONTHS},?\s+(?:\d{{1,2}},?\s+)?{YEAR}\b"                          # Feb 2026 / February 5, 2026
    rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}\s+{YEAR}\b"                  # 5 Feb 2026 / 5th February 2026
    rf"|\b(?:spring|summer|fall|autumn|winter)\s+{YEAR}\b"                  # Summer 2024
    rf"|\bQ[1-4]\s*{YEAR}\b"                                                # Q3 2024
    rf"|\b\d{{1,2}}[/.\-]\d{{1,2}}[/.\-](?:{YEAR}|\d{{2}})\b"               # 01/09/2019, 1.9.19
    rf"|\b\d{{1,2}}[/.\-]{YEAR}\b"                                          # 02/2026, 02-2026, 02.2026
    rf"|\b{YEAR}[/.\-](?:0?[1-9]|1[0-2])(?:[/.\-]\d{{1,2}})?\b"             # 2026-02, 2026-02-15
    rf"|\b{YEAR}\s*(?:[-–—/]|to|until|till)\s*{END}\b"                      # 2019 – 2021, 2019 to Present, 2019/2020
    rf"|\b(?:since|from|in|until|till)\s+{YEAR}\b"                          # since 2020, from 2019
    rf"|\b{YEAR}\s*$",                                                      # year alone at the end of a line (right-aligned dates)
    re.I | re.M,
)


def ats_check(parsed, match=None):
    text = parsed["text"]
    sections = parsed["sections"]
    layout = parsed.get("layout", {})
    checks = []

    def add(label, passed, weight, ok_msg, fail_msg):
        checks.append({
            "label": label,
            "passed": bool(passed),
            "weight": weight,
            "message": ok_msg if passed else fail_msg,
        })

    standard = [s for s in ("summary", "education", "experience", "skills") if sections.get(s)]
    add("Standard section headings", len(standard) >= 3, 20,
        "Uses standard headings that ATS systems recognize.",
        "Use standard headings like 'Experience', 'Education' and 'Skills' so ATS can find your content.")

    email_in_text = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    add("Contact info readable", email_in_text and parsed["contact"].get("phone"), 15,
        "Email and phone are readable as plain text.",
        "Write your email and phone as plain text (not only icons or links) so ATS can read them.")

    icons = parsed.get("icon_artifacts", 0)
    add("Clean text extraction", icons < 3, 15,
        "Text extracts cleanly — no unreadable symbols.",
        f"Found {icons} unreadable symbols from icon fonts. Replace icons with plain labels like 'Email:' or 'Phone:'.")

    add("Simple layout (no tables)", layout.get("tables", 0) == 0, 10,
        "No tables detected — easy for ATS to read in order.",
        "Tables or boxed columns detected. Some ATS read them out of order — prefer a single-column layout.")

    add("No images or graphics", layout.get("images", 0) == 0, 10,
        "No images — all content is plain text.",
        "Images or graphics detected. ATS can't read text inside images — keep key info as text.")

    bullets = len(re.findall(r"^\s*[•\-–▪●◦*➢►✓✔◆○➤■□]\s+", text, re.M))
    add("Bullet points", bullets >= 3, 10,
        "Uses bullet points — easy to scan and parse.",
        "Use bullet points for your experience and projects instead of long paragraphs.")

    dates = DATE_PATTERN.findall(text)
    add("Readable dates", len(dates) >= 2, 10,
        f"Found {len(dates)} clear dates — easy for ATS to build your timeline.",
        f"Found only {len(dates)} date(s). Add dates to each role and education entry, like 'Feb 2025 – Jul 2025'.")

    add("ATS-friendly file type", parsed.get("file_type") in ("pdf", "docx"), 5,
        "PDF and DOCX are ATS-friendly formats.",
        "Use a PDF or DOCX file.")

    if match and match.get("skill_coverage") is not None:
        coverage = match["skill_coverage"]
        add("Job keyword coverage", coverage >= 60, 15,
            f"Covers {coverage}% of the job's required skills.",
            f"Covers only {coverage}% of the job's required skills — add the relevant ones you really have.")

    total = sum(c["weight"] for c in checks)
    earned = sum(c["weight"] for c in checks if c["passed"])
    return {"score": round(earned / total * 100), "checks": checks}