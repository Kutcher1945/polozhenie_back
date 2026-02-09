# Backend API

Django REST Framework backend with PostgreSQL and PostGIS.

## Prerequisites

- Python 3.10+
- PostgreSQL with PostGIS extension
- pip

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd experimental_admin_back
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure database**

Create a PostgreSQL database with PostGIS:
```sql
CREATE DATABASE your_database_name;
\c your_database_name
CREATE EXTENSION postgis;
```

Update database settings in `mchs_back/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'your_database_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
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

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
- Admin Panel: `http://localhost:8000/admin/`

## Environment Variables

Create a `.env` file for sensitive settings:
```
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
MISTRAL_API_KEY=your-mistral-api-key
```

## Common Commands

```bash
# Run migrations
python manage.py migrate

# Create migrations after model changes
python manage.py makemigrations

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Start development server
python manage.py runserver

# Access Django shell
python manage.py shell
```

## Production Deployment

For production, ensure:
- `DEBUG = False`
- Configure proper database credentials
- Set up static file serving
- Use a production WSGI server (gunicorn, uwsgi)
- Configure ALLOWED_HOSTS
- Set strong SECRET_KEY

## License

All rights reserved.
