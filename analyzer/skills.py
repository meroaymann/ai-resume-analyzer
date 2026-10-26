import json
import os
import re
import spacy
from spacy.matcher import PhraseMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE_DIR, "data", "skills.json"), encoding="utf-8") as f:
    SKILLS_DB = json.load(f)

nlp = spacy.blank("en")
matcher_lower = PhraseMatcher(nlp.vocab, attr="LOWER")
matcher_exact = PhraseMatcher(nlp.vocab, attr="ORTH")

SKILL_CATEGORY = {}
for category, skills in SKILLS_DB["categories"].items():
    for skill in skills:
        SKILL_CATEGORY[skill] = category
        matcher = matcher_exact if len(skill) <= 2 else matcher_lower
        matcher.add(skill, [nlp.make_doc(skill)])

for alias, skill in SKILLS_DB["aliases"].items():
    SKILL_CATEGORY.setdefault(skill, "Other")
    matcher = matcher_exact if len(alias) <= 3 else matcher_lower
    matcher.add(skill, [nlp.make_doc(alias)])

# Lookup to normalize names: "sklearn" -> "Scikit-learn", "python" -> "Python"
CANONICAL = {s.lower(): s for s in SKILL_CATEGORY}
CANONICAL.update({a.lower(): s for a, s in SKILLS_DB["aliases"].items()})


# ---------- Layer 1: dictionary ----------
def _dictionary_skills(text):
    doc = nlp.make_doc(text)
    matches = matcher_lower(doc) + matcher_exact(doc)
    return {nlp.vocab.strings[mid] for mid, _, _ in matches}


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


def implied_skills(skills):
    """Skills implied by others: AWS → Cloud, LLMs → Generative AI (used in job matching)."""
    lower_map = {k.lower(): v for k, v in IMPLIES.items()}
    implied = set()
    for s in skills:
        implied.update(i.lower() for i in lower_map.get(s.lower(), []))
    return implied    