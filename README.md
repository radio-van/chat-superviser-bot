Chat Superviser Bot
================

A simple bot to check messages in Telegram group chats for text duplication.  
It can be configured to check only messages that are forwarded from other chats, or messages which text is longer  
than defined number of words.

Bot sends a warning message as a reply to the original message with a mention of the duplicate sender.  
This warning is self-destroed in defined amount of seconds.

#### installation
* dev deployment
  - define required env vars in `.env` file (see `env.example` for a list of vars)
  - `docker-compose up -d redis` start a Redis container which is used to store recent messages
  - `poetry install && ./start.sh` create local Python env in `.venv`, install dependencies and run the bot

* containered deployment
  - define required env vars in `.env` file (see `env.example` for a list of vars)
  - `docker-compose up -d` start both Redis and bot

#### info
Bot is based on [pyrogram](https://pyrogram.org/) library.
