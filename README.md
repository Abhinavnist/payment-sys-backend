# Payment System

A secure, reliable best payment tracking system for merchants to integrate UPI and bank transfers with their applications.

## Features

- 🔒 Secure API for merchant integration
- 💰 UPI and bank transfer payment processing
- 📱 Payment link and UPI URL generation
- 🔍 UTR verification system
- 🛡️ IP whitelisting for enhanced security
- 📊 Comprehensive analytics and reporting
- ⚙️ Webhook system for payment notifications
- 🔄 Rate limiting for API protection
- 📝 CSV export functionality

## Architecture

### Backend

- FastAPI framework with Python
- PostgreSQL database (direct access with psycopg2)
- Redis for rate limiting
- JWT authentication for admin users
- API key authentication for merchants

### Frontend (Coming Soon)

- Next.js for both Admin and Merchant panels
- Tailwind CSS for styling
- React Query for data fetching

## Getting Started

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.11+ (if running without Docker)
- PostgreSQL 13+ (if running without Docker)
- Redis 6+ (if running without Docker)

### Setup with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/payment-system.git
   cd payment-system
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. The API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/api/docs`

### Setup without Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/payment-system.git
   cd payment-system/backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Setup PostgreSQL:
   - Create a database named `payment_system`
   - Run the SQL script in `sql/init.sql`

5. Create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Run the application:
   ```bash
   ./run.sh  # On Windows: python -m uvicorn app.main:app --reload
   ```

## API Documentation

After starting the application, visit `http://localhost:8000/api/docs` for the interactive API documentation.

### Main API Endpoints

- `/api/v1/auth/*`: Authentication endpoints
- `/api/v1/admin/*`: Admin management endpoints
- `/api/v1/payments/*`: Payment processing endpoints
- `/api/v1/merchants/*`: Merchant management endpoints
- `/api/v1/reports/*`: Reporting and analytics endpoints

## Security Features

- JWT authentication for admin access
- API key authentication for merchants
- IP whitelisting for merchant API access
- Rate limiting to prevent abuse
- Webhook signature verification
- Password hashing with bcrypt

## Development

### Backend Structure

```
backend/
├── app/
│   ├── api/                 # API endpoints
│   ├── core/                # Core configuration
│   ├── db/                  # Database connection and queries
│   ├── middlewares/         # Custom middlewares
│   ├── models/              # Data models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── utils/               # Utility functions
├── sql/                     # SQL scripts
├── uploads/                 # Uploaded files
├── .env.example             # Environment variables template
├── Dockerfile               # Dockerfile for the backend
└── requirements.txt         # Python dependencies
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.