import re

ACTION_VERBS = {
    "developed", "built", "designed", "implemented", "created", "led", "managed",
    "improved", "optimized", "analyzed", "automated", "deployed", "engineered",
    "launched", "integrated", "reduced", "increased", "achieved", "delivered",
    "collaborated", "researched", "trained", "evaluated", "architected", "streamlined",
    "conducted", "performed", "established", "coordinated", "presented", "maintained",
    "tested", "debugged", "migrated", "visualized", "generated", "identified",
    "organized", "planned", "prepared", "supervised", "taught", "mentored",
    "assisted", "supported", "handled", "served", "negotiated", "sold", "resolved",
    "administered", "facilitated", "oversaw", "drove", "spearheaded", "initiated",
    "produced", "wrote", "edited", "audited", "reconciled", "budgeted", "forecasted",
    "treated", "monitored", "consulted", "advised", "recruited", "scheduled",
}

# Numbers/percentages that are NOT years (e.g. 85%, 3x, 1,000+, 40 users)
IMPACT_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:%|x\b|\+|k\b)|\b(?!19\d{2}\b|20\d{2}\b)\d{2,}(?:,\d{3})*\b")


def score_resume(parsed, skills):
    text = parsed["text"]
    sections = parsed["sections"]
    contact = parsed["contact"]
    words = parsed["word_count"]
    breakdown, tips = [], []

    # 1) Sections — 25  (Experience OR Projects counts, so non-tech CVs aren't penalized)
    checks = {
        "Summary": (bool(sections.get("summary")), 6),
        "Education": (bool(sections.get("education")), 6),
        "Experience / Projects": (bool(sections.get("experience") or sections.get("projects")), 7),
        "Skills": (bool(sections.get("skills")), 6),
    }
    sec_score = sum(points for ok, points in checks.values() if ok)
    breakdown.append({"label": "Sections", "score": sec_score, "max": 25})
    for name, (ok, _) in checks.items():
        if not ok:
            tips.append(f"Add a clear '{name}' section — recruiters and ATS systems look for it.")

    # 2) Skills — 20
    skill_score = round(min(skills["count"], 20) / 20 * 20)
    breakdown.append({"label": "Skills", "score": skill_score, "max": 20})
    if skills["count"] < 10:
        tips.append("List more relevant skills for your field (tools, software, methods, certifications).")
    if "Soft Skills" not in skills["by_category"]:
        tips.append("Mention soft skills like Teamwork, Communication or Problem Solving through your experience.")

    # 3) Action verbs — 15
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    verbs_found = sorted(tokens & ACTION_VERBS)
    verb_score = round(min(len(verbs_found), 10) / 10 * 15)
    breakdown.append({"label": "Action Verbs", "score": verb_score, "max": 15})
    if len(verbs_found) < 6:
        tips.append("Start bullet points with strong action verbs (Developed, Built, Optimized, Led...).")

    # 4) Quantified impact — 15
    impact_text = sections.get("experience", "") + "\n" + sections.get("projects", "")
    impacts = IMPACT_PATTERN.findall(impact_text)
    impact_score = round(min(len(impacts), 5) / 5 * 15)
    breakdown.append({"label": "Quantified Impact", "score": impact_score, "max": 15})
    if len(impacts) < 3:
        tips.append("Add numbers to show impact (e.g. 'improved accuracy by 12%', 'processed 10K+ records').")

    # 5) Length — 15
    if 350 <= words <= 900:
        length_score = 15
    elif 200 <= words < 350 or 900 < words <= 1200:
        length_score = 9
        tips.append("Aim for 350–900 words — your resume is a bit " + ("short." if words < 350 else "long."))
    else:
        length_score = 4
        tips.append("Your resume length is far from ideal (350–900 words). Consider restructuring it.")
    breakdown.append({"label": "Length", "score": length_score, "max": 15})

    # 6) Contact info — 10  (GitHub is optional: non-tech CVs aren't penalized)
    has_profile = bool(contact.get("linkedin") or contact.get("github"))
    contact_score = (4 if contact.get("email") else 0) + \
                    (3 if contact.get("phone") else 0) + \
                    (3 if has_profile else 0)
    breakdown.append({"label": "Contact Info", "score": contact_score, "max": 10})
    if not contact.get("email"):
        tips.append("Add a professional email address to the header.")
    if not contact.get("phone"):
        tips.append("Add a phone number to the header.")
    if not has_profile:
        tips.append("Add a LinkedIn profile (or GitHub/portfolio link if relevant to your field).")

    total = sum(item["score"] for item in breakdown)
    if total >= 85:
        grade = "Excellent"
    elif total >= 70:
        grade = "Good"
    elif total >= 50:
        grade = "Fair"
    else:
        grade = "Needs Work"

    return {
        "score": total,
        "grade": grade,
        "breakdown": breakdown,
        "action_verbs": verbs_found,
        "impact_count": len(impacts),
        "tips": tips,
    }