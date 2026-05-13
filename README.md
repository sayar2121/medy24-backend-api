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


