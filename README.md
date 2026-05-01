# Desperate Job Search Bot

A Telegram bot that automatically scans job platforms, generates tailored cover letters using Claude AI, and notifies you of new vacancies.

## Architecture

```
jobsearch_bot/
├── bot.py                      # Entry point, registers handlers
├── config.py                   # Settings from .env
├── handlers/
│   ├── setup.py                # /start wizard (5-step conversation)
│   ├── jobs.py                 # /status /pause /resume /results
│   └── states.py               # ConversationHandler state IDs
├── platforms/
│   ├── base.py                 # Abstract adapter interface
│   ├── hh.py                   # HH.ru — official REST API ✅
│   ├── djinni.py               # Djinni.co — httpx + BeautifulSoup ✅
│   ├── linkedin.py             # LinkedIn — Playwright 🔧
│   ├── glassdoor.py            # Glassdoor — Playwright 🔧
│   └── telegram_channels.py    # Telegram — Bot API / Telethon 🔧
├── services/
│   ├── agent.py                # Background scan loop + orchestration
│   ├── cover_letter.py         # Claude AI cover letter generation
│   └── cv_parser.py            # PDF → plain text (pdfplumber / pypdf)
└── utils/
    ├── keyboards.py            # InlineKeyboardMarkup builders
    └── storage.py              # SQLite (user configs + found jobs)
```

## Quick Start

### 1. Clone & install
```bash
cd jobsearch_bot
pip install -r requirements.txt
playwright install chromium    # for LinkedIn & Glassdoor
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env — at minimum set TELEGRAM_TOKEN and ANTHROPIC_API_KEY
```

### 3. Create Telegram bot
1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the token → `TELEGRAM_TOKEN` in `.env`

### 4. Get Anthropic key
[console.anthropic.com](https://console.anthropic.com) → API Keys → Copy → `ANTHROPIC_API_KEY` in `.env`

### 5. Run
```bash
python bot.py
```

---

## Platform Support

| Platform  | Search | Apply | Method |
|-----------|--------|-------|--------|
| HH.ru     | ✅ | ✅ (with OAuth token) | Official REST API |
| Djinni    | ✅ | 🔧 stub | httpx + BeautifulSoup |
| LinkedIn  | ✅ | 🔧 stub | Playwright (headless Chrome) |
| Glassdoor | ✅ | 🔧 stub | Playwright (headless Chrome) |
| Telegram  | 🔧 (needs bot as admin) | N/A | Bot API / Telethon |

**Legend:** ✅ implemented · 🔧 partial / requires extra setup

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Run the setup wizard |
| `/status` | Show agent status and stats |
| `/results` | List recently found jobs |
| `/pause` | Pause the scan loop |
| `/resume` | Resume scanning |
| `/help` | Show command list |
| `/cancel` | Abort current setup |

---

## HH.ru OAuth (for apply)

1. Register app at [dev.hh.ru](https://dev.hh.ru)
2. Get `HH_CLIENT_ID` + `HH_CLIENT_SECRET`
3. Obtain user OAuth token, set as `HH_ACCESS_TOKEN`

## LinkedIn cookies (for search)

1. Log into LinkedIn in Chrome
2. Use a cookie export extension (e.g. "EditThisCookie")  
3. Save JSON to `storage/linkedin_cookies.json`

## Telegram channel scanning

**Option A** (easiest): Add your bot as admin to a private job channel.  
**Option B** (full access): Use [Telethon](https://docs.telethon.dev) with a user account — uncomment the dependency in `requirements.txt` and extend `telegram_channels.py`.

---

## Extending

Add a new platform by creating `platforms/yourplatform.py`:

```python
from platforms.base import BasePlatformAdapter

class YourAdapter(BasePlatformAdapter):
    async def search(self, position: str) -> list[dict]:
        ...   # return list of job dicts
    
    async def apply(self, job: dict, cover_letter: str) -> bool:
        ...   # return True on success
```

Then register it in `services/agent.py`:
```python
ADAPTER_MAP = {
    ...
    "YourPlatform": YourAdapter,
}
```
