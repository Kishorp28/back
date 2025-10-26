import pandas as pd

def read_job_description(csv_path, row_index=0):
    if hasattr(csv_path, "seek"):  # Handle Streamlit file object
        csv_path.seek(0)

    df = pd.read_csv(csv_path, encoding='ISO-8859-1', engine='python')
    jd = df.iloc[row_index]

    job_title = jd.get('Job Title', 'N/A')
    jd_text = jd.get('Job Description', '').lower()

    # Define basic skill + cert banks
    skill_bank = [
        'python', 'sql', 'tensorflow', 'pytorch', 'docker',
        'kubernetes', 'git', 'rest apis', 'django', 'flask',
        'nlp', 'machine learning', 'deep learning', 'linux',
        'cybersecurity', 'communication', 'agile'
    ]
    cert_bank = ['ceh', 'aws certified', 'pmp', 'cissp']

    extracted_skills = [skill for skill in skill_bank if skill in jd_text]
    extracted_certs = [cert for cert in cert_bank if cert in jd_text]

    return {
        'title': job_title,
        'skills': extracted_skills,
        'experience': '',
        'certifications': extracted_certs
    }
