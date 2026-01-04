# JournalSmart for QuickBooks Online

Automated journal entry reclassification for QuickBooks Online. Create pattern-based rules that automatically find and fix journal entries. **Set it once, run it forever.**

## Features

- **Pattern-based rules** - Match journal descriptions with text or regex patterns
- **Bulk reclassification** - Update multiple entries at once
- **Reusable mappings** - Save rules, apply them repeatedly
- **Multi-company support** - Connect multiple QBO companies
- **Full history** - Audit trail of all changes
- **Encrypted storage** - OAuth tokens encrypted at rest
- **Self-hosted** - Your data stays on your server

## Quick Start

### Prerequisites

- Python 3.11+
- QuickBooks Online account
- [Intuit Developer](https://developer.intuit.com/) app credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/fbsobreira/JournalSmart.git
cd JournalSmart

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your QuickBooks credentials
```

### Configuration

Edit `.env` with your settings:

```bash
# Required - Flask
FLASK_SECRET_KEY=your-secret-key-here  # Generate: python -c "import secrets; print(secrets.token_hex(32))"

# Required - QuickBooks OAuth (from developer.intuit.com)
QBO_CLIENT_ID=your-client-id
QBO_CLIENT_SECRET=your-client-secret
QBO_REDIRECT_URI=https://localhost:443/callback
QBO_ENVIRONMENT=sandbox  # or 'production'

# Required - Token Encryption
ENCRYPTION_KEY=your-fernet-key  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Optional
APP_PASSWORD=              # Protect access with a password
DATABASE_PATH=./data/journalsmart.db
LOG_LEVEL=INFO
```

### Running

```bash
# Development
python run.py

# Production (with SSL)
SSL_CERT=cert.pem SSL_KEY=key.pem python run.py
```

Open `https://localhost:443` in your browser.

## QuickBooks App Setup

1. Go to [Intuit Developer Portal](https://developer.intuit.com/)
2. Create a new app (or use existing)
3. In **Keys & credentials**:
   - Copy **Client ID** and **Client Secret**
   - Add redirect URI: `https://localhost:443/callback` (or your domain)
4. In **Scopes**, enable **Accounting**
5. Add credentials to your `.env` file

## Usage

1. **Connect to QuickBooks** - Click "Connect to QuickBooks" and authorize
2. **Create Mappings** - Define pattern rules (e.g., "Office Supplies" -> reclassify to Account X)
3. **View Journals** - Browse journal entries, filter by date/account
4. **Apply Mappings** - Select entries and apply your rules
5. **Review History** - See all changes in the audit log

## Project Structure

```
JournalSmart/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   ├── templates/       # HTML templates
│   ├── static/          # CSS, JS, images
│   └── utils/           # Helpers
├── data/                # SQLite database (gitignored)
├── config.py            # Configuration
├── run.py               # Entry point
└── requirements.txt     # Dependencies
```

## Security

- **OAuth tokens** encrypted at rest using Fernet symmetric encryption
- **CSRF protection** on all forms via Flask-WTF
- **Security headers** (CSP, X-Frame-Options, etc.)
- **Session security** with HttpOnly, SameSite cookies
- **Input validation** on all user inputs

See [SECURITY.md](SECURITY.md) for security best practices and vulnerability reporting.

## Data Privacy

This is **self-hosted software**. Your data stays on your server:

- QuickBooks OAuth tokens stored in local SQLite database (encrypted)
- Journal data fetched from QuickBooks API on-demand
- No telemetry or analytics sent anywhere
- No external services except QuickBooks API

**You are the data controller.** The developers of this software never see your data.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

This means:
- You can use, modify, and distribute this software freely
- If you modify and host it as a service, you must open-source your changes
- No warranty is provided

See [LICENSE](LICENSE) for the full text.

## Disclaimer

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This software interacts with QuickBooks Online via their official API. It is not affiliated with, endorsed by, or sponsored by Intuit Inc. QuickBooks is a registered trademark of Intuit Inc.

