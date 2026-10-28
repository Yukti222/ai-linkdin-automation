"""Legacy LinkedIn sender entry point, retained as a safe disabled command."""


def run_linkedin_outreach():
    print(
        "LinkedIn auto-sending is disabled. Use the dashboard's Review message "
        "action to prepare an unsent draft."
    )
    return False


if __name__ == "__main__":
    run_linkedin_outreach()
