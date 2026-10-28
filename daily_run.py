"""Manually discover leads; message drafts are prepared individually for review."""
import find_leads
import tracker


def main():
    print("Starting LinkedIn lead search...")
    if not find_leads.main():
        print("Lead search stopped because login or security verification failed.")
        return
    print(f"\nLead search complete. {len(tracker.get_queued(1000))} leads are ready for message review.")
    print("Open the dashboard and choose Review message. No messages are sent automatically.")


if __name__ == "__main__":
    main()
