(function () {
    'use strict';
    
    // Get CSRF token from cookies
    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }
    const csrftoken = getCookie('csrftoken');

    // Attach click handler to all order status buttons
    document.addEventListener('click', function (e) {
        const btn = e.target;
        if (!btn.classList.contains('order-status-btn')) return;

        const orderId = btn.dataset.orderId;
        const action = btn.dataset.action;

        if (!orderId || !action) {
            console.error('Missing orderId or action');
            return;
        }

        // If cancelling, ask for reason
        if (action === 'cancel') {
            Swal.fire({
                title: 'Cancel Order?',
                input: 'text',
                inputPlaceholder: 'Reason (optional)',
                inputAttributes: {
                    maxlength: 200
                },
                showCancelButton: true,
                confirmButtonText: 'Yes, cancel order',
                confirmButtonColor: '#d33',
                cancelButtonText: 'Keep order'
            }).then((result) => {
                if (result.isConfirmed) {
                    sendStatusUpdate(orderId, action, result.value || '');
                }
            });
            return;
        }

        // Confirmation for other actions
        const actionLabels = {
            'accept': 'Accept',
            'making': 'Mark as Making',
            'collect': 'Ready to Collect',
            'delivered': 'Mark as Delivered'
        };

        Swal.fire({
            title: 'Update Order Status?',
            text: `Order #${orderId} → ${actionLabels[action]}`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'OK',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                sendStatusUpdate(orderId, action, '');
            }
        });
    });

    function sendStatusUpdate(orderId, action, reason) {
        // Show loading state
        Swal.fire({
            title: 'Updating...',
            didOpen: () => Swal.showLoading(),
            allowOutsideClick: false,
            allowEscapeKey: false
        });

        const url = `/api/orders/${orderId}/status/`;
        const body = new FormData();
        body.append('action', action);
        if (reason) body.append('reason', reason);

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: body,
            credentials: 'same-origin'
        })
        .then(resp => {
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            return resp.json();
        })
        .then(data => {
            if (data && data.success) {
                Swal.fire({
                    title: '✓ Success',
                    text: `Order #${orderId} is now "${data.status}".\n${data.email_sent ? '📧 Email sent' : ''}${data.fcm_sent ? ' • 🔔 Push sent' : ''}`,
                    icon: 'success',
                    confirmButtonText: 'OK'
                }).then(() => {
                    // Reload page to show updated status
                    window.location.reload();
                });
            } else {
                Swal.fire(
                    'Error',
                    (data && data.error) || 'Failed to update order status',
                    'error'
                );
            }
        })
        .catch(err => {
            console.error('Request error:', err);
            Swal.fire(
                'Error',
                'Network error. Please try again.',
                'error'
            );
        });
    }
})();
