# Medy24 Backend

Backend system for Patho Lab management, including authentication, document uploads, and profile management.

## Setup Instructions

### 1. Create a Virtual Environment
```bash
python -m venv venv
```

### 2. Activate the Virtual Environment
- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```
- **On Windows:**
  ```bash
  venv\Scripts\activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Firebase Configuration (Required for Phone Authentication)

#### Step A: Download Firebase Service Account Key
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (Medy24)
3. Click the gear icon → **Project Settings**
4. Go to **Service Accounts** tab
5. Click **Generate New Private Key**
6. Save the JSON file as `secrets/firebase-adminsdk-medy24.json`

#### Step B: Enable Phone Authentication in Firebase
1. Go to **Build** → **Authentication** → **Get Started**
2. Click **Phone** and enable it
3. Add your phone numbers to the test list (for testing)

### 5. Configure Environment Variables
Copy values from `.env.example` and update `.env`:
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/medy24_db
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=medy24_db
DB_HOST=localhost
DB_PORT=5432

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=secrets/firebase-adminsdk-medy24.json

# JWT Configuration for backend tokens
JWT_SECRET=your-strong-random-secret-key-here
JWT_ALGORITHM=HS256
```

**To generate a strong JWT_SECRET:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 6. Start the Backend Server
```bash
python main.py
```
The server will start on `http://0.0.0.0:8000`. You can access the API documentation at `http://localhost:8000/docs`.

## Customer Authentication API

### Phone Authentication Flow

#### 1. Check if Phone Number is Registered
```bash
POST /customers/check-phone
Body: {
  "phone_number": "+919876543210"
}
Response: {
  "message": "Phone check completed",
  "phone_number": "+919876543210",
  "exists": false,
  "user_id": null
}
```

#### 2. Send OTP (Triggered from Frontend)
The OTP is sent by Firebase from the client-side using Firebase Phone Authentication.

#### 3. Verify OTP and Register/Login
```bash
POST /customers/verify-otp
Body (Multipart Form):
{
  "token": "firebase_id_token_here",
  "phone_number": "+919876543210",
  "full_name": "John Doe",           # Required for new users
  "email": "john@example.com",       # Optional
  "alternative_phone_no": "+919876543211",  # Optional
  "saved_addresses": [               # Optional (JSON list)
    {
      "address": "123 Main St, City",
      "type": "home"
    }
  ],
  "profile_photo": <file>            # Optional
}
Response:
{
  "message": "Registration successful",
  "status": "signup",
  "user": {
    "customer_id": "CUST-1715708933",
    "phone_number": "+919876543210",
    "full_name": "John Doe",
    "email": "john@example.com",
    "alternative_phone_no": "+919876543211",
    "profile_photo": "/uploads/auth/CUST-1715708933/profile_photo.jpg",
    "saved_addresses": [...],
    "created_at": "2026-05-14T...",
    "updated_at": "2026-05-14T..."
  },
  "backend_token": "eyJhbGc..."  # Use this for authenticated requests
}
```

#### 4. Get Customer Profile
```bash
GET /customers/profile/{customer_id}
Response: {
  "message": "Profile retrieved successfully",
  "user": { ... }
}
```

#### 5. Update Customer Profile
```bash
PUT /customers/profile/{customer_id}
Body (Multipart Form):
{
  "full_name": "Jane Doe",           # Optional
  "email": "jane@example.com",       # Optional
  "alternative_phone_no": "+919876543212",  # Optional
  "profile_photo": <file>            # Optional
}
```

#### 6. Add Saved Address
```bash
POST /customers/addresses/{customer_id}
Body (JSON):
{
  "address": "456 Oak St, City",
  "address_type": "office"
}
Response: {
  "message": "Address added successfully",
  "address": {
    "id": 1,
    "address": "456 Oak St, City",
    "type": "office",
    "created_at": "2026-05-14T..."
  },
  "user": { ... }
}
```

#### 7. Delete Saved Address
```bash
DELETE /customers/addresses/{customer_id}/{address_id}
Response: {
  "message": "Address deleted successfully",
  "user": { ... }
}
```

## Medicine Management API

### Bulk Upload Medicines from CSV (Asynchronous)

#### 1. Upload CSV File
```bash
POST /medicines/create
Body: Form Data with CSV file
Content-Type: multipart/form-data

file: medicines.csv

Response:
{
  "status": "queued",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "CSV file 'medicines.csv' uploaded successfully. Processing started in background.",
  "check_status_url": "/medicines/import-status/550e8400-e29b-41d4-a716-446655440000"
}
```

**CSV File Format (Required Columns):**
```csv
medicine_name,medicine_category,medicine_quantity,mrp,discount_percent,medicine_description,medicine_composition,precautions,prescription_required
Paracetamol,Pain Relief,10 tablets,150,10,For fever and pain,Paracetamol 500mg,Avoid if allergic,false
Aspirin,Pain Relief,20 tablets,200,5,For headache,Aspirin 100mg,"Do not take with alcohol",true
Amoxicillin,Antibiotics,15 capsules,450,,Antibiotic medicine,Amoxicillin 500mg,Take with food,true
```

**Required Columns:**
- `medicine_name` - Name of the medicine
- `medicine_category` - Category/Type
- `medicine_quantity` - Quantity (e.g., "10 tablets", "15 capsules")
- `mrp` - Maximum Retail Price (numeric)

**Optional Columns:**
- `discount_percent` - Discount percentage (numeric)
- `medicine_description` - Description
- `medicine_composition` - Composition details
- `precautions` - Precautions (JSON array or comma-separated values)
- `prescription_required` - "true" or "false" (default: "false")

#### 2. Check Import Status
```bash
GET /medicines/import-status/{job_id}

Example:
GET /medicines/import-status/550e8400-e29b-41d4-a716-446655440000

Response (While Processing):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "filename": "medicines.csv",
  "created_at": "2026-05-23T10:30:45.123456",
  "started_at": "2026-05-23T10:30:46.234567",
  "completed_at": null
}

Response (After Completion):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "medicines.csv",
  "created_at": "2026-05-23T10:30:45.123456",
  "started_at": "2026-05-23T10:30:46.234567",
  "completed_at": "2026-05-23T10:45:12.567890",
  "results": {
    "total_rows": 100000,
    "successful": 99800,
    "failed": 200,
    "created_medicines_count": 99800,
    "errors": [
      "Row 15: Missing required field 'mrp'",
      "Row 42: Medicine 'Aspirin' in category 'Pain Relief' already exists"
    ],
    "sample_created_medicines": [
      {"medicine_id": "MED-PARA-123", "medicine_name": "Paracetamol"},
      {"medicine_id": "MED-ASPI-456", "medicine_name": "Aspirin"},
      ...
    ]
  }
}
```

### Other Medicine Endpoints

#### Search Medicines
```bash
GET /medicines/search?search_term=paracetamol&category=Pain%20Relief&price_range=0-100&page=1&limit=20

Query Parameters:
- search_term: Search by medicine name (optional)
- category: Filter by category (optional)
- price_range: Filter by price ranges - can use multiple (optional)
  - "0-100": 0 to 100
  - "100-500": 100 to 500
  - "500-1000": 500 to 1000
  - "1000-5000": 1000 to 5000
  - "5000+": Above 5000
- page: Page number (default: 1)
- limit: Results per page (default: 20, max: 100)

Response:
{
  "total": 150,
  "page": 1,
  "limit": 20,
  "count": 20,
  "data": [...]
}
```

#### Get All Medicines
```bash
GET /medicines/get-all?page=1&limit=20

Response:
{
  "total": 100000,
  "page": 1,
  "limit": 20,
  "data": [...]
}
```

#### Get Medicine by ID
```bash
GET /medicines/get-by/{medicine_id}

Response:
{
  "medicine_id": "MED-PARA-123",
  "medicine_name": "Paracetamol",
  "medicine_category": "Pain Relief",
  "medicine_quantity": "10 tablets",
  "mrp": 150.0,
  "discount_percent": 10.0,
  "final_selling_price": 135.0,
  "prescription_required": "false",
  ...
}
```

#### Update Medicine
```bash
PUT /medicines/update-by/{medicine_id}
Body: Form Data (all fields optional)

- medicine_name
- medicine_category
- medicine_quantity
- mrp
- discount_percent
- medicine_description
- medicine_composition
- precautions (JSON string)
- prescription_required ("true" or "false")
- medicine_photo (file upload)
```

#### Delete Medicines
```bash
DELETE /medicines/delete-by-ids
Body: {
  "medicine_ids": ["MED-PARA-123", "MED-ASPI-456"]
}
```


