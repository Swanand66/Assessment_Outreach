import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Resolve the brochure path relative to this file
_DIR = os.path.dirname(os.path.abspath(__file__))
BROCHURE_PATH = os.path.join(_DIR, "services_brochure.pdf")

# Auto-generate the brochure if it doesn't exist yet
if not os.path.exists(BROCHURE_PATH):
    try:
        from generate_brochure import build_pdf
        build_pdf(BROCHURE_PATH)
    except Exception as e:
        print(f"⚠️  Could not generate brochure: {e}")


def send_email_to_lead(to_email: str, subject: str, body: str) -> bool:
    from dotenv import dotenv_values
    env_vars = dotenv_values(os.path.join(_DIR, ".env"))

    smtp_server   = env_vars.get("SMTP_SERVER", "")
    smtp_port     = env_vars.get("SMTP_PORT", "587")
    smtp_user     = env_vars.get("SMTP_USER", "")
    smtp_password = env_vars.get("SMTP_PASSWORD", "")

    if smtp_server and smtp_user and smtp_password and smtp_user != "your_email@gmail.com":
        try:
            msg = MIMEMultipart()
            msg["From"]    = smtp_user
            msg["To"]      = to_email
            msg["Subject"] = subject

            # Plain-text body
            msg.attach(MIMEText(body, "plain"))

            # Attach the brochure PDF if it exists
            if os.path.exists(BROCHURE_PATH):
                with open(BROCHURE_PATH, "rb") as f:
                    pdf_part = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_part.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename="Hyper-Nova AI — Services Brochure.pdf"
                    )
                    msg.attach(pdf_part)
                print(f"📎 Brochure attached ({os.path.getsize(BROCHURE_PATH) // 1024} KB)")
            else:
                print("⚠️  Brochure PDF not found — sending without attachment.")

            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ SMTP sent to {to_email}")
            return True

        except Exception as e:
            print(f"❌ SMTP Error: {e}")
            return False
    else:
        # Simulation mode (no credentials configured)
        print("\n" + "=" * 55)
        print(f"📨 [SIMULATION] Email → {to_email}")
        print(f"   Subject : {subject}")
        print(f"   Body    : {body[:120]}...")
        print(f"   Attach  : services_brochure.pdf (simulated)")
        print("=" * 55 + "\n")
        return True
