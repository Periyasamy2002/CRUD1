from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notifications_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:20]
    data = [{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "url": n.url,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat()
    } for n in qs]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"notifications": data, "unread": unread_count})

@login_required
def mark_read(request, pk):
    try:
        n = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return HttpResponseNotFound()
    n.is_read = True
    n.save(update_fields=["is_read"])
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"success": True, "unread": unread_count})
