from playwright.sync_api import sync_playwright

def test_browser_automation():
    """
    Yeh function check karta hai ki Playwright ka browser 
    theek se khul raha hai ya nahi.
    """
    print("🚀 Browser start ho raha hai...")
    
    with sync_playwright() as p:
        # Chromium browser khol rahe hain (headless=False matlab browser screen par dikhega)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Test ke liye Google khol kar dekhte hain
        page.goto("https://www.google.com")
        print("🌐 Browser successfully khul gaya aur Google load ho gaya!")
        
        # 3 seconds ke liye ruka rahenge taaki tumhe dikhe
        page.wait_for_timeout(3000)
        
        browser.close()
        print("🔒 Browser safely close ho gaya.")

if __name__ == "__main__":
    test_browser_automation()