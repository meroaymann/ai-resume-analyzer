import os
import uuid
import tempfile
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from analyzer.parser import parse_resume
from analyzer.skills import extract_skills, merge_skills
from analyzer.scorer import score_resume
from analyzer.matcher import match_job
from analyzer.ai_feedback import get_ai_feedback
from analyzer.ats import ats_check


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4MB (Vercel's request limit is 4.5MB)
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "resumeiq_uploads")   # /tmp on Vercel
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("resume")
    job_description = request.form.get("job_description", "").strip()

    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF or DOCX files are allowed"}), 400

    # Unique name so two uploads never overwrite each other
    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    try:
        parsed = parse_resume(path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        # Corrupted or fake files (e.g. a renamed .txt) → clear message instead of a crash
        return jsonify({"error": "Couldn't read this file. Make sure it's a valid PDF or DOCX."}), 400
    finally:
        # Privacy: delete the CV right after reading it
        if os.path.exists(path):
            os.remove(path)

    # Layers 1 + 2 (rule-based)
    skills = extract_skills(parsed["text"], parsed["sections"].get("skills", ""))
    rule_score = score_resume(parsed, skills)

    # Layer 3 (AI) — optional, app still works if it fails
    ai = get_ai_feedback(parsed["text"], job_description, rule_score, parsed["contact"])
    if ai:
        skills = merge_skills(skills, ai["skills"])
    score = score_resume(parsed, skills)
    # Never suggest "learning" a skill the candidate already has
    if ai:
        have = {s.lower() for s in skills["all"]}
        for role in ai["suggested_roles"]:
            role["skills_to_learn"] = [s for s in role["skills_to_learn"] if s.lower() not in have]
    match = None
    if job_description:
        match = match_job(
            parsed["text"], skills["all"], job_description,
            extra_jd_skills=ai["jd_skills"] if ai else None,
            ai_matched=ai["matched_jd_skills"] if ai else None,
            ai_keywords=ai["jd_keywords"] if ai else None,
        )

    ats = ats_check(parsed, match)

    return jsonify({
        "contact": parsed["contact"],
        "word_count": parsed["word_count"],
        "sections_found": list(parsed["sections"].keys()),
        "skills": skills,
        "score": score,
        "match": match,
        "ai_used": ai is not None,
        "ai": ai,
        "ats": ats,
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File is too large (max 4MB)"}), 413

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Something went wrong on our side. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")