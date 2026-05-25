# WebSocket Order Management System - Complete Guide

## 🔌 **WebSocket Endpoints**

### **Base URL:** `ws://localhost:8000`

---

## 👥 **Customer WebSocket**

**Endpoint:** `ws://localhost:8000/orders-ws/customer/{customer_id}`

### **Connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/orders-ws/customer/CUST-123456`);

ws.onopen = () => {
    console.log("Connected to order system");
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log("Received:", message);
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("Disconnected from order system");
};
```

---

## 📬 **Customer Message Types**

### **1. Place Order from Cart**
```json
{
    "type": "place_order_from_cart",
    "platform_fee": 50,
    "delivery_fee": 40,
    "taxes": 45,
    "payment_mode": "cod",
    "receiver_name": "John Doe",
    "receiver_phone": "9876543210",
    "delivery_address": {
        "address": "123 Main Street",
        "lat": 28.6139,
        "lng": 77.2090
    }
}
```

**Response:**
```json
{
    "type": "order_placed",
    "status": "success",
    "message": "Order placed successfully",
    "order": {
        "order_id": "ORD_CUST-123456_1779699879539",
        "customer_id": "CUST-123456",
        "order_type": "cart",
        "order_status": "broadcast",
        "total_bill_amount": 500,
        "payment_mode": "cod",
        "items": [...]
    }
}
```

---

### **2. Place Prescription Order**
```json
{
    "type": "place_order_from_prescription",
    "platform_fee": 50,
    "delivery_fee": 40,
    "taxes": 45,
    "payment_mode": "cod",
    "receiver_name": "John Doe",
    "receiver_phone": "9876543210",
    "delivery_address": {
        "address": "123 Main Street",
        "lat": 28.6139,
        "lng": 77.2090
    },
    "prescription": "base64_encoded_image_or_pdf"
}
```

**Response:**
```json
{
    "type": "order_placed",
    "status": "success",
    "message": "Prescription order placed successfully",
    "order": { ... }
}
```

---

### **3. Get All Orders**
```json
{
    "type": "get_orders",
    "page": 1,
    "limit": 10
}
```

**Response:**
```json
{
    "type": "orders_list",
    "total": 5,
    "page": 1,
    "limit": 10,
    "data": [ ... ]
}
```

---

### **4. Get Order Details**
```json
{
    "type": "get_order_details",
    "order_id": "ORD_CUST-123456_1779699879539"
}
```

**Response:**
```json
{
    "type": "order_details",
    "order": { ... }
}
```

---

### **5. Cancel Order**
```json
{
    "type": "cancel_order",
    "order_id": "ORD_CUST-123456_1779699879539"
}
```

**Response:**
```json
{
    "type": "order_cancelled",
    "status": "success",
    "message": "Order cancelled successfully",
    "order": { ... }
}
```

---

### **6. Initiate Online Payment**
```json
{
    "type": "initiate_payment",
    "order_id": "ORD_CUST-123456_1779699879539"
}
```

**Response:**
```json
{
    "type": "payment_initiated",
    "status": "success",
    "razorpay_order_id": "order_1234567890",
    "amount": 500,
    "currency": "INR"
}
```

---

### **7. Verify Payment**
```json
{
    "type": "verify_payment",
    "order_id": "ORD_CUST-123456_1779699879539",
    "razorpay_payment_id": "pay_1234567890",
    "razorpay_order_id": "order_1234567890",
    "razorpay_signature": "signature_hash"
}
```

**Response:**
```json
{
    "type": "payment_verified",
    "status": "success",
    "message": "Payment verified successfully",
    "order": { ... }
}
```

---

### **8. Keep-Alive Ping**
```json
{
    "type": "ping"
}
```

**Response:**
```json
{
    "type": "pong"
}
```

---

## 🏪 **Pharmacy Shop WebSocket**

**Endpoint:** `ws://localhost:8000/orders-ws/shop/{shop_id}`

### **Connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/orders-ws/shop/SHOP-789012`);

ws.onopen = () => {
    console.log("Connected as pharmacy shop");
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === "new_order_broadcast") {
        // New order available for acceptance
        console.log("New order:", message.order);
        showNotification(`New order: ${message.order.order_type}`);
    }
};
```

---

## 📬 **Pharmacy Shop Message Types**

### **1. Accept Broadcast Order**
```json
{
    "type": "accept_order",
    "order_id": "ORD_CUST-123456_1779699879539"
}
```

**Response:**
```json
{
    "type": "order_accepted",
    "status": "success",
    "message": "Order accepted successfully",
    "order": {
        "order_id": "ORD_CUST-123456_1779699879539",
        "order_status": "accepted",
        "shop_id": "SHOP-789012",
        "accepted_at": "2026-05-25T10:30:00Z"
    }
}
```

---

### **2. Update Order for Packing**
```json
{
    "type": "update_packing",
    "order_id": "ORD_CUST-123456_1779699879539",
    "rider_name": "Raj Kumar",
    "rider_phone": "9876543210",
    "vehicle_number": "DL01AB1234",
    "vehicle_model": "Bike",
    "items": [
        {
            "medicine_id": "MED123",
            "medicine_name": "Aspirin",
            "quantity": 2,
            "price_per_unit": 50,
            "subtotal": 100
        }
    ],
    "item_total": 100
}
```

**Response:**
```json
{
    "type": "order_updated",
    "status": "success",
    "message": "Order updated for packing",
    "order": {
        "order_status": "packing",
        "rider_name": "Raj Kumar",
        "rider_phone": "9876543210",
        "vehicle_number": "DL01AB1234",
        "vehicle_model": "Bike"
    }
}
```

---

### **3. Update Order Status**
```json
{
    "type": "update_status",
    "order_id": "ORD_CUST-123456_1779699879539",
    "new_status": "out_for_delivery"
}
```

**Response:**
```json
{
    "type": "order_status_updated",
    "status": "success",
    "message": "Order status updated to out_for_delivery",
    "order": {
        "order_status": "out_for_delivery"
    }
}
```

---

### **4. Mark Order as Delivered**
```json
{
    "type": "update_status",
    "order_id": "ORD_CUST-123456_1779699879539",
    "new_status": "delivered",
    "transaction_id": "TXN123456"
}
```

**Response:**
```json
{
    "type": "order_status_updated",
    "status": "success",
    "message": "Order status updated to delivered",
    "order": {
        "order_status": "delivered",
        "delivered_at": "2026-05-25T11:00:00Z",
        "payment_status": "success"
    }
}
```

---

### **5. Get Shop Orders**
```json
{
    "type": "get_shop_orders",
    "status": "accepted",
    "page": 1,
    "limit": 20
}
```

**Response:**
```json
{
    "type": "orders_list",
    "total": 3,
    "page": 1,
    "limit": 20,
    "status_filter": "accepted",
    "data": [ ... ]
}
```

---

## 🔔 **Real-Time Notifications Received**

### **New Order Broadcast (to all shops)**
```json
{
    "type": "new_order_broadcast",
    "event": "broadcast",
    "message": "New cart order available",
    "order": {
        "order_id": "ORD_CUST-123456_1779699879539",
        "order_type": "cart",
        "receiver_name": "John Doe",
        "total_bill_amount": 500,
        "items": [...]
    }
}
```

---

### **Order Accepted (to customer)**
```json
{
    "type": "order_accepted",
    "status": "accepted",
    "message": "Your order has been accepted by Naiyo24 Medicine",
    "shop_name": "Naiyo24 Medicine",
    "order": { ... }
}
```

---

### **Order Status Update (to customer)**
```json
{
    "type": "order_status_update",
    "status": "packing",
    "message": "Your order is being packed",
    "order": { ... }
}
```

---

## ⚠️ **Error Messages**

All errors follow this format:
```json
{
    "type": "error",
    "message": "Error description here",
    "details": "Optional additional details"
}
```

**Examples:**
```json
{
    "type": "error",
    "message": "Cart is empty"
}
```

```json
{
    "type": "error",
    "message": "Cannot cancel order in packing status"
}
```

---

## 📊 **Real-Time Flow Diagram**

### **Cart Order Flow:**
```
Customer connects (WS)
    ↓
Customer adds items to cart (REST API)
    ↓
Customer places order (WS: place_order_from_cart)
    ↓
🔔 All connected shops receive notification (WS broadcast)
    ↓
Shop accepts order (WS: accept_order)
    ↓
🔔 Customer receives acceptance notification (WS)
    ↓
Shop updates packing info (WS: update_packing)
    ↓
🔔 Customer notified (WS)
    ↓
Shop dispatches (WS: update_status → out_for_delivery)
    ↓
🔔 Customer notified (WS)
    ↓
Shop delivers (WS: update_status → delivered)
    ↓
🔔 Customer notified + Earnings created (WS)
```

---

## 🎯 **Advantages of WebSocket vs REST**

| Aspect | WebSocket | REST |
|--------|-----------|------|
| Real-time | ✅ Instant | ❌ Polling delay |
| Latency | Ultra-low | 5-30 seconds |
| Notifications | ✅ Push | ❌ Pull only |
| Connection | Persistent | One-time |
| Battery (mobile) | ⚠️ Always on | ✅ Better |
| Complexity | Medium | Simple |

---

## 💡 **Usage Tips**

1. **Mobile App**: Implement reconnection logic when network changes
2. **Browser**: Use browser DevTools → Network → WS to monitor WebSocket
3. **Logging**: Log all incoming messages for debugging
4. **Heartbeat**: Send `ping` every 30 seconds to keep connection alive
5. **Error Handling**: Implement exponential backoff for reconnection

---

## 🔐 **Security Notes**

- Always validate `customer_id` and `shop_id` before connecting
- Verify customer/shop status on each operation
- All WebSocket messages follow same validation as REST
- CORS applies to WebSocket upgrade handshake
