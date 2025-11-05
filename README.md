# Local Business Intelligence Bot

An AI-powered platform that helps small restaurants understand and improve their online reputation through automated review analysis and intelligent business recommendations.

## Features

- **Dual-Agent AI Architecture**: Fast review classification (GPT-5 Nano) + strategic business advice (Claude 3.5 Haiku)
- **Multi-Language Support**: German, English, Turkish, Arabic interface with automatic review language detection
- **Real-Time Analytics**: Automated daily review processing with 4-hour dashboard updates
- **Smart Alerts**: Critical review detection with multi-channel notifications (email, SMS, in-app)
- **Cost Management**: AI usage tracking with budget limits and warnings
- **Multi-Tenant Support**: Role-based access control for restaurant chains
- **GDPR Compliant**: Built-in data protection and privacy controls

## Architecture

### Backend Structure
```
backend/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
│
├── ai/                        # AI service layer
│   ├── base.py               # Abstract base classes and protocols
│   ├── gpt5_classifier.py    # GPT-5 Nano review classification
│   ├── claude_advisor.py     # Claude Haiku business advisor
│   ├── language_detector.py  # Language detection service
│   └── cost_tracker.py       # AI usage cost tracking
│
├── db/                        # Database layer
│   ├── database.py           # Connection management
│   ├── models.py             # SQLAlchemy models
│   ├── schemas.py            # Pydantic schemas
│   └── repositories/         # Repository pattern
│       ├── base.py
│       ├── business.py
│       └── review.py
│
├── services/                  # Business logic layer
│   ├── review/
│   │   └── processor.py      # Review processing pipeline
│   ├── analytics/
│   │   └── calculator.py     # Analytics and metrics
│   └── notification/
│       └── alert_service.py  # Real-time alerts
│
├── routes/                    # API endpoints
│   └── health.py             # Health check endpoints
│
├── external/                  # External API integrations
│   ├── base_client.py        # Base HTTP client
│   └── google_places.py      # Google Places API
│
└── tests/                     # Test suite
    ├── conftest.py           # Pytest configuration
    ├── unit/                 # Unit tests
    ├── integration/          # Integration tests
    └── fixtures/             # Test data
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- API Keys:
  - OpenAI API key (for GPT-5 Nano)
  - Anthropic API key (for Claude Haiku)
  - Google Places API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd local-business-intelligence-bot
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

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Run database migrations
   alembic upgrade head
   ```

6. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running the Application

1. **Start the development server**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

## Development

### Code Quality Standards

This project follows strict code quality standards:

- **PEP 8 Compliance**: All Python code follows PEP 8 style guidelines
- **Type Hints**: Full type annotation coverage
- **File Size Limits**: Maximum 500 lines per file, 200 lines per class, 50 lines per function
- **Test Coverage**: Minimum 80% code coverage
- **Documentation**: Google-style docstrings for all classes and functions

### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality:

- **Black**: Code formatting
- **Flake8**: Linting and style checking
- **MyPy**: Static type checking
- **isort**: Import sorting
- **File size checks**: Enforce size limits

### Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test categories
pytest backend/tests/unit/          # Unit tests only
pytest backend/tests/integration/   # Integration tests only
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/businessbot
REDIS_URL=redis://localhost:6379/0

# AI Services
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Google Places
GOOGLE_PLACES_API_KEY=your-google-places-api-key

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS (optional)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-number
```

## API Documentation

### Health Endpoints

- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed health with database check
- `GET /api/health/readiness` - Kubernetes readiness probe
- `GET /api/health/liveness` - Kubernetes liveness probe

### Core Features (To be implemented)

- `POST /api/businesses` - Create business
- `GET /api/businesses/{id}` - Get business details
- `POST /api/reviews/classify` - Classify reviews
- `POST /api/chat/{business_id}` - Chat with AI advisor
- `GET /api/analytics/{business_id}` - Get dashboard data
- `POST /api/reports/weekly` - Generate weekly report

## Deployment

### Docker

```bash
# Build image
docker build -t business-bot .

# Run container
docker run -p 8000:8000 --env-file .env business-bot
```

### Production Considerations

- Use PostgreSQL with connection pooling
- Set up Redis for caching and session storage
- Configure proper logging and monitoring
- Set up SSL/TLS certificates
- Use environment-specific configuration
- Implement proper backup strategies

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code quality standards
4. Run tests and ensure they pass
5. Run pre-commit hooks (`pre-commit run --all-files`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review the API documentation at `/docs` when running the server