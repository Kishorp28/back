# app.py - RecruitAI Backend with PROPER CORS
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from pymongo import MongoClient
from jd_parser import read_job_description
from resume_extractor import extract_resume_text, extract_candidate_details
from match_score import calculate_match_score
from shortlist_agent import save_to_db
from email_generator import send_email
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# PROPER CORS Configuration
CORS(app, resources={
    r"/*": {
        "origins": ["https://recurit.netlify.app", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})

# Add manual CORS headers for all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://main.d1sj18xuk9hyn7.amplifyapp.com')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Handle preflight requests
@app.route('/', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path=None):
    return jsonify({}), 200

# MongoDB Connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb+srv://itsmekishore28:itsmekishore28@cluster0.epss3og.mongodb.net/'))
db = client['recruitai']
jd_collection = db['jd']
candidates_collection = db['candidates']

@app.route('/')
def home():
    return jsonify({
        "message": "RecruitAI Backend is running!",
        "status": "active",
        "cors": "enabled",
        "frontend": "https://main.d1sj18xuk9hyn7.amplifyapp.com",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0"
    }), 200

@app.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    try:
        db_status = "connected" if client.admin.command('ping') else "disconnected"
        return jsonify({
            "status": "healthy",
            "service": "recruitai-backend",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/upload-jd', methods=['POST', 'OPTIONS'])
@cross_origin()
def upload_jd():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        if 'jd' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['jd']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        jd_data = read_job_description(file)
        insert_result = jd_collection.insert_one(jd_data)
        jd_data_with_id = {**jd_data, "_id": str(insert_result.inserted_id)}
        
        return jsonify({
            "message": "JD processed successfully", 
            "jd": jd_data_with_id
        }), 200
        
    except Exception as e:
        print(f"❌ Error in /upload-jd: {str(e)}")
        return jsonify({"error": f"Failed to process JD: {str(e)}"}), 500

@app.route('/manual-jd', methods=['POST', 'OPTIONS'])
@cross_origin()
def manual_jd():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
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

        insert_result = jd_collection.insert_one(jd_result)
        return jsonify({
            "message": "Manual JD created successfully",
            "jd": {**jd_result, "_id": str(insert_result.inserted_id)}
        }), 200
        
    except Exception as e:
        print(f"❌ Error in /manual-jd: {str(e)}")
        return jsonify({"error": f"Failed to create manual JD: {str(e)}"}), 500

@app.route('/jobs', methods=['GET', 'OPTIONS'])
@cross_origin()
def list_jobs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        jobs = list(jd_collection.find({}, {'title': 1, 'company': 1, 'skills': 1, 'certifications': 1}))
        for j in jobs:
            j['_id'] = str(j['_id'])
        return jsonify({
            "message": "Jobs retrieved successfully",
            "jobs": jobs,
            "count": len(jobs)
        }), 200
    except Exception as e:
        print(f"❌ Error in /jobs: {str(e)}")
        return jsonify({"error": f"Failed to retrieve jobs: {str(e)}"}), 500

@app.route('/upload-resumes', methods=['POST', 'OPTIONS'])
@cross_origin()
def upload_resumes():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
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
        if not files or all(file.filename == '' for file in files):
            return jsonify({"error": "No files selected"}), 400

        results = []
        processed_count = 0

        for pdf in files:
            try:
                if pdf.filename == '':
                    continue
                    
                resume_text = extract_resume_text(pdf)
                candidate = extract_candidate_details(resume_text)
                score, skills, certs = calculate_match_score(jd_data, candidate)
                is_shortlisted = score >= 50.0
                save_to_db(candidate, score, is_shortlisted, job_id=job_id)
                
                email_status = None
                if is_shortlisted:
                    try:
                        email_status = send_email(candidate['name'], candidate['email'], jd_data['title'])
                    except Exception as email_error:
                        email_status = f"Email failed: {str(email_error)}"

                results.append({
                    "name": candidate['name'],
                    "email": candidate['email'],
                    "score": score,
                    "shortlisted": is_shortlisted,
                    "email_status": email_status if is_shortlisted else "Not shortlisted",
                    "skills_matched": skills,
                    "certifications_matched": certs
                })
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Error processing {pdf.filename}: {str(e)}")
                results.append({
                    "filename": pdf.filename,
                    "error": f"Error processing resume: {str(e)}"
                })

        return jsonify({
            "message": f"Processed {processed_count} resumes",
            "results": results,
            "job_title": jd_data.get('title', 'Unknown')
        }), 200
        
    except Exception as e:
        print(f"❌ Error in /upload-resumes: {str(e)}")
        return jsonify({"error": f"Failed to process resumes: {str(e)}"}), 500

@app.route('/check-jd', methods=['GET', 'OPTIONS'])
@cross_origin()
def check_jd():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        jd_data = jd_collection.find_one({}, {'_id': 0})
        if jd_data:
            return jsonify({
                "ready": True, 
                "jd": jd_data,
                "message": "JD found"
            }), 200
        return jsonify({
            "ready": False,
            "message": "No JD found"
        }), 200
    except Exception as e:
        print(f"❌ Error in /check-jd: {str(e)}")
        return jsonify({"error": f"Failed to check JD: {str(e)}"}), 500

@app.route('/get-results', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_results():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        stored_candidates = list(candidates_collection.find({}, {'_id': 0}))
        return jsonify({
            "message": "Results retrieved successfully",
            "results": stored_candidates,
            "count": len(stored_candidates)
        }), 200
    except Exception as e:
        print(f"❌ Error in /get-results: {str(e)}")
        return jsonify({"error": f"Failed to retrieve results: {str(e)}"}), 500

@app.route('/send-emails', methods=['POST', 'OPTIONS'])
@cross_origin()
def send_emails():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
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

        return jsonify({
            "message": f"Emails attempted for {len(shortlisted)} candidates. Sent: {sent_count}",
            "sent_count": sent_count,
            "total_shortlisted": len(shortlisted),
            "errors": errors
        }), 200
        
    except Exception as e:
        print(f"❌ Error in /send-emails: {str(e)}")
        return jsonify({"error": f"Failed to send emails: {str(e)}"}), 500

@app.route('/clear-results', methods=['DELETE', 'OPTIONS'])
@cross_origin()
def clear_results():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        result = candidates_collection.delete_many({})
        return jsonify({
            "message": f"Deleted {result.deleted_count} candidates",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        print(f"❌ Error in /clear-results: {str(e)}")
        return jsonify({"error": f"Failed to clear results: {str(e)}"}), 500

@app.route('/delete-job', methods=['DELETE', 'OPTIONS'])
@cross_origin()
def delete_job():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        job_id = request.args.get('job_id') or request.json.get('job_id')
        if not job_id:
            return jsonify({"error": "job_id is required"}), 400
        
        print(f"Attempting to delete job with ID: {job_id}")
        result = jd_collection.delete_one({"_id": ObjectId(job_id)})
        print(f"Delete result: {result.deleted_count} documents deleted")
        
        if result.deleted_count > 0:
            return jsonify({"message": "Job deleted successfully"}), 200
        else:
            return jsonify({"error": "Job not found"}), 404
            
    except Exception as e:
        print(f"Error deleting job: {str(e)}")
        return jsonify({"error": f"Invalid job ID: {str(e)}"}), 400

@app.route('/delete-all-jobs', methods=['DELETE', 'OPTIONS'])
@cross_origin()
def delete_all_jobs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        result = jd_collection.delete_many({})
        return jsonify({
            "message": f"Deleted {result.deleted_count} jobs",
            "deleted_count": result.deleted_count
        }), 200
    except Exception as e:
        print(f"Error deleting jobs: {str(e)}")
        return jsonify({"error": "Failed to delete jobs"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting RecruitAI Backend on port {port}")
    print(f"🌐 CORS enabled for: https://main.d1sj18xuk9hyn7.amplifyapp.com")
    print(f"🔧 Debug mode: {debug_mode}")
    print(f"📊 MongoDB: {client.admin.command('ping') and 'Connected' or 'Failed'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
