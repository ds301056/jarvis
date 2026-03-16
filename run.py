"""Start Jarvis server with optional SSL for phone voice testing."""

import uvicorn
import config

if __name__ == "__main__":
    kwargs = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
    }

    if config.SSL_ENABLED:
        kwargs["ssl_certfile"] = config.SSL_CERTFILE
        kwargs["ssl_keyfile"] = config.SSL_KEYFILE

    uvicorn.run(**kwargs)
