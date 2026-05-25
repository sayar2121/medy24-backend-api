from typing import Dict, Set, List
import json
from fastapi import WebSocket
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    # Custom JSON encoder to handle datetime objects
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ConnectionManager:
    # Manage WebSocket connections for customers and pharmacy shops
    def __init__(self):
        # Active customer connections: customer_id -> WebSocket
        self.active_customers: Dict[str, WebSocket] = {}
        
        # Active pharmacy shop connections: shop_id -> WebSocket
        self.active_shops: Dict[str, WebSocket] = {}
        
        # Track which shops are listening for broadcast orders
        self.broadcast_listeners: Set[str] = set()
    
    # ========================================================================
    # CUSTOMER CONNECTION MANAGEMENT
    # ========================================================================
    
    async def connect_customer(self, customer_id: str, websocket: WebSocket):
        # Register a customer connection and accept the WebSocket
        await websocket.accept()
        self.active_customers[customer_id] = websocket
        print(f"✅ Customer {customer_id} connected. Total customers: {len(self.active_customers)}")
    
    def disconnect_customer(self, customer_id: str):
        # Remove customer from active connections
        if customer_id in self.active_customers:
            del self.active_customers[customer_id]
            print(f"❌ Customer {customer_id} disconnected. Total customers: {len(self.active_customers)}")
    
    async def send_to_customer(self, customer_id: str, message: dict):
        # Send message to specific customer with custom datetime encoding
        if customer_id in self.active_customers:
            try:
                # Use custom encoder to handle datetime objects
                json_str = json.dumps(message, cls=DateTimeEncoder)
                await self.active_customers[customer_id].send_text(json_str)
            except Exception as e:
                print(f"❌ Error sending to customer {customer_id}: {e}")
                self.disconnect_customer(customer_id)
    
    # ========================================================================
    # PHARMACY SHOP CONNECTION MANAGEMENT
    # ========================================================================
    
    async def connect_shop(self, shop_id: str, websocket: WebSocket):
        # Register a pharmacy shop connection and accept the WebSocket
        await websocket.accept()
        self.active_shops[shop_id] = websocket
        self.broadcast_listeners.add(shop_id)
        print(f"✅ Pharmacy Shop {shop_id} connected. Total shops: {len(self.active_shops)}")
    
    def disconnect_shop(self, shop_id: str):
        # Remove shop from active connections and listeners
        if shop_id in self.active_shops:
            del self.active_shops[shop_id]
            self.broadcast_listeners.discard(shop_id)
            print(f"❌ Pharmacy Shop {shop_id} disconnected. Total shops: {len(self.active_shops)}")
    
    async def send_to_shop(self, shop_id: str, message: dict):
        # Send message to specific pharmacy shop with custom datetime encoding
        if shop_id in self.active_shops:
            try:
                # Use custom encoder to handle datetime objects
                json_str = json.dumps(message, cls=DateTimeEncoder)
                await self.active_shops[shop_id].send_text(json_str)
            except Exception as e:
                print(f"❌ Error sending to shop {shop_id}: {e}")
                self.disconnect_shop(shop_id)
    
    # ========================================================================
    # BROADCAST MANAGEMENT
    # ========================================================================
    
    async def broadcast_to_all_shops(self, message: dict, exclude_shop_id: str = None):
        # Send message to all active pharmacy shops with custom datetime encoding
        disconnected_shops = []
        
        # Pre-encode message to JSON for efficient broadcasting
        json_str = json.dumps(message, cls=DateTimeEncoder)
        
        for shop_id in self.broadcast_listeners:
            if exclude_shop_id and shop_id == exclude_shop_id:
                continue
            
            if shop_id in self.active_shops:
                try:
                    await self.active_shops[shop_id].send_text(json_str)
                except Exception as e:
                    print(f"❌ Error broadcasting to shop {shop_id}: {e}")
                    disconnected_shops.append(shop_id)
        
        # Clean up disconnected shops
        for shop_id in disconnected_shops:
            self.disconnect_shop(shop_id)
    
    async def broadcast_to_listening_shops(self, message: dict):
        # Send order availability to all shops listening to broadcast channel
        await self.broadcast_to_all_shops(message)
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def is_customer_connected(self, customer_id: str) -> bool:
        # Check if customer is currently connected
        return customer_id in self.active_customers
    
    def is_shop_connected(self, shop_id: str) -> bool:
        # Check if pharmacy shop is currently connected
        return shop_id in self.active_shops
    
    def get_connected_shops_count(self) -> int:
        # Get total number of connected pharmacy shops
        return len(self.active_shops)
    
    def get_connected_customers_count(self) -> int:
        # Get total number of connected customers
        return len(self.active_customers)
    
    async def send_to_broadcast_listeners(self, message: dict):
        # Alias for broadcast_to_listening_shops
        await self.broadcast_to_listening_shops(message)


# Global connection manager instance
connection_manager = ConnectionManager()
