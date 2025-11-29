# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email security concerns to the project maintainer
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Response Time**: We aim to acknowledge reports within 48 hours
- **Resolution**: Critical vulnerabilities will be prioritized
- **Credit**: Reporters will be credited in release notes (unless they prefer anonymity)

## Security Best Practices for Deployment

### Environment Variables

Always set these in production:

```bash
# Generate secure values
FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Enable secure cookies (requires HTTPS)
SESSION_COOKIE_SECURE=true

# Disable debug mode
FLASK_DEBUG=false
```

### HTTPS

Always run behind HTTPS in production. The OAuth flow requires HTTPS for the callback URL.

### Database

- Keep the SQLite database file outside the web root
- Set appropriate file permissions (600 or 640)
- Back up the database regularly
- The `ENCRYPTION_KEY` is required to read encrypted OAuth tokens

### QuickBooks OAuth Tokens

- Tokens are encrypted at rest using Fernet symmetric encryption
- Never share or commit your `.env` file
- Rotate your `ENCRYPTION_KEY` periodically (requires re-authentication)

## Security Features

- **CSRF Protection**: Flask-WTF CSRFProtect on all forms
- **Session Security**: HttpOnly, SameSite=Lax cookies
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **Input Validation**: All QuickBooks IDs validated with regex
- **SQL Injection Prevention**: SQLAlchemy ORM throughout
- **XSS Prevention**: Jinja2 auto-escaping enabled
- **Token Encryption**: OAuth tokens encrypted at rest with Fernet
