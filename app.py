# app.py (Updated with multi-JD support and jobs listing)
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from jd_parser import read_job_description
from resume_extractor import extract_resume_text, extract_candidate_details
from match_score import calculate_match_score
from shortlist_agent import save_to_db
from email_generator import send_email  # Updated to use send_email
import os
from dotenv import load_dotenv  # Added for env vars
from bson.objectid import ObjectId

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv('FRONTEND_URL', 'http://localhost:5173')}})

# MongoDB Connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb+srv://itsmekishore28:itsmekishore28@cluster0.epss3og.mongodb.net/'))
db = client['recruitai']
jd_collection = db['jd']
candidates_collection = db['candidates']
print("connected to database")

@app.route('/upload-jd', methods=['POST'])
def upload_jd():
    if 'jd' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['jd']
    jd_data = read_job_description(file)
    # Insert as a new JD document
    insert_result = jd_collection.insert_one(jd_data)
    jd_data_with_id = {**jd_data, "_id": str(insert_result.inserted_id)}
    return jsonify({"message": "JD processed", "jd": jd_data_with_id}), 200

@app.route('/manual-jd', methods=['POST'])
def manual_jd():
    data = request.json
    jd_text = data.get('jd_text', '')
    job_title = data.get('job_title', 'Manual Entry')
    company_name = data.get('company_name', '')

    if not jd_text:
        return jsonify({"error": "No JD text provided"}), 400

    skill_bank = [
        'python', 'sql', 'tensorflow', 'pytorch', 'docker',
        'kubernetes', 'git', 'rest apis', 'django', 'flask',
        'nlp', 'machine learning', 'deep learning', 'linux',
        'cybersecurity', 'communication', 'agile'
    ]
    cert_bank = ['ceh', 'aws certified', 'pmp', 'cissp']

    extracted_skills = [skill for skill in skill_bank if skill in jd_text.lower()]
    extracted_certs = [cert for cert in cert_bank if cert in jd_text.lower()]

    jd_result = {
        "title": job_title,
        "company": company_name,
        "skills": extracted_skills,
        "experience": '',
        "certifications": extracted_certs
    }

    # Insert as a new JD document
    insert_result = jd_collection.insert_one(jd_result)
    return jsonify({"jd": {**jd_result, "_id": str(insert_result.inserted_id)}}), 200

@app.route('/jobs', methods=['GET'])
def list_jobs():
    jobs = list(jd_collection.find({}, {'title': 1, 'company': 1, 'skills': 1, 'certifications': 1}))
    for j in jobs:
        j['_id'] = str(j['_id'])
    return jsonify({'jobs': jobs}), 200

@app.route('/upload-resumes', methods=['POST'])
def upload_resumes():
    # Require a specific job selection
    job_id = request.args.get('job_id') or request.form.get('job_id')
    if not job_id:
        return jsonify({"error": "job_id is required. Select a job first."}), 400
    try:
        jd_data = jd_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        return jsonify({"error": "Invalid job_id"}), 400

    if not jd_data:
        return jsonify({"error": "Job not found"}), 404

    if 'resumes' not in request.files:
        return jsonify({"error": "No resumes provided"}), 400

    files = request.files.getlist('resumes')
    results = []

    for pdf in files:
        try:
            resume_text = extract_resume_text(pdf)
            candidate = extract_candidate_details(resume_text)
            score, skills, certs = calculate_match_score(jd_data, candidate)
            is_shortlisted = score >= 50.0
            save_to_db(candidate, score, is_shortlisted, job_id=job_id)
            email_status = send_email(candidate['name'], candidate['email'], jd_data['title']) if is_shortlisted else "Not shortlisted"

            results.append({
                "name": candidate['name'],
                "email": candidate['email'],
                "score": score,
                "shortlisted": is_shortlisted,
                "email_status": email_status if is_shortlisted else None
            })
        except Exception as e:
            print(f"Error processing {pdf.filename}: {str(e)}")
            results.append({
                "error": f"Error processing {pdf.filename}: {str(e)}"
            })

    return jsonify({"results": results}), 200

@app.route('/check-jd', methods=['GET'])
def check_jd():
    # Keep legacy behavior: return True if any JD exists
    jd_data = jd_collection.find_one({}, {'_id': 0})
    if jd_data:
        return jsonify({"ready": True, "jd": jd_data}), 200
    return jsonify({"ready": False}), 200

@app.route('/get-results', methods=['GET'])
def get_results():
    stored_candidates = list(candidates_collection.find({}, {'_id': 0}))
    return jsonify({"results": stored_candidates}), 200

# New endpoint to send emails to all shortlisted candidates
@app.route('/send-emails', methods=['POST'])
def send_emails():
    # Fallback: use the most recently added JD for the email title
    jd_data = jd_collection.find_one({}, sort=[('_id', -1)])
    if not jd_data:
        return jsonify({"error": "No JD available"}), 400

    shortlisted = list(candidates_collection.find({"shortlisted": "Yes"}, {'_id': 0}))
    if not shortlisted:
        return jsonify({"message": "No shortlisted candidates"}), 200

    sent_count = 0
    errors = []

    for candidate in shortlisted:
        try:
            print(f"📧 Sending email to: {candidate['email']}")
            status = send_email(candidate['name'], candidate['email'], jd_data['title'])
            print(f"Result for {candidate['email']}: {status}")

            if status == "Email sent successfully":
                sent_count += 1
                candidates_collection.update_one(
                    {"email": candidate['email']},
                    {"$set": {"email_sent": True}}
                )
            else:
                errors.append({"email": candidate['email'], "error": status})
        except Exception as e:
            print(f"❌ Exception while sending to {candidate['email']}: {str(e)}")
            errors.append({"email": candidate['email'], "error": str(e)})

    # ✅ Always return 200 to avoid frontend crash
    return jsonify({
        "message": f"Emails attempted for {len(shortlisted)} candidates. Sent: {sent_count}",
        "errors": errors
    }), 200

@app.route('/clear-results', methods=['DELETE'])
def clear_results():
    result = candidates_collection.delete_many({})
    return jsonify({"message": f"Deleted {result.deleted_count} candidates"}), 200

@app.route('/delete-job', methods=['DELETE'])
def delete_job():
    try:
        job_id = request.args.get('job_id') or request.json.get('job_id')
        if not job_id:
            return jsonify({"error": "job_id is required"}), 400
        
        print(f"Attempting to delete job with ID: {job_id}")
        result = jd_collection.delete_one({"_id": ObjectId(job_id)})
        print(f"Delete result: {result.deleted_count} documents deleted")
        if result.deleted_count > 0:
            return jsonify({"message": f"Job deleted successfully"}), 200
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        print(f"Error type: {type(e)}")
        return jsonify({"error": f"Invalid job ID: {str(e)}"}), 400

@app.route('/delete-all-jobs', methods=['DELETE'])
def delete_all_jobs():
    try:
        result = jd_collection.delete_many({})
        return jsonify({"message": f"Deleted {result.deleted_count} jobs"}), 200
    except Exception as e:
        print(f"Error deleting jobs: {str(e)}")
        return jsonify({"error": "Failed to delete jobs"}), 500

@app.route('/cleanup-invalid-jobs', methods=['DELETE'])
def cleanup_invalid_jobs():
    """Remove any jobs with invalid ObjectIds"""
    try:
        import re
        object_id_pattern = re.compile(r'^[0-9a-fA-F]{24}$')
        
        # Find all jobs
        all_jobs = list(jd_collection.find({}))
        deleted_count = 0
        
        for job in all_jobs:
            job_id_str = str(job['_id'])
            # If _id is not a valid 24-character hex string, delete it
            if not object_id_pattern.match(job_id_str):
                print(f"Deleting invalid job ID: {job_id_str}")
                jd_collection.delete_one({"_id": job["_id"]})
                deleted_count += 1
        
        return jsonify({
            "message": f"Deleted {deleted_count} invalid jobs",
            "deleted": deleted_count
        }), 200
    except Exception as e:
        print(f"Error cleaning up invalid jobs: {str(e)}")
        return jsonify({"error": f"Failed to cleanup jobs: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG') == 'True')
