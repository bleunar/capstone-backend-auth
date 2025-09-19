import smtplib
from config import config
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from services.core import get_mail_server


def send_email(receiver: str, subject: str, body: str, html_body: str = None):
    try:
        message = MIMEMultipart("alternative")
        message["From"] = f"{"System"} <{config.MAIL_ADDRESS}>"
        message["To"] = receiver
        message["Subject"] = subject

        footer = "\n\nTHIS IS AN AUTOMATED MESSAGE, DO NOT REPLY."
        message.attach(MIMEText(body + footer, "plain"))

        if html_body:
            html_content = f"""
            <html>
              <body>
                {html_body}
                <br><br>
                <p><i>THIS IS AN AUTOMATED MESSAGE, DO NOT REPLY.</i></p>
              </body>
            </html>
            """
            message.attach(MIMEText(html_content, "html"))

        server = get_mail_server()
        if not server:
            return {"success": False, "msg": "Mail server connection failed"}

        server.sendmail(config.MAIL_ADDRESS, receiver, message.as_string())
        server.quit()

        return {"success": True, "msg": "Email sent successfully"}

    except Exception as err:
        return {"success": False, "msg": f"Failed to send email: {err}"}
