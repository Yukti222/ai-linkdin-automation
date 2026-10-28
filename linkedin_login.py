from playwright.sync_api import sync_playwright
import json

def save_linkedin_session():
    """
    Yeh function browser kholta hai taaki tum manually LinkedIn par login kar sako,
    aur phir session cookies ko 'linkedin_cookies.json' me save kar leta hai.
    """
    print("🌐 LinkedIn login session start ho raha hai...")
    
    with sync_playwright() as p:
        # Browser khol rahe hain (headless=False taaki tumhein login screen dikhe)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # LinkedIn login page par navigate karna
        page.goto("https://www.linkedin.com/login")
        
        print("\n⏳ ----------------------------------------------------")
        print("ACTION REQUIRED:")
        print("1. Jo browser window khuli hai, wahan apna LinkedIn login karo.")
        print("2. Jab tumhara LinkedIn Feed / Home page puri tarah open ho jaye,")
        print("   tab yahan terminal me aakar 'Enter' button daba dena!")
        print("------------------------------------------------------\n")
        
        # User ke manual login karne ka wait karna
        input("Press Enter here AFTER you have successfully logged in on the browser...")
        
        # Session cookies extract karke save karna
        cookies = context.cookies()
        with open("linkedin_cookies.json", "w") as f:
            json.dump(cookies, f)
            
        print("✅ Success! Cookies safely 'linkedin_cookies.json' me save ho gayi hain.")
        browser.close()

if __name__ == "__main__":
    save_linkedin_session()