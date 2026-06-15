import os
import re
import smtplib
import time

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SMTP_USER    = os.environ["SMTP_USER"]
SMTP_PASS    = os.environ["SMTP_PASS"]
ALERT_EMAIL  = os.environ["ALERT_EMAIL"]
ALERT_EMAIL2 = os.environ.get("ALERT_EMAIL2", "")

BASE_URL    = "https://www.ingolstadt.de/tevisweb/"
BOOKING_URL = "https://www.ingolstadt.de/termin"


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def wait_sec(seconds=2):
    time.sleep(seconds)


def parse_date_from_text(text) -> datetime | None:
    idx = text.find("Nächster Termin")
    if idx == -1:
        idx = text.lower().find("nächster termin")
    if idx != -1:
        snippet = text[idx: idx + 120]
        print(f"  Snippet: {snippet.strip()}")
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", snippet)
        if match:
            day, month, year = match.groups()
            return datetime(int(year), int(month), int(day))
    matches = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if matches:
        print(f"  Fallback dates: {matches}")
        day, month, year = matches[0]
        return datetime(int(year), int(month), int(day))
    return None


def navigate_and_get_date(driver) -> datetime | None:
    W = WebDriverWait(driver, 15)

    print("Step 1: Loading homepage...")
    driver.get(BASE_URL)
    wait_sec(3)

    print("Step 2: Loading service selection page...")
    driver.get("https://www.ingolstadt.de/tevisweb/select2?md=5")
    wait_sec(4)

    print("Step 3: Setting cnc-246 = 1 via jQuery...")
    result = driver.execute_script("""
        try {
            var $plusBtn = $("#button-plus-246");
            if ($plusBtn.length === 0) return "ERROR: button-plus-246 not found";
            $plusBtn.prop('disabled', false);
            $plusBtn.trigger('click');
            return "clicked + button. input val: " + $("#input-246").val();
        } catch(e) {
            return "EXCEPTION: " + e.toString();
        }
    """)
    print(f"  jQuery result: {result}")
    wait_sec(2)

    print("Step 4: Clicking Weiter...")
    driver.execute_script("""
        var $btn = $("#WeiterButton");
        $btn.removeClass("disabledButton");
        $btn.prop("disabled", false);
        $btn.attr("aria-disabled", "false");
        $btn.unbind("click");
    """)
    wait_sec(1)
    weiter = driver.find_element(By.ID, "WeiterButton")
    driver.execute_script("arguments[0].click();", weiter)
    wait_sec(3)
    print(f"  URL after Weiter: {driver.current_url}")

    print("Step 4b: Handling Hinweis popup (clicking OK)...")
    try:
        ok_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "OKButton"))
        )
        driver.execute_script("arguments[0].click();", ok_btn)
        print("  Clicked OK on Hinweis popup.")
    except Exception:
        print("  No Hinweis popup found (or already dismissed).")
    wait_sec(3)
    print(f"  URL after OK: {driver.current_url}")

    print("Step 5: Parsing date...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(),'Nächster')]")
            )
        )
    except Exception:
        print("  Timed out waiting.")
    wait_sec(2)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    return parse_date_from_text(body_text)


def send_alert(appt_date: datetime) -> None:
    subject = "Early Appointment available - Wohnungsanmeldung - Kar jaldi Book!"
    body = (
        f"Hallo Bhaiyaji,\n\n"
        f"Tamari Dharmpatni mate ek veli appointment male chhe!\n\n"
        f"  Navi appointment: {appt_date.strftime('%d.%m.%Y')}\n\n"
        f"Joti hoy to jaldi lai le\n{BOOKING_URL}\n\n"
        f"(Aa ek Automatic alert chhe!!)\n"
    )


    recipients = [ALERT_EMAIL]
    if ALERT_EMAIL2:
        recipients.append(ALERT_EMAIL2)

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())
    print(f"Alert sent to {recipients}! Appointment: {appt_date.strftime('%d.%m.%Y')}")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Checking appointment...")
    driver = get_driver()
    try:
        appt_date = navigate_and_get_date(driver)
    finally:
        driver.quit()

    if appt_date is None:
        print("Could not parse date.")
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_away = (appt_date - today).days
    print(f"Next appointment: {appt_date.strftime('%d.%m.%Y')} ({days_away} days away)")

    if days_away <= 7:
        print("Within 7 days! Sending alert...")
        send_alert(appt_date)
    else:
        print("Not within 7 days. No alert sent.")


if __name__ == "__main__":
    main()
