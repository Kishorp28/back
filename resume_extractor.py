import fitz
import re

def extract_resume_text(pdf_path):
    doc = fitz.open(stream=pdf_path.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()

def clean_keywords(raw_list):
    tokens = []
    for phrase in raw_list:
        words = re.findall(r'\b[a-zA-Z]+\b', phrase.lower())
        tokens.extend(words)
    return list(set(tokens))

def extract_candidate_details(text):
    lines = text.lower().split('\n')
    candidate = {
        'name': '',
        'email': '',
        'skills': [],
        'certifications': [],
        'tech_stack': []
    }

    for i, line in enumerate(lines):
        line = line.strip()

        if 'name:' in line and not candidate['name']:
            candidate['name'] = line.split('name:')[-1].strip()

        if 'email:' in line and not candidate['email']:
            candidate['email'] = line.split('email:')[-1].strip()

        if 'skills' in line:
            next_lines = lines[i:i+2]
            all_skills = ' '.join(next_lines)
            tokens = re.split(r'[,-]', all_skills)
            candidate['skills'] = [s.strip() for s in tokens if s.strip()]

        if 'certifications' in line:
            next_lines = lines[i:i+2]
            all_certs = ' '.join(next_lines)
            tokens = re.split(r'[,-]', all_certs)
            candidate['certifications'] = [s.strip() for s in tokens if s.strip()]

        if 'tech stack' in line:
            stack_line = line.split('tech stack')[-1].replace(':', '').strip()
            candidate['tech_stack'] = [s.strip() for s in stack_line.split(',') if s.strip()]

    candidate['skills'] = clean_keywords(candidate['skills'])
    candidate['certifications'] = clean_keywords(candidate['certifications'])
    candidate['tech_stack'] = clean_keywords(candidate['tech_stack'])

    return candidate
