# jd_parser.py - Fixed version for PDF/DOCX files
import PyPDF2
import docx
import re

def read_job_description(file):
    """Extract text from JD file (PDF, DOCX, or text)"""
    try:
        print(f"📄 Processing JD file: {file.filename}")
        
        # Reset file stream
        file.stream.seek(0)
        text = ""
        
        if file.filename.lower().endswith('.pdf'):
            print("🔍 Detected PDF file")
            pdf_reader = PyPDF2.PdfReader(file.stream)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        elif file.filename.lower().endswith(('.docx', '.doc')):
            print("🔍 Detected Word document")
            doc = docx.Document(file.stream)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
                    
        else:
            # Try to read as text
            try:
                file.stream.seek(0)
                text = file.stream.read().decode('utf-8', errors='ignore')
            except:
                raise ValueError(f"Unsupported file format: {file.filename}")
        
        if not text.strip():
            raise ValueError("No text content found in file")
            
        return parse_jd_text(text)
        
    except Exception as e:
        print(f"❌ Error reading JD: {str(e)}")
        return {
            "title": "Error Processing JD",
            "company": "Unknown",
            "skills": [],
            "experience": "Error",
            "certifications": [],
            "error": str(e)
        }

def parse_jd_text(text):
    """Parse JD text to extract skills, experience, etc."""
    text_lower = text.lower()
    
    # Comprehensive skill bank
    skill_bank = [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
        'html', 'css', 'react', 'angular', 'vue', 'node.js',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'tensorflow', 'pytorch', 'machine learning', 'deep learning',
        'linux', 'git', 'rest api', 'graphql', 'nlp',
        'cybersecurity', 'communication', 'agile', 'scrum'
    ]
    
    certifications = [
        'aws certified', 'pmp', 'cissp', 'ceh', 'azure certified'
    ]
    
    # Extract skills
    found_skills = []
    for skill in skill_bank:
        if skill in text_lower:
            found_skills.append(skill)
    
    # Extract certifications
    found_certs = []
    for cert in certifications:
        if cert in text_lower:
            found_certs.append(cert)
    
    # Extract job title
    title = "Extracted Position"
    title_patterns = [
        r'job title:\s*(.+)',
        r'position:\s*(.+)',
        r'role:\s*(.+)',
        r'title:\s*(.+)'
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            break
    
    # Extract company
    company = "Unknown Company"
    company_patterns = [
        r'company:\s*(.+)',
        r'at\s+([A-Za-z0-9\s&]+)',
        r'organization:\s*(.+)'
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            break
    
    # Extract experience
    experience = "Not specified"
    exp_patterns = [
        r'(\d+\+?\s*years?)',
        r'experience:\s*(.+)',
        r'(\d+-\d+\s*years?)'
    ]
    
    for pattern in exp_patterns:
        match = re.search(pattern, text_lower)
        if match:
            experience = match.group(0)
            break
    
    return {
        "title": title,
        "company": company,
        "skills": found_skills,
        "experience": experience,
        "certifications": found_certs,
        "text_length": len(text)
    }
