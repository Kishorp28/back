# shortlist_agent.py (Updated to include email_sent field default)
from pymongo import MongoClient

def save_to_db(candidate_data, match_score, is_shortlisted, job_id=None):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['recruitai']
    candidates = db['candidates']
    candidates.insert_one({
        'name': candidate_data['name'],
        'email': candidate_data['email'],
        'score': match_score,
        'shortlisted': 'Yes' if is_shortlisted else 'No',
        'email_sent': False,  # New field
        'job_id': job_id
    })