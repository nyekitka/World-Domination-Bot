# How to use?

Clone that repository with
```
git clone https://github.com/nyekitka/World-Domination-Bot.git
```

Next, create a `.env` file in the folder where you cloned the repository and set there these variables.
```bash
OWNER=... #Telegram id of bot's owner. This Telegram account will be the main administrator.
POSTGRES_NAME=... #name of the database. You can make it whatever you want
POSTGRES_USER=postgres
POSTGRES_PASSWORD=... #password to the database
POSTGRES_HOST=db
POSTGRES_PORT=5432
BOT_TOKEN=... #token of the telegram bot
ROUND_LENGTH=... #length of the round in seconds
```

You can do it fast with this command:
```
cp .env.example .env
```

Make sure that you have installed Docker and it's running. If it is, then enter the next command in the terminal
```
docker-compose up
```
or (it probably depends on your OS)
```
docker compose up
```
