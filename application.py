# app.py — RecruitAI Backend (CORS FIXED & PRODUCTION READY)

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from jd_parser import read_job_description
from resume_extractor import extract_resume_text, extract_candidate_details
from match_score import calculate_match_score
from shortlist_agent import save_to_db
from email_generator import send_email
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime
import os

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

app = Flask(__name__)

# --------------------------------------------------
# ✅ SINGLE, CLEAN CORS CONFIG (THIS IS THE KEY FIX)
# --------------------------------------------------
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://recurit.netlify.app",
                "http://localhost:5173"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    }
)

# --------------------------------------------------
# MongoDB Connection
# --------------------------------------------------
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["recruitai"]
jd_collection = db["jd"]
candidates_collection = db["candidates"]

# --------------------------------------------------
# Health / Home
# --------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "RecruitAI Backend is running",
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


# --------------------------------------------------
# JD Upload
# --------------------------------------------------
@app.route("/upload-jd", methods=["POST"])
def upload_jd():
    if "jd" not in request.files:
        return jsonify({"error": "No JD file provided"}), 400

    file = request.files["jd"]
    jd_data = read_job_description(file)
    result = jd_collection.insert_one(jd_data)

    return jsonify({
        "message": "JD uploaded",
        "jd": {**jd_data, "_id": str(result.inserted_id)}
    }), 200


@app.route("/manual-jd", methods=["POST"])
def manual_jd():
    data = request.json
    jd_text = data.get("jd_text", "")
    job_title = data.get("job_title", "Manual JD")
    company = data.get("company_name", "")

    if not jd_text:
        return jsonify({"error": "JD text required"}), 400

    skills = [
        s for s in [
            "python", "sql", "django", "flask",
            "machine learning", "docker", "git"
        ] if s in jd_text.lower()
    ]

    jd = {
        "title": job_title,
        "company": company,
        "skills": skills,
        "experience": "",
        "certifications": []
    }

    result = jd_collection.insert_one(jd)
    return jsonify({"jd": {**jd, "_id": str(result.inserted_id)}}), 200


# --------------------------------------------------
# Jobs
# --------------------------------------------------
@app.route("/jobs", methods=["GET"])
def list_jobs():
    jobs = list(jd_collection.find({}, {
        "title": 1,
        "company": 1,
        "skills": 1
    }))
    for j in jobs:
        j["_id"] = str(j["_id"])
    return jsonify({"jobs": jobs}), 200


# --------------------------------------------------
# Resume Upload
# --------------------------------------------------
@app.route("/upload-resumes", methods=["POST"])
def upload_resumes():
    job_id = request.args.get("job_id") or request.form.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400

    try:
        jd = jd_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        return jsonify({"error": "Invalid job_id"}), 400

    if not jd:
        return jsonify({"error": "Job not found"}), 404

    if "resumes" not in request.files:
        return jsonify({"error": "No resumes uploaded"}), 400

    results = []
    files = request.files.getlist("resumes")

    for pdf in files:
        resume_text = extract_resume_text(pdf)
        candidate = extract_candidate_details(resume_text)
        score, skills, certs = calculate_match_score(jd, candidate)
        shortlisted = score >= 50

        save_to_db(candidate, score, shortlisted, job_id)

        email_status = None
        if shortlisted:
            email_status = send_email(
                candidate["name"],
                candidate["email"],
                jd["title"]
            )

        results.append({
            "name": candidate["name"],
            "email": candidate["email"],
            "score": score,
            "shortlisted": shortlisted,
            "email_status": email_status
        })

    return jsonify({"results": results}), 200


# --------------------------------------------------
# Results
# --------------------------------------------------
@app.route("/get-results", methods=["GET"])
def get_results():
    data = list(candidates_collection.find({}, {"_id": 0}))
    return jsonify({"results": data}), 200


@app.route("/clear-results", methods=["DELETE"])
def clear_results():
    candidates_collection.delete_many({})
    return jsonify({"message": "Results cleared"}), 200


# --------------------------------------------------
# Delete Jobs
# --------------------------------------------------
@app.route("/delete-job", methods=["DELETE"])
def delete_job():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400

    jd_collection.delete_one({"_id": ObjectId(job_id)})
    return jsonify({"message": "Job deleted"}), 200


# --------------------------------------------------
# Run App
# --------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
