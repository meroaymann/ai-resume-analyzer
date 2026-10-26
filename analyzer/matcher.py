import re
from collections import Counter
from analyzer.skills import extract_skills, _merge, implied_skills, _compile, CASE_SENSITIVE_SKILLS
from analyzer.textutils import STOP_WORDS as BASE_STOP_WORDS, tokenize, tfidf_cosine

# Common JD words that aren't real requirements
GENERIC_WORDS = {
    "experience", "work", "working", "team", "role", "company", "join", "opportunity",
    "ability", "strong", "including", "years", "skills", "knowledge", "using", "looking",
    "environment", "culture", "business", "help", "new", "well", "within", "across",
    "equal", "regardless", "diversity", "diverse", "inclusive", "employer", "proud",
    "requirements", "responsibilities", "preferred", "plus", "candidate", "position",
    "job", "apply", "make", "good", "great", "excellent", "related", "field", "etc",
    "opportunities", "solutions", "markets", "market", "concepts", "proof", "value",
    "growth", "ideas", "partner", "partners", "people", "products", "success", "future",
    "passionate", "curious", "world", "best", "support", "ensure", "shape", "magic",
    "humble", "belong", "belongs", "contributes", "collective", "thrive", "thrives",
}
STOP_WORDS = BASE_STOP_WORDS | GENERIC_WORDS


def text_similarity(resume_text, jd_text):
    return tfidf_cosine(resume_text, jd_text)


def _is_proper_noun(term, jd_text):
    # Words that never appear in lowercase in the JD are usually names (Coca, Cola, Cairo)
    occurrences = re.findall(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", jd_text, re.I)
    return bool(occurrences) and all(o[0].isupper() for o in occurrences)


def _in_resume(term, resume_lower):
    # Handle simple plurals: "stakeholders" matches "stakeholder", "opportunities" → "opportunity"
    forms = {term, term[:-1] if term.endswith("s") else term}   # remove ONE plural "s" only
    if term.endswith("ies"):
        forms.add(term[:-3] + "y")
    return any(re.search(r"(?<![a-z])" + re.escape(f), resume_lower) for f in forms if len(f) > 2)


def missing_keywords(resume_text, jd_text, top_n=15):
    counts = Counter(tokenize(jd_text, stop_words=STOP_WORDS, min_len=3))
    ranked = counts.most_common()

    resume_lower = resume_text.lower()
    missing = []
    for term, count in ranked:
        if count < 2:          # appears only once in the JD → not important
            break
        if _is_proper_noun(term, jd_text) or _in_resume(term, resume_lower):
            continue
        missing.append(term)
        if len(missing) >= top_n:
            break
    return missing


def _resume_has(skill, resume_set, resume_text):
    if skill.lower() in resume_set:
        return True
    # Same whole-word rules as skills.py ("R" ≠ "R&D", "Excel" ≠ "I excel in...")
    case_sensitive = len(skill) <= 2 or skill in CASE_SENSITIVE_SKILLS
    return _compile(skill, case_sensitive).search(resume_text) is not None


def match_job(resume_text, resume_skills, jd_text, extra_jd_skills=None, ai_matched=None, ai_keywords=None):
    jd_skills = _merge(extract_skills(jd_text)["all"], extra_jd_skills)
    resume_set = {s.lower() for s in resume_skills} | implied_skills(resume_skills)
    # Normalize AI names the same way ("ML" → "Machine Learning") so they compare correctly
    ai_matched_set = {s.lower() for s in _merge(ai_matched)}

    # Matched = found in resume text/skills OR confirmed by the AI (understands synonyms)
    matched = [s for s in jd_skills
               if _resume_has(s, resume_set, resume_text) or s.lower() in ai_matched_set]
    missing = [s for s in jd_skills if s not in matched]

    similarity = text_similarity(resume_text, jd_text)
    similarity_score = min(similarity / 0.4, 1) * 100  # 0.4+ cosine = strong match

    if jd_skills:
        coverage = len(matched) / len(jd_skills) * 100
        match_score = 0.7 * coverage + 0.3 * similarity_score
    else:
        coverage = None
        match_score = similarity_score

    
    # Missing keywords: AI keywords first (much cleaner), TF-IDF as fallback
    if ai_keywords:
        jd_skill_set = {s.lower() for s in jd_skills}
        resume_lower = resume_text.lower()
        keywords = [k for k in ai_keywords
                    if k.lower() not in jd_skill_set               # already shown in missing_skills
                    and not _in_resume(k.lower(), resume_lower)]
    else:
        keywords = missing_keywords(resume_text, jd_text)

    return {
        "match_score": round(match_score),
        "skill_coverage": round(coverage) if coverage is not None else None,
        "text_similarity": round(similarity, 3),
        "jd_skills": jd_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "missing_keywords": keywords,
    }