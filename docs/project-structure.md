video-ai-learning-platform/
│
├── .env.example                           ⚠️ UPDATE (add new keys)
├── .gitignore                             🆕 NEW
├── requirements.txt                       ⚠️ UPDATE (add packages)
├── README.md                              🆕 NEW
│
├── backend/
│   ├── app.py                             ❌ REPLACE
│   ├── config.py                          ❌ REPLACE
│   │
│   ├── database/
│   │   ├── __init__.py                    🆕 NEW
│   │   ├── firebase_manager.py            🆕 NEW
│   │   └── cache_manager.py               🆕 NEW
│   │
│   ├── video_processing/
│   │   ├── __init__.py                    🆕 NEW
│   │   ├── youtube_processor.py           ❌ REPLACE
│   │   ├── facebook_processor.py          ❌ REPLACE
│   │   ├── transcript_processor.py        ❌ REPLACE
│   │   └── video_downloader.py            ⚠️ UPDATE
│   │
│   ├── ai_models/
│   │   ├── __init__.py                    🆕 NEW
│   │   ├── ai_orchestrator.py             ❌ REPLACE
│   │   ├── gemini_handler.py              🆕 NEW
│   │   ├── openrouter_handler.py          🆕 NEW
│   │   └── model_configs.py               🆕 NEW
│   │
│   ├── routes/
│   │   ├── __init__.py                    🆕 NEW
│   │   ├── video_routes.py                ❌ REPLACE
│   │   ├── ai_routes.py                   ❌ REPLACE
│   │   ├── chat_routes.py                 ⚠️ UPDATE
│   │   └── health_routes.py               🆕 NEW
│   │
│   ├── utils/
│   │   ├── __init__.py                    🆕 NEW
│   │   ├── helpers.py                     ✅ KEEP
│   │   ├── logger.py                      ✅ KEEP
│   │   ├── sync_manager.py                🆕 NEW
│   │   └── chunking_manager.py            🆕 NEW
│   │
│   └── middleware/
│       ├── __init__.py                    🆕 NEW
│       ├── rate_limiter.py                🆕 NEW
│       └── error_handler.py               🆕 NEW
│
├── frontend/
│   ├── index.html                         🆕 NEW
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css                   🆕 NEW
│   │   │   ├── video-player.css           🆕 NEW
│   │   │   └── ai-chat.css                🆕 NEW
│   │   │
│   │   └── js/
│   │       ├── app.js                     🆕 NEW
│   │       ├── video-player.js            🆕 NEW
│   │       ├── ai-chat.js                 🆕 NEW
│   │       ├── sync-manager.js            🆕 NEW
│   │       ├── model-selector.js          🆕 NEW
│   │       └── utils.js                   🆕 NEW
│   │
│   └── components/
│       ├── video-player.html              🆕 NEW
│       └── ai-interface.html              🆕 NEW
│
├── logs/
│   └── .gitkeep                           🆕 NEW
│
├── temp_videos/
│   └── .gitkeep                           🆕 NEW
│
└── docs/
    ├── API.md                             🆕 NEW
    ├── SETUP.md                           🆕 NEW
    └── FEATURES.md                        🆕 NEW
