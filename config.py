# ============================================================
# config.py  -  Yahan sirf settings hain. Code samajhna zaroori nahi.
# Jo cheez badalni ho, sirf "=" ke baad wali value badlo.
# ============================================================

COOKIES_FILE = "linkedin_cookies.json"
RESUME_FILE = r"E:\resume 3rd sem main.pdf"

# --- Search settings (find_leads.py use karega) ---
SEARCH_QUERY = "recruiter"
SEARCH_PAGES = 3          # kitne search pages dekhne hain (1 page = ~10 log)
SEARCH_NETWORK = "F"       # LinkedIn first-degree connections only

# --- Limits ---
DAILY_LIMIT = 20         # ek din mein total max msgs (naye + follow-up)
SLOT_LIMIT = 5           # ek baar script chalne par max msgs
DELAY_MIN = 90            # do msgs ke beech kam se kam kitne second
DELAY_MAX = 240           # do msgs ke beech zyada se zyada kitne second
FOLLOWUP_AFTER_DAYS = 10  # kitne din baad follow-up

# --- Recruiter pehchanne ke keywords (headline mein dhundhe jaayenge) ---
GOOD_WORDS = ["recruiter", "talent acquisition", "hiring", "hr ", "human resources",
              "talent partner", "staffing", "recruitment", "talent"]
BAD_WORDS = ["student", "intern ", "looking for", "open to work", "seeking"]

# --- Tumhara intro ---
MY_NAME = "Yukti Yadav"          # <-- yahan apna naam likho
MY_INTRO = "B.Tech AI/ML student at ITM Universe Gwalior (Python, C++, PyTorch, GenAI)"


def build_message(first_name, headline=""):
    """Build Yukti's outreach message for a recruiter."""
    return (
        f"Hi {first_name},\n\n"
        "I am Yukti Yadav, a B.Tech AI/ML student (3rd semester) currently looking "
        "for a software or AI internship.\n\n"
        "I have built production-ready projects like MediRush (an emergency medical "
        "assistant using Firebase) and a Multilingual Government Schemes Voice "
        "Assistant using Llama 3.2 under 30 KB. I have also secured 3rd place in the "
        "Prompt Pioneers Hackathon.\n\n"
        "I have attached my resume here. Would love to explore any relevant "
        "opportunities at your company.\n\n"
        "Best regards,\n"
        "Yukti Yadav"
    )


def build_followup(first_name):
    """10 din baad ka follow-up msg."""
    return (
        f"Hi {first_name}, just following up on my earlier message. "
        f"I'd really appreciate it if you could let me know about any AI/ML openings "
        f"that might suit my profile. Thank you for your time!"
    )