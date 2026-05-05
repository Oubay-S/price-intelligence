import requests
import os
import datetime

def send_notification(message, status="error"):
    """
    Sends a notification to a Discord or Slack webhook.
    Set DISCORD_WEBHOOK_URL or SLACK_WEBHOOK_URL in your .env file.
    """
    webhook_url = os.environ.get("NOTIFICATION_WEBHOOK_URL")
    
    if not webhook_url:
        print(f"📢 Notification (No Webhook configured): {message}")
        return

    # Determine emoji based on status
    emoji = "🚨" if status == "error" else "✅"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    payload = {
        "content": f"{emoji} **Price Intelligence Alert** [{timestamp}]\n> {message}"
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("🚀 Notification sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

if __name__ == "__main__":
    # Test notification
    send_notification("Test notification from Price Intelligence Platform", status="info")
