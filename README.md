# ZhanCare Backend

Backend API for ZhanCare - a comprehensive healthcare platform connecting patients with doctors and nurses for telemedicine consultations and home visits.

## Features

- **Authentication**: JWT-based authentication with multi-device session management
- **User Management**: Support for patients, doctors, nurses, and administrators
- **Video Consultations**: Real-time video consultations between patients and doctors
- **Home Appointments**: Schedule and manage home visits by nurses
- **AI Recommendations**: AI-powered doctor/specialty recommendations based on symptoms
- **Payment Integration**: Kaspi payment processing for appointments
- **Real-time Updates**: WebSocket support for live availability status and notifications
- **Multi-clinic Support**: Manage multiple clinics with separate admin access
- **Reports & Analytics**: Comprehensive reporting for administrators

## Tech Stack

- **Framework**: Django 5.x + Django REST Framework
- **Database**: PostgreSQL with PostGIS extension
- **Authentication**: djangorestframework-simplejwt
- **WebSocket**: Django Channels + Daphne (ASGI)
- **Task Queue**: APScheduler
- **API Documentation**: drf-yasg / drf-spectacular

## Project Structure

```
experimental_admin_back/
├── mchs_back/              # Project settings
├── common/                 # Users, authentication, sessions
├── appointments/           # Home appointment management
├── consultations/          # Video consultation management
├── payments/               # Kaspi payment integration
├── clinics/                # Clinic management
├── clinical_protocols/     # Medical protocols
├── questionnaire/          # Patient questionnaires
├── ai_game/                # AI features
└── telegram_bot/           # Telegram bot integration
```

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL with PostGIS
- Redis (for Channels)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd experimental_admin_back
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

   Or with ASGI (for WebSocket support):
   ```bash
   daphne -b 0.0.0.0 -p 8000 mchs_back.asgi:application
   ```

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register/` | POST | Register new user |
| `/api/v1/auth/login/` | POST | Login with JWT tokens |
| `/api/v1/auth/logout/` | POST | Logout and revoke session |
| `/api/v1/user-profile/auth/refresh/` | POST | Refresh access token |

### Sessions
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sessions/` | GET | List active sessions |
| `/api/v1/sessions/{id}/revoke/` | POST | Revoke specific session |
| `/api/v1/sessions/revoke-all-others/` | POST | Revoke all other sessions |

### Staff Management (Admin)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/staff/` | GET | List all staff |
| `/api/v1/staff/` | POST | Create staff member |
| `/api/v1/staff/{id}/` | PATCH | Update staff member |

### Patients (Admin)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/patients/` | GET | List patients |
| `/api/v1/patients/` | POST | Create patient |

### Reports (Admin)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reports/` | GET | Get analytics reports |

### User Profile
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/user-profile/profile/` | GET | Get current user profile |
| `/api/v1/user-profile/profile/` | PATCH | Update current user profile |

## Authentication

The API uses JWT (JSON Web Tokens) for authentication:

- **Access Token**: Valid for 15 minutes
- **Refresh Token**: Valid for 7 days

Include the token in requests:
```
Authorization: Bearer <access_token>
```

## Environment Variables

```env
# Database
DATABASE_URL=postgres://user:password@localhost:5432/zhancare

# Django
SECRET_KEY=your-secret-key
DEBUG=True

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Redis (for Channels)
REDIS_URL=redis://localhost:6379
```

## Running Tests

```bash
python manage.py test
```

## API Documentation

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## License

Proprietary - All rights reserved

## Contact

ZhanCare Team - support@zhancare.app
