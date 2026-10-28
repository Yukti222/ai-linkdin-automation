from ai_brain import generate_cold_message
from tracker import init_db, can_send_message
from playwright.sync_api import sync_playwright

def run_full_automation(company_name, job_description, resume_text, target_url):
    """
    Generate a message and open a target page for inspection; no message is sent or saved.
    """
    print(f"\n==========================================")
    print(f"🚀 Target Company: {company_name}")
    print(f"==========================================")
    
    # Step 1: Initialize Database
    init_db()
    
    # Step 2: Cooldown & Duplicate Check
    allowed, reason = can_send_message(company_name)
    print(f"🔍 Tracker Status: {reason}")
    
    if not allowed:
        print(f"❌ Process Stopped: Is company ko abhi message nahi bheja ja sakta.")
        return
    
    # Step 3: Generate Cold Message from Brain
    print(f"🤖 Generating tailored AI/ML cold message...")
    message = generate_cold_message(resume_text, job_description, company_name)
    
    print("\n--- Generated Message ---")
    print(message)
    print("-------------------------")
    
    # Step 4: Browser Automation via Playwright
    print(f"🌐 Browser open ho raha hai automation ke liye...")
    with sync_playwright() as p:
        # Browser khol rahe hain (headless=False taaki tumhe screen par dikhe)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Target job page ya portal par navigate karna
        print(f"🔗 Opening URL: {target_url}")
        page.goto(target_url)
        
        # Thoda wait karte hain page load hone ke liye
        page.wait_for_timeout(3000)
        
        # Yahan hum future me input box ka selector dekar message type karwayenge
        # Abhi ke liye hum test ke taur par browser khol rahe hain
        print(f"✍️ Simulated: Message clipboard par copy ho gaya hai / type ho raha hai...")
        
        # 5 seconds ka pause taaki tum dekh sako
        page.wait_for_timeout(5000)
        browser.close()
        print("🔒 Browser safely close ho gaya.")
        
    print("The message was not sent or saved as a draft.")

if __name__ == "__main__":
    # Test Data
    my_resume = "B.Tech in AI/ML student at ITM Universe Gwalior. Proficient in Python, C++, GenAI, Next.js, and building AI agents."
    
    # Test ke liye ek company aur sample URL (jaise Google ya Internshala)
    company = "TechVanguard AI"
    jd = "Looking for an AI/ML Intern who knows Python, machine learning models, and can build generative AI applications."
    url = "https://www.google.com" # Yahin par baad me hum Internshala/LinkedIn ka URL daalenge
    
    # Poora workflow run karo
    run_full_automation(company, jd, my_resume, url)