import firebase_admin
from firebase_admin import credentials, messaging
from django.core.mail import send_mail
from django.conf import settings
import os

# Initialize Firebase Admin
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": settings.FIREBASE_PROJECT_ID,
    "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
    "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
    "client_email": settings.FIREBASE_CLIENT_EMAIL,
    "client_id": settings.FIREBASE_CLIENT_ID,
})
firebase_admin.initialize_app(cred)

def send_order_notification(order, action):
    """Send notifications across all channels"""
    status_messages = {
        'accept': 'Your order has been accepted',
        'making': 'Your order is being prepared',
        'collect': 'Your order is ready for collection',
        'delivered': 'Your order has been delivered',
        'cancel': 'Your order has been cancelled'
    }
    
    message = status_messages.get(action, 'Your order status has been updated')
    
    # Send email
    send_email_notification(order.email, message)
    
    # Send push notification
    if order.fcm_token:
        send_push_notification(order.fcm_token, message)

def send_email_notification(email, message):
    """Send email notification using Gmail SMTP"""
    subject = 'Order Status Update'
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )

def send_push_notification(token, message):
    """Send Firebase push notification"""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title='Order Update',
                body=message
            ),
            token=token,
        )
        messaging.send(message)
    except Exception as e:
        print(f"Failed to send push notification: {str(e)}")
