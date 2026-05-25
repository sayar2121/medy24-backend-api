from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
import json
import base64
from typing import Optional

from db import get_db
from models.medicine.medicine_order_models import Order
from models.cart.cart_models import Cart
from models.auth.customer_user_models import CustomerUser
from models.auth.pharma_shop_user_models import PharmaShopUser
from models.earnings.pharma_shop_earning_models import Earning
from services.medicine.medicine_order_id_generator import generate_order_id
from services.earnings.earning_id_generator import generate_earning_id
from services.medicine.prescription_upload import save_and_compress_prescription, save_and_compress_prescription_bytes, delete_prescription
from services.websocket.connection_manager import connection_manager
from services.razorpay.razorpay_services import client as razorpay_client

router = APIRouter(prefix="/orders-ws", tags=["Medicine Orders WebSocket"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_total_bill(item_total: float, platform_fee: float, delivery_fee: float, taxes: float) -> float:
    # Calculate total bill amount from item total and all charges
    return item_total + platform_fee + delivery_fee + taxes


def create_earnings_record(db: Session, shop_id: str, order_id: str, total_bill: float, 
                          platform_fee: float, delivery_fee: float, taxes: float, payment_mode: str) -> Earning:
    # Create earnings record for pharma shop with all deductions calculated
    earning_id = generate_earning_id(shop_id)
    net_earning = total_bill - (platform_fee + delivery_fee + taxes)
    
    earning = Earning(
        earning_id=earning_id,
        shop_id=shop_id,
        order_id=order_id,
        total_bill_amount=total_bill,
        platform_fee_deduction=platform_fee,
        delivery_fee_deduction=delivery_fee,
        taxes_deduction=taxes,
        net_earning=net_earning,
        payment_mode=payment_mode,
        settlement_status="pending"
    )
    
    db.add(earning)
    db.commit()
    db.refresh(earning)
    
    return earning


# ============================================================================
# CUSTOMER WEBSOCKET
# ============================================================================

@router.websocket("/customer/{customer_id}")
async def websocket_customer_endpoint(
    websocket: WebSocket,
    customer_id: str,
    db: Session = Depends(get_db)
):
    # WebSocket endpoint for customers to place orders and track status
    try:
        # Verify customer exists
        customer = db.query(CustomerUser).filter(CustomerUser.customer_id == customer_id).first()
        if not customer:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Customer not found")
            return
        
        if customer.status != "active":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Customer account not active")
            return
        
        # Connect customer
        await connection_manager.connect_customer(customer_id, websocket)
        
        # Send welcome message
        await connection_manager.send_to_customer(customer_id, {
            "type": "connection",
            "status": "connected",
            "message": f"Welcome {customer.full_name or 'Customer'}",
            "customer_id": customer_id
        })
        
        # Listen for messages from customer
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "place_order_from_cart":
                # Customer places order from cart items
                await handle_place_order_from_cart(customer_id, data, websocket, db)
            
            elif message_type == "place_order_from_prescription":
                # Customer places prescription order
                await handle_place_order_from_prescription(customer_id, data, websocket, db)
            
            elif message_type == "get_orders":
                # Customer requests all their orders
                await handle_get_customer_orders(customer_id, data, websocket, db)
            
            elif message_type == "get_order_details":
                # Customer requests specific order details
                await handle_get_order_details(customer_id, data, websocket, db)
            
            elif message_type == "cancel_order":
                # Customer cancels an order
                await handle_cancel_order(customer_id, data, websocket, db)
            
            elif message_type == "initiate_payment":
                # Customer initiates Razorpay payment
                await handle_initiate_payment(customer_id, data, websocket, db)
            
            elif message_type == "verify_payment":
                # Customer verifies payment
                await handle_verify_payment(customer_id, data, websocket, db)
            
            elif message_type == "ping":
                # Keep-alive ping
                await connection_manager.send_to_customer(customer_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        connection_manager.disconnect_customer(customer_id)
    except Exception as e:
        print(f"❌ Customer WebSocket error: {e}")
        connection_manager.disconnect_customer(customer_id)


async def handle_place_order_from_cart(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Place order from cart items through WebSocket
    try:
        platform_fee = float(data.get("platform_fee", 0))
        delivery_fee = float(data.get("delivery_fee", 0))
        taxes = float(data.get("taxes", 0))
        payment_mode = data.get("payment_mode", "cod")
        receiver_name = data.get("receiver_name")
        receiver_phone = data.get("receiver_phone")
        delivery_address = data.get("delivery_address")
        
        # Validate inputs
        if not all([receiver_name, receiver_phone, delivery_address, payment_mode]):
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Missing required fields",
                "details": "receiver_name, receiver_phone, delivery_address, payment_mode required"
            })
            return
        
        if payment_mode not in ["cod", "online"]:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Invalid payment mode"
            })
            return
        
        # Get customer's cart
        cart = db.query(Cart).filter(Cart.customer_id == customer_id).first()
        if not cart or not cart.items:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Cart is empty"
            })
            return
        
        # Generate order ID
        order_id = generate_order_id(customer_id)
        
        # Calculate totals
        item_total = cart.total_price
        total_bill = calculate_total_bill(item_total, platform_fee, delivery_fee, taxes)
        
        # Create order
        new_order = Order(
            order_id=order_id,
            customer_id=customer_id,
            shop_id=None,
            order_type="cart",
            items=cart.items,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            delivery_address=delivery_address,
            item_total=item_total,
            platform_fee=platform_fee,
            delivery_fee=delivery_fee,
            taxes=taxes,
            total_bill_amount=total_bill,
            payment_mode=payment_mode,
            payment_status="pending",
            order_status="broadcast"
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        # Clear cart
        cart.items = []
        cart.total_price = 0.0
        db.commit()
        
        # Notify customer of successful order placement
        await connection_manager.send_to_customer(customer_id, {
            "type": "order_placed",
            "status": "success",
            "message": "Order placed successfully",
            "order": new_order.to_dict()
        })
        
        # Broadcast order to all listening pharmacy shops
        await connection_manager.broadcast_to_listening_shops({
            "type": "new_order_broadcast",
            "event": "broadcast",
            "order": new_order.to_dict(),
            "message": f"New {new_order.order_type} order available"
        })
    
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Failed to place order: {str(e)}"
        })


async def handle_place_order_from_prescription(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Place prescription order through WebSocket
    try:
        platform_fee = float(data.get("platform_fee", 0))
        delivery_fee = float(data.get("delivery_fee", 0))
        taxes = float(data.get("taxes", 0))
        payment_mode = data.get("payment_mode", "cod")
        receiver_name = data.get("receiver_name")
        receiver_phone = data.get("receiver_phone")
        delivery_address = data.get("delivery_address")
        prescription_base64 = data.get("prescription")  # Base64 encoded file
        
        # Validate inputs
        if not all([receiver_name, receiver_phone, delivery_address, payment_mode, prescription_base64]):
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Missing required fields"
            })
            return
        
        # Generate order ID first
        order_id = generate_order_id(customer_id)
        
        # Decode and save prescription file using service function
        prescription_url = None
        try:
            # Decode base64 prescription
            prescription_bytes = base64.b64decode(prescription_base64)
            
            # Determine file extension from base64 data (common formats)
            filename = "prescription.jpg"  # Default filename
            if prescription_base64.startswith("iVBORw0KGgo"):  # PNG signature
                filename = "prescription.png"
            elif prescription_base64.startswith("JVBERi0"):  # PDF signature
                filename = "prescription.pdf"
            
            # Use service function to save and compress
            prescription_url = save_and_compress_prescription_bytes(
                prescription_bytes, filename, order_id
            )
            
        except Exception as e:
            print(f"❌ Failed to save prescription: {e}")
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": f"Failed to upload prescription: {str(e)}"
            })
            return
        
        # Create order with uploaded prescription file path
        new_order = Order(
            order_id=order_id,
            customer_id=customer_id,
            shop_id=None,
            order_type="prescription",
            prescription_url=prescription_url,
            items=[],
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            delivery_address=delivery_address,
            item_total=0.0,
            platform_fee=platform_fee,
            delivery_fee=delivery_fee,
            taxes=taxes,
            total_bill_amount=calculate_total_bill(0, platform_fee, delivery_fee, taxes),
            payment_mode=payment_mode,
            payment_status="pending",
            order_status="broadcast"
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        # Notify customer
        await connection_manager.send_to_customer(customer_id, {
            "type": "order_placed",
            "status": "success",
            "message": "Prescription order placed successfully",
            "order": new_order.to_dict()
        })
        
        # Broadcast to pharmacy shops
        await connection_manager.broadcast_to_listening_shops({
            "type": "new_order_broadcast",
            "event": "prescription_broadcast",
            "order": new_order.to_dict(),
            "message": "New prescription order available"
        })
    
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Failed to place prescription order: {str(e)}"
        })


async def handle_get_customer_orders(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Send all customer orders to customer (no pagination - instant push)
    try:
        orders = db.query(Order).filter(Order.customer_id == customer_id).all()
        
        await connection_manager.send_to_customer(customer_id, {
            "type": "orders_list",
            "total": len(orders),
            "data": [order.to_dict() for order in orders]
        })
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Failed to fetch orders: {str(e)}"
        })


async def handle_get_order_details(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Send specific order details to customer
    try:
        order_id = data.get("order_id")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.customer_id != customer_id:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Order not found"
            })
            return
        
        await connection_manager.send_to_customer(customer_id, {
            "type": "order_details",
            "order": order.to_dict()
        })
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Failed to fetch order: {str(e)}"
        })


async def handle_cancel_order(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Cancel an order
    try:
        order_id = data.get("order_id")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.customer_id != customer_id:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Order not found"
            })
            return
        
        if order.order_status not in ["broadcast", "accepted"]:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": f"Cannot cancel order in {order.order_status} status"
            })
            return
        
        # Delete prescription file if exists
        if order.prescription_url:
            delete_prescription(order.prescription_url)
        
        order.order_status = "cancelled"
        db.commit()
        
        await connection_manager.send_to_customer(customer_id, {
            "type": "order_cancelled",
            "status": "success",
            "message": "Order cancelled successfully",
            "order": order.to_dict()
        })
    
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Failed to cancel order: {str(e)}"
        })


async def handle_initiate_payment(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Initiate Razorpay payment
    try:
        order_id = data.get("order_id")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.customer_id != customer_id:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Order not found"
            })
            return
        
        if order.payment_mode != "online":
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "This order is not set for online payment"
            })
            return
        
        try:
            # Create Razorpay order with correct dictionary format
            razorpay_order = razorpay_client.order.create({
                "amount": int(order.total_bill_amount * 100),  # Amount in paise
                "currency": "INR",
                "receipt": order_id,
                "payment_capture": 1,
                "notes": {
                    "order_id": order_id,
                    "customer_id": customer_id
                }
            })
            
            await connection_manager.send_to_customer(customer_id, {
                "type": "payment_initiated",
                "status": "success",
                "razorpay_order_id": razorpay_order["id"],
                "amount": order.total_bill_amount,
                "currency": "INR"
            })
        except Exception as e:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": f"Failed to initiate payment: {str(e)}"
            })
    
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Payment initiation error: {str(e)}"
        })


async def handle_verify_payment(customer_id: str, data: dict, websocket: WebSocket, db: Session):
    # Verify Razorpay payment
    import hmac
    import hashlib
    import os
    
    try:
        order_id = data.get("order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.customer_id != customer_id:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Order not found"
            })
            return
        
        # Verify signature
        razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        signature = hmac.new(
            razorpay_key_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != razorpay_signature:
            await connection_manager.send_to_customer(customer_id, {
                "type": "error",
                "message": "Payment verification failed"
            })
            return
        
        # Update order
        order.transaction_id = razorpay_payment_id
        order.payment_status = "success"
        db.commit()
        
        # Create earnings record for online payments when payment is verified
        # (For COD orders, earnings are created when shop accepts)
        if order.payment_mode == "online":
            try:
                # Get the shop_id - if order not yet accepted, we'll create earnings without shop_id
                # Once a shop accepts it, the earning will be linked to that shop
                if order.shop_id:
                    # Order already accepted by a shop
                    create_earnings_record(
                        db, order.shop_id, order_id,
                        order.total_bill_amount, order.platform_fee,
                        order.delivery_fee, order.taxes, order.payment_mode
                    )
                    print(f"💰 Earnings record created for online order {order_id} (payment verified)")
                else:
                    # Order still in broadcast, no shop accepted yet
                    # Still create earnings record for accounting
                    earning_id = generate_earning_id(f"PENDING_{customer_id}")
                    net_earning = order.total_bill_amount - (order.platform_fee + order.delivery_fee + order.taxes)
                    
                    earning = Earning(
                        earning_id=earning_id,
                        shop_id=None,  # Will be updated when shop accepts
                        order_id=order_id,
                        total_bill_amount=order.total_bill_amount,
                        platform_fee_deduction=order.platform_fee,
                        delivery_fee_deduction=order.delivery_fee,
                        taxes_deduction=order.taxes,
                        net_earning=net_earning,
                        payment_mode=order.payment_mode,
                        settlement_status="pending"
                    )
                    
                    db.add(earning)
                    db.commit()
                    print(f"💰 Pending earnings record created for online order {order_id}")
            except Exception as e:
                print(f"❌ Failed to create earnings for online payment: {e}")
        
        await connection_manager.send_to_customer(customer_id, {
            "type": "payment_verified",
            "status": "success",
            "message": "Payment verified successfully",
            "order": order.to_dict()
        })
    
    except Exception as e:
        await connection_manager.send_to_customer(customer_id, {
            "type": "error",
            "message": f"Payment verification error: {str(e)}"
        })


# ============================================================================
# PHARMACY SHOP WEBSOCKET
# ============================================================================

@router.websocket("/shop/{shop_id}")
async def websocket_shop_endpoint(
    websocket: WebSocket,
    shop_id: str,
    db: Session = Depends(get_db)
):
    # WebSocket endpoint for pharmacy shops to accept orders and update status
    try:
        # Verify shop exists
        shop = db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first()
        if not shop:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Shop not found")
            return
        
        if shop.status != "active":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Shop account not active")
            return
        
        # Connect shop
        await connection_manager.connect_shop(shop_id, websocket)
        
        # Send welcome message
        await connection_manager.send_to_shop(shop_id, {
            "type": "connection",
            "status": "connected",
            "message": f"Welcome {shop.shop_name}",
            "shop_id": shop_id,
            "connected_shops": connection_manager.get_connected_shops_count()
        })
        
        # Fetch and send all pending broadcast orders to newly connected shop
        try:
            pending_orders = db.query(Order).filter(Order.order_status == "broadcast").all()
            if pending_orders:
                await connection_manager.send_to_shop(shop_id, {
                    "type": "pending_broadcast_orders",
                    "total": len(pending_orders),
                    "message": f"{len(pending_orders)} pending orders available",
                    "data": [order.to_dict() for order in pending_orders]
                })
                print(f"📦 Sent {len(pending_orders)} pending broadcast orders to shop {shop_id}")
            else:
                await connection_manager.send_to_shop(shop_id, {
                    "type": "pending_broadcast_orders",
                    "total": 0,
                    "message": "No pending broadcast orders at this time",
                    "data": []
                })
        except Exception as e:
            print(f"❌ Error fetching pending orders for shop {shop_id}: {e}")
        
        # Listen for messages from shop
        while True:
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "accept_order":
                # Shop accepts a broadcast order
                await handle_accept_order(shop_id, data, websocket, db)
            
            elif message_type == "update_packing":
                # Shop updates order with rider info
                await handle_update_packing(shop_id, data, websocket, db)
            
            elif message_type == "update_status":
                # Shop updates order status
                await handle_update_status(shop_id, data, websocket, db)
            
            elif message_type == "get_shop_orders":
                # Shop requests all their orders
                await handle_get_shop_orders(shop_id, data, websocket, db)
            
            elif message_type == "get_broadcast_orders":
                # Shop requests all pending broadcast orders
                await handle_get_broadcast_orders(shop_id, data, websocket, db)
            
            elif message_type == "ping":
                # Keep-alive ping
                await connection_manager.send_to_shop(shop_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        connection_manager.disconnect_shop(shop_id)
    except Exception as e:
        print(f"❌ Shop WebSocket error: {e}")
        connection_manager.disconnect_shop(shop_id)


async def handle_accept_order(shop_id: str, data: dict, websocket: WebSocket, db: Session):
    # Shop accepts a broadcast order
    try:
        order_id = data.get("order_id")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": "Order not found"
            })
            return
        
        if order.order_status != "broadcast":
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": f"Order is already in {order.order_status} status"
            })
            return
        
        # Accept order
        order.shop_id = shop_id
        order.order_status = "accepted"
        order.accepted_at = datetime.now()
        db.commit()
        db.refresh(order)
        
        # Create or update earnings record when order is accepted
        try:
            # Check if earnings record already exists (for online payments verified before acceptance)
            existing_earning = db.query(Earning).filter(Earning.order_id == order_id).first()
            
            if existing_earning:
                # Online payment already verified - update with shop_id
                existing_earning.shop_id = shop_id
                db.commit()
                print(f"💰 Earnings record updated with shop_id for order {order_id}")
            else:
                # COD or online payment not yet verified - create new earnings record
                create_earnings_record(
                    db, shop_id, order_id,
                    order.total_bill_amount, order.platform_fee,
                    order.delivery_fee, order.taxes, order.payment_mode
                )
                print(f"💰 Earnings record created for order {order_id}")
        except Exception as e:
            print(f"❌ Failed to create/update earnings record: {e}")
        
        # Notify shop
        await connection_manager.send_to_shop(shop_id, {
            "type": "order_accepted",
            "status": "success",
            "message": "Order accepted successfully",
            "order": order.to_dict()
        })
        
        # Notify customer
        if connection_manager.is_customer_connected(order.customer_id):
            await connection_manager.send_to_customer(order.customer_id, {
                "type": "order_accepted",
                "status": "accepted",
                "message": f"Your order has been accepted by {db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first().shop_name}",
                "order": order.to_dict(),
                "shop_name": db.query(PharmaShopUser).filter(PharmaShopUser.shop_id == shop_id).first().shop_name
            })
    
    except Exception as e:
        await connection_manager.send_to_shop(shop_id, {
            "type": "error",
            "message": f"Failed to accept order: {str(e)}"
        })


async def handle_update_packing(shop_id: str, data: dict, websocket: WebSocket, db: Session):
    # Shop updates order for packing
    try:
        order_id = data.get("order_id")
        rider_name = data.get("rider_name")
        rider_phone = data.get("rider_phone")
        vehicle_number = data.get("vehicle_number")
        vehicle_model = data.get("vehicle_model")
        items = data.get("items")
        item_total = data.get("item_total")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.shop_id != shop_id:
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": "Order not found or unauthorized"
            })
            return
        
        if order.order_status not in ["accepted", "packing"]:
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": f"Cannot update order in {order.order_status} status"
            })
            return
        
        # Update rider info
        order.rider_name = rider_name
        order.rider_phone = rider_phone
        order.vehicle_number = vehicle_number
        order.vehicle_model = vehicle_model
        
        # Update items if provided (for prescription orders)
        if items:
            order.items = items
            if item_total:
                order.item_total = item_total
                order.total_bill_amount = calculate_total_bill(
                    item_total, order.platform_fee, order.delivery_fee, order.taxes
                )
        
        order.order_status = "packing"
        db.commit()
        db.refresh(order)
        
        # Notify shop
        await connection_manager.send_to_shop(shop_id, {
            "type": "order_updated",
            "status": "success",
            "message": "Order updated for packing",
            "order": order.to_dict()
        })
        
        # Notify customer
        if connection_manager.is_customer_connected(order.customer_id):
            await connection_manager.send_to_customer(order.customer_id, {
                "type": "order_status_update",
                "status": "packing",
                "message": "Your order is being packed",
                "order": order.to_dict()
            })
    
    except Exception as e:
        await connection_manager.send_to_shop(shop_id, {
            "type": "error",
            "message": f"Failed to update packing: {str(e)}"
        })


async def handle_update_status(shop_id: str, data: dict, websocket: WebSocket, db: Session):
    # Shop updates order status during delivery
    try:
        order_id = data.get("order_id")
        new_status = data.get("new_status")
        transaction_id = data.get("transaction_id")
        
        if new_status not in ["out_for_delivery", "delivered"]:
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": f"Invalid status: {new_status}"
            })
            return
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order or order.shop_id != shop_id:
            await connection_manager.send_to_shop(shop_id, {
                "type": "error",
                "message": "Order not found or unauthorized"
            })
            return
        
        # Update status
        if new_status == "out_for_delivery":
            if order.order_status != "packing":
                await connection_manager.send_to_shop(shop_id, {
                    "type": "error",
                    "message": "Order must be in packing status"
                })
                return
            order.order_status = "out_for_delivery"
        
        elif new_status == "delivered":
            if order.order_status not in ["packing", "out_for_delivery"]:
                await connection_manager.send_to_shop(shop_id, {
                    "type": "error",
                    "message": "Order must be in packing or out_for_delivery status"
                })
                return
            
            order.order_status = "delivered"
            order.delivered_at = datetime.now()
            
            # Update payment status
            if transaction_id and order.payment_mode == "online":
                order.transaction_id = transaction_id
                order.payment_status = "success"
            elif order.payment_mode == "cod":
                order.payment_status = "success"
        
        db.commit()
        db.refresh(order)
        
        # Notify shop
        await connection_manager.send_to_shop(shop_id, {
            "type": "order_status_updated",
            "status": "success",
            "message": f"Order status updated to {new_status}",
            "order": order.to_dict()
        })
        
        # Notify customer
        if connection_manager.is_customer_connected(order.customer_id):
            await connection_manager.send_to_customer(order.customer_id, {
                "type": "order_status_update",
                "status": new_status,
                "message": f"Your order is {new_status.replace('_', ' ')}",
                "order": order.to_dict()
            })
    
    except Exception as e:
        await connection_manager.send_to_shop(shop_id, {
            "type": "error",
            "message": f"Failed to update status: {str(e)}"
        })


async def handle_get_shop_orders(shop_id: str, data: dict, websocket: WebSocket, db: Session):
    # Send all shop orders to shop (no pagination - instant push)
    try:
        status_filter = data.get("status")
        
        query = db.query(Order).filter(Order.shop_id == shop_id)
        
        if status_filter:
            query = query.filter(Order.order_status == status_filter)
        
        orders = query.all()
        
        await connection_manager.send_to_shop(shop_id, {
            "type": "orders_list",
            "total": len(orders),
            "status_filter": status_filter,
            "data": [order.to_dict() for order in orders]
        })
    except Exception as e:
        await connection_manager.send_to_shop(shop_id, {
            "type": "error",
            "message": f"Failed to fetch orders: {str(e)}"
        })


async def handle_get_broadcast_orders(shop_id: str, data: dict, websocket: WebSocket, db: Session):
    # Get all pending broadcast orders available for this shop to accept (no pagination - instant push)
    try:
        # Fetch ALL broadcast orders without pagination
        broadcast_orders = db.query(Order).filter(Order.order_status == "broadcast").all()
        
        await connection_manager.send_to_shop(shop_id, {
            "type": "broadcast_orders_list",
            "total": len(broadcast_orders),
            "data": [order.to_dict() for order in broadcast_orders]
        })
        
        print(f"📦 Sent {len(broadcast_orders)} broadcast orders to shop {shop_id}")
    except Exception as e:
        await connection_manager.send_to_shop(shop_id, {
            "type": "error",
            "message": f"Failed to fetch broadcast orders: {str(e)}"
        })
