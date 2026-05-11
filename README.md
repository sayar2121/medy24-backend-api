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

### 4. Configure Environment Variables
Edit the `.env` file with your PostgreSQL credentials:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/medy24_db
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=medy24_db
DB_HOST=localhost
DB_PORT=5432
```

### 5. Start the Backend Server
```bash
python main.py
```
The server will start on `http://0.0.0.0:8000`. You can access the API documentation at `http://localhost:8000/docs`.

## API Endpoints

### Patho Lab Authentication
- `POST /auth/patho-lab/signup`: Register a new lab (form-data).
- `POST /auth/patho-lab/login`: Login with email and password (form-data).
- `GET /auth/patho-lab/{lab_id}`: Get lab details by Lab ID.
- `PUT /auth/patho-lab/{lab_id}`: Update lab details (form-data).

### General
- `GET /health`: System health check.
