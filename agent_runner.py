from ai_brain import generate_cold_message
from tracker import init_db, can_send_message, log_application

def run_agent_workflow(company_name, job_description, resume_text):
    """
    Yeh function tracker aur brain ko connect karta hai:
    1. Check karta hai ki cooldown ya duplicate issue toh nahi hai.
    2. Agar safe hai, toh AI message generate karta hai.
    3. Successfully message generate hone ke baad database me log kar deta hai.
    """
    print(f"\n🔍 Processing application for: {company_name}...")
    
    # 1. Database initialize karo
    init_db()
    
    # 2. Cooldown aur duplicate check karo
    allowed, reason = can_send_message(company_name)
    print(f"Status Check: {reason}")
    
    if not allowed:
        print(f"❌ Skipped! Message nahi bheja ja sakta.")
        return
    
    # 3. Agar allowed hai, toh Brain (Message Generator) se message banao
    print(f"🤖 Generating tailored AI/ML cold message...")
    message = generate_cold_message(resume_text, job_description, company_name)
    
    print("\n--- Final Cold Message ---")
    print(message)
    print("--------------------------")
    
    # This workflow generates a draft; it does not send an application.
    log_application(company_name, status="Drafted")
    print(f"✅ Draft logged for {company_name}; no message was sent.")

if __name__ == "__main__":
    # Test Data
    my_resume = "B.Tech in AI/ML student at ITM Universe Gwalior. Proficient in Python, C++, GenAI, Next.js, and building AI agents."
    
    target_company = "TechVanguard AI"
    sample_jd = "Looking for an AI/ML Intern who knows Python, machine learning models, and can build generative AI applications."
    
    # Agent workflow execute karo
    run_agent_workflow(target_company, sample_jd, my_resume)