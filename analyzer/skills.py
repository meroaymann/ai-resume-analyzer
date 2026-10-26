import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "data", "skills.json"), encoding="utf-8") as f:
    SKILLS_DB = json.load(f)


def _compile(term, case_sensitive):
    """Whole-word match: 'Java' won't match inside 'JavaScript', 'R' won't match 'R&D'."""
    body = r"\s+".join(re.escape(part) for part in term.split())
    pattern = r"(?<![\w+#&])" + body + r"(?![\w+#&])"
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


# Tool names that are also common English words ("I excel in...", "express interest", "swift delivery")
# → only match when written with a capital letter, like the real tool name
CASE_SENSITIVE_SKILLS = {"Excel", "Express", "Swift", "Spark", "Oracle", "Dart"}

SKILL_CATEGORY = {}
PATTERNS = []   # (compiled regex, canonical skill name)

for category, skills in SKILLS_DB["categories"].items():
    for skill in skills:
        SKILL_CATEGORY[skill] = category
        case_sensitive = len(skill) <= 2 or skill in CASE_SENSITIVE_SKILLS
        PATTERNS.append((_compile(skill, case_sensitive), skill))

for alias, skill in SKILLS_DB["aliases"].items():
    SKILL_CATEGORY.setdefault(skill, "Other")
    PATTERNS.append((_compile(alias, case_sensitive=len(alias) <= 3), skill))

# Lookup to normalize names: "sklearn" -> "Scikit-learn", "python" -> "Python"
CANONICAL = {s.lower(): s for s in SKILL_CATEGORY}
CANONICAL.update({a.lower(): s for a, s in SKILLS_DB["aliases"].items()})


# ---------- Layer 1: dictionary ----------
def _dictionary_skills(text):
    return {skill for pattern, skill in PATTERNS if pattern.search(text)}


# ---------- Layer 2: skills section parser ----------
PROFICIENCY_WORDS = {
    "native", "fluent", "beginner", "intermediate", "advanced", "basic", "proficient",
    "elementary", "professional", "conversational", "mother tongue", "good", "excellent",
}
SPOKEN_LANGUAGES = {
    "arabic", "english", "german", "french", "spanish", "italian", "chinese", "japanese",
    "korean", "turkish", "russian", "portuguese", "hindi", "dutch",
}
GENERIC_SKILL_WORDS = {
    "report", "preparation", "management", "skills", "tools", "work", "experience",
    "knowledge", "basic", "good", "other", "various", "general",
}


def _section_skills(section_text):
    found = {}
    for line in section_text.split("\n"):
        if ":" in line:
            label, line = line.split(":", 1)
            label = label.lower()
            # Skip "Languages: Arabic (Native)..." but keep "Programming Languages: ..."
            if "language" in label and "programming" not in label:
                continue
        line = re.sub(r"[()]", ",", line)

        for item in re.split(r"[,•|;·]|\s[-–]\s", line):
            item = item.strip(" .-–\t")
            key = item.lower()
            # Split "Git/GitHub" into two skills, but keep known ones like "CI/CD"
            parts = [item] if key in CANONICAL or "/" not in item else item.split("/")

            for part in parts:
                part = part.strip()
                p_key = part.lower()
                words = part.split()
                too_short = len(part) < 2 and p_key not in CANONICAL   # keeps "R"
                if (not (1 <= len(words) <= 4) or too_short or part.isdigit()
                        or p_key in PROFICIENCY_WORDS or p_key in SPOKEN_LANGUAGES):
                    continue
                canon = CANONICAL.get(p_key, part)
                found.setdefault(canon.lower(), canon)
    return set(found.values())


def _build_result(all_skills):
    by_category = {}
    for skill in all_skills:
        by_category.setdefault(SKILL_CATEGORY.get(skill, "Other"), []).append(skill)
    return {
        "all": all_skills,
        "by_category": by_category,
        "count": len(all_skills),
        "new_skills": [s for s in all_skills if s not in SKILL_CATEGORY],
    }


def _merge(*skill_lists):
    merged = {}
    for skills in skill_lists:
        for s in skills or []:
            if not isinstance(s, str):
                continue
            s = re.sub(r"\s*\(.*?\)\s*", " ", s).strip()   # "Arabic (Native)" → "Arabic"
            key = s.lower()
            too_short = len(s) < 2 and key not in CANONICAL   # keeps "R"
            if (not s or too_short or len(s) > 40 or len(s.split()) > 5
                    or key in SPOKEN_LANGUAGES or key in PROFICIENCY_WORDS
                    or key in GENERIC_SKILL_WORDS):
                continue
            canon = CANONICAL.get(key, s)
            if canon.islower():                      # "firewalls" → "Firewalls"
                canon = canon[0].upper() + canon[1:]
            merged.setdefault(canon.lower(), canon)   # key by normalized name → no duplicates
    return sorted(merged.values(), key=str.lower)


def extract_skills(text, skills_section=""):
    known = _dictionary_skills(text)
    from_section = _section_skills(skills_section) if skills_section else set()
    return _build_result(_merge(known, from_section))


def merge_skills(skills_result, extra_skills):
    """Layer 3: add AI-detected skills to the rule-based ones."""
    return _build_result(_merge(skills_result["all"], extra_skills))


IMPLIES = SKILLS_DB.get("implies", {})
IMPLIES_LOWER = {k.lower(): v for k, v in IMPLIES.items()}


def implied_skills(skills):
    """Skills implied by others: AWS → Cloud, LLMs → Generative AI (used in job matching)."""
    implied = set()
    for s in skills:
        implied.update(i.lower() for i in IMPLIES_LOWER.get(s.lower(), []))
    return implied