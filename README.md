# In The Event Of My Death

A zero-knowledge time-locked secret delivery service. Create encrypted messages that are only accessible after a specified date and time.

## Environment Variables

### Frontend Configuration

Create a `.env` file in the `frontend/` directory based on `.env.example`:

```bash
# API Configuration
VITE_API_URL=http://localhost:8000

# Base URL for shareable links
# In production, set this to your domain (e.g., https://ieomd.com)
VITE_BASE_URL=http://localhost:5173
```

**Variables:**
- `VITE_API_URL`: URL of the backend API server
- `VITE_BASE_URL`: Base URL used for generating shareable links. In production, this should be set to your production domain (e.g., `https://ieomd.com`)

### Backend Configuration

Create a `.env` file in the `backend/` directory based on `.env.example`:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./secrets.db

# CORS Configuration
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

**Variables:**
- `DATABASE_URL`: Database connection string. Default is SQLite for development. For production, consider PostgreSQL (e.g., `postgresql://user:password@host:port/dbname`)
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins. In production, set this to your frontend URL (e.g., `https://ieomd.com`)

## Development Setup

1. Install dependencies:
   ```bash
   make install
   ```

2. Copy environment files:
   ```bash
   cp frontend/.env.example frontend/.env
   cp backend/.env.example backend/.env
   ```

3. Run database migrations:
   ```bash
   make migrate
   ```

4. Start development servers:
   ```bash
   make dev
   ```

## Production Deployment

For production deployment on `ieomd.com`:

1. Set frontend environment variables:
   ```bash
   VITE_API_URL=https://api.ieomd.com
   VITE_BASE_URL=https://ieomd.com
   ```

2. Set backend environment variables:
   ```bash
   DATABASE_URL=postgresql://user:password@host:port/dbname
   CORS_ORIGINS=https://ieomd.com
   ```

3. Build the frontend:
   ```bash
   cd frontend && npm run build
   ```

4. Deploy the backend with production settings.

## Available Commands

See the `Makefile` for all available commands:

```bash
make help
```

## Security

This service uses client-side encryption (AES-256-GCM). Encryption keys are never sent to the server and are only included in URL fragments (which are not transmitted to the server per RFC 3986).

For more details, see [docs/design.md](docs/design.md).
