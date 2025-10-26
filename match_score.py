import re

def clean_and_tokenize(keywords):
    tokens = set()
    for item in keywords:
        words = re.findall(r'\b[a-zA-Z]+\b', item.lower())
        tokens.update(words)
    return tokens

def calculate_match_score(jd_data, candidate_data):
    # Normalize JD tokens
    jd_skills_raw = jd_data.get('skills', [])
    jd_certs_raw = jd_data.get('certifications', [])
    jd_skills = clean_and_tokenize(jd_skills_raw)
    jd_certs = clean_and_tokenize(jd_certs_raw)

    # Normalize candidate tokens
    cand_skills_raw = candidate_data.get('skills', [])
    cand_stack_raw = candidate_data.get('tech_stack', [])
    cand_certs_raw = candidate_data.get('certifications', [])

    cand_skills = clean_and_tokenize(cand_skills_raw)
    cand_stack = clean_and_tokenize(cand_stack_raw)
    cand_certs = clean_and_tokenize(cand_certs_raw)

    candidate_tokens = cand_skills.union(cand_stack)

    matched_skills = jd_skills.intersection(candidate_tokens)
    matched_certs = jd_certs.intersection(cand_certs)

    total_possible = len(jd_skills) + len(jd_certs)
    total_matched = len(matched_skills) + len(matched_certs)

    score = (total_matched / total_possible) * 100 if total_possible > 0 else 0

    return round(score, 2), matched_skills, matched_certs