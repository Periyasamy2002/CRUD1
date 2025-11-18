




@csrf_exempt
def order_submit(request):
    """
    Accepts both JSON (AJAX) and regular form POSTs.
    Supports:
      - cart: [ {name, price, qty}, ... ]  (JSON array)
      - single item: item, price, qty, mobile, address, delivery, orderType
    For guest users, an 'email' field is required.
    On success:
      - For JSON requests: returns JsonResponse with created order ids
      - For form POSTs: stores created ids in session['last_order_ids'] and redirects to cart_page
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    # Determine request type (JSON/AJAX vs form)
    is_json = request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        # Parse payload
        if is_json:
            try:
                data = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
        else:
            # POST form; attempt to read a JSON 'cart' field if present
            data = request.POST.dict()
            if 'cart' in request.POST:
                try:
                    data['cart'] = json.loads(request.POST['cart'])
                except Exception:
                    data['cart'] = None

        # Determine email (guest must provide, logged-in users may omit)
        email = data.get('email') or (request.user.email if getattr(request, 'user', None) and request.user.is_authenticated else None)
        if not email:
            if is_json:
                return JsonResponse({'success': False, 'error': 'Email is required for guest orders.'}, status=400)
            messages.error(request, 'Email is required to place an order.')
            return redirect('cart_page')

        created_ids = []
        cart = data.get('cart')
        # Normalize some possible field names
        def _num(v, default=0):
            try:
                return float(v)
            except Exception:
                return default

        if cart and isinstance(cart, list):
            # Bulk/cart create
            mobile = data.get('mobile') or data.get('phone') or ''
            address = data.get('address') or ''
            delivery = data.get('delivery') or ''
            order_type = data.get('orderType') or data.get('order_type') or 'now'
            order_date = data.get('orderDate') if order_type == 'later' else None
            order_time = data.get('orderTime') if order_type == 'later' else None

            # Simple contact validation for cart orders
            if not (mobile and address and delivery):
                if is_json:
                    return JsonResponse({'success': False, 'error': 'Missing contact/delivery info for cart order.'}, status=400)
                messages.error(request, 'Please provide phone, address and delivery option.')
                return redirect('cart_page')

            for c in cart:
                name = c.get('name') or c.get('item') or c.get('item_name')
                price = _num(c.get('price'), 0)
                qty = int(c.get('qty') or c.get('quantity') or 1)
                if not name:
                    if is_json:
                        return JsonResponse({'success': False, 'error': 'Cart item missing name.'}, status=400)
                    messages.error(request, 'One of the cart items is missing a name.')
                    return redirect('cart_page')
                order = Order.objects.create(
                    item=name,
                    price=price,
                    qty=qty,
                    order_type=order_type,
                    order_date=order_date,
                    order_time=order_time,
                    email=email,
                    mobile=mobile,
                    address=address,
                    delivery=delivery,
                )
                created_ids.append(order.id)
        else:
            # Single item flow (form or JSON)
            item = data.get('item') or data.get('name')
            price = _num(data.get('price') or data.get('amount'), 0)
            qty = int(data.get('qty') or data.get('quantity') or 1)
            mobile = data.get('mobile') or data.get('phone') or ''
            address = data.get('address') or ''
            delivery = data.get('delivery') or ''
            order_type = data.get('orderType') or data.get('order_type') or 'now'
            order_date = data.get('orderDate') if order_type == 'later' else None
            order_time = data.get('orderTime') if order_type == 'later' else None

            # Validate required fields
            if not all([item, price is not None, qty, mobile, address, delivery]):
                if is_json:
                    return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)
                messages.error(request, 'Please fill all required order fields.')
                return redirect('cart_page')

            order = Order.objects.create(
                item=item,
                price=price,
                qty=qty,
                order_type=order_type,
                order_date=order_date,
                order_time=order_time,
                email=email,
                mobile=mobile,
                address=address,
                delivery=delivery,
            )
            created_ids.append(order.id)

        # store created ids in session so cart.html can show last successful order(s)
        request.session['last_order_ids'] = created_ids

        # Send email confirmation
        subject = 'New Order Received'
        
        # Prepare order details for the email body
        order_details_str = ""
        total_price = 0
        if cart and isinstance(cart, list):
            for c in cart:
                name = c.get('name') or c.get('item') or c.get('item_name')
                price = _num(c.get('price'), 0)
                qty = int(c.get('qty') or c.get('quantity') or 1)
                item_total = price * qty
                total_price += item_total
                order_details_str += f"  - {name} (x{qty}): {item_total:.2f} CHF\n"
        else:
            name = data.get('item') or data.get('name')
            price = _num(data.get('price') or data.get('amount'), 0)
            qty = int(data.get('qty') or data.get('quantity') or 1)
            total_price = price * qty
            order_details_str = f"  - {name} (x{qty}): {total_price:.2f} CHF\n"


        message = f"""
        <div class="container">
        <h2>New Order Received</h2>

        <p>A new order has been placed.</p>

        <div class="section-title">Customer Details:</div>
        <div class="details">
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Mobile:</strong> {data.get('mobile') or data.get('phone') or ''}</p>
            <p><strong>Address:</strong> {data.get('address') or ''}</p>
        </div>

        <div class="section-title">Order Details:</div>
        <div class="order-box">
            {order_details_str}
        </div>

        <p><strong>Total Price:</strong> {total_price:.2f} CHF</p>

        <div class="details">
            <p><strong>Delivery Method:</strong> {data.get('delivery') or ''}</p>
            <p><strong>Order Type:</strong> {data.get('orderType') or data.get('order_type') or 'now'}</p>
        </div>
        """

        # 🔥 ADD EXTRA INFO ONLY IF orderType == 'later'
        if (data.get('orderType') or data.get('order_type')) == 'later':
            message += f"""
            <p><strong>Scheduled for:</strong> {data.get('orderDate')} at {data.get('orderTime')}</p>
            """

        # close div
        message += "</div>"

                

        try:
            to = [{"email": "vshigamaru@gmail.com"}]
            send_new_email(to,cc=[],bcc=[],subject=subject,content=message)
                
              
            
        except Exception as e:
            # Log the error but don't fail the request
            logging.error(f"Failed to send order confirmation email: {e}")

        if is_json:
            return JsonResponse({'success': True, 'order_ids': created_ids})
        else:
            messages.success(request, 'Order placed successfully.')
            return redirect('cart_page')

    except Exception as e:
        # Log the error and respond appropriately
        # (keep server-rendered behavior friendly)
        if is_json:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Failed to place order: {e}')
        return redirect('cart_page')
    
