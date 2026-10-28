import re

def generate_cold_message(resume_text, job_description, company_name):
    """
    Bina kisi external API/Key ke ek smart, dynamic aur professional 
    cold message generate karne ka function.
    """
    
    # JD me se keywords detect karna (jaise Python, PyTorch, GenAI, etc.)
    skills_to_highlight = []
    common_skills = ["Python", "PyTorch", "GenAI", "Machine Learning", "Data Structures", "Next.js", "AI Agents", "C++"]
    
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', job_description, re.IGNORECASE):
            skills_to_highlight.append(skill)
            
    # Agar specific skills match na ho, toh default core skills le lo
    if not skills_to_highlight:
        skills_to_highlight = ["Python", "PyTorch", "GenAI"]
        
    skills_str = ", ".join(skills_to_highlight[:3]) # Top 3 skills

    # Professional cold message template
    message = (
        f"Hi Team {company_name},\n\n"
        f"I hope you're doing well. I came across the AI/ML opportunity at {company_name} and "
        f"wanted to reach out directly. As an AI/ML Engineer and B.Tech student specializing in "
        f"intelligent systems, I build practical solutions leveraging {skills_str}.\n\n"
        f"My background includes developing AI agents, participating in hackathons, and writing "
        f"efficient code in Python. I would love to bring my technical skills and problem-solving "
        f"mindset to your engineering team.\n\n"
        f"I have attached my resume for your review and would welcome a brief conversation.\n\n"
        f"Best regards,\n"
        f"Yukti Yadav\n"
        f"AI/ML Engineer"
    )
    
    return message

# --- Test karne ke liye code ---
if __name__ == "__main__":
    my_resume = "B.Tech in AI/ML student at ITM Universe Gwalior. Proficient in Python, C++, GenAI, Next.js, and building AI agents."
    sample_jd = "Looking for an AI/ML Intern who knows Python, machine learning models, and can build generative AI applications."
    target_company = "TechVanguard AI"

    print("🤖 Generating Smart Template-Based Cold Message...\n")
    message = generate_cold_message(my_resume, sample_jd, target_company)
    print("\n--- Generated Message ---")
    print(message)