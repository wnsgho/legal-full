from playwright.sync_api import Page, expect
import traceback

def test_dashboard_screenshot(page: Page):
    """
    This test verifies that the dashboard page loads correctly.
    """
    try:
        print("Navigating to http://localhost:5173")
        page.goto("http://localhost:5173")
        print("Navigation successful")

        print("Waiting for heading")
        expect(page.get_by_role("heading", name="계약서 분석 AI")).to_be_visible()
        print("Heading found")

        print("Taking screenshot")
        page.screenshot(path="jules-scratch/verification/verification.png")
        print("Screenshot taken")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())
