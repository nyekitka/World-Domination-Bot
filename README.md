![Tech Stack](https://github-readme-tech-stack.vercel.app/api/cards?title=Tech+Stack&align=center&fontFamily=Montserratt&lineCount=3&line1=python%2Cpython%2C00d0c7%3Baiogram%2Caiogram%2C00ff35%3Bpytest%2Cpytest%2C2e50c8%3Bdjango%2Cdjango%2C0b7829%3B&line2=html%2Chtml%2Cffa100%3Bcss%2Ccss%2C4e6eff%3Bjinja%2Cjinja%2C4e0000%3Bpoetry%2Cpoetry%2C3294ff%3B&line3=postgresql%2Cpostgresql%2C302eff%3Bredis%2Credis%2Cff0000%3Bdocker%2Cdocker%2C3e85ff%3Bsqlalchemy%2Csqlalchemy%2C00c128%3B)

# How to use?

Clone that repository with
```
git clone https://github.com/nyekitka/World-Domination-Bot.git
```

Next, create a `.env` file from `.env.example` in the folder where you cloned the repository and set there secret variables.
```
cp .env.example .env
```

Make sure that you have installed Docker and it's running. If it is, then enter the next command in the terminal
```
docker compose up -d --build app
```

# What does it consist of?

## Modules

The app consists of
- Aiogram app (`/app` folder),
- PostgreSQL database (`/database`),
- Redis storage (`/storage`)
- Mini-website (`/web_app`)

The main part is aiogram app which includes all handlers of telegram events. PostgreSQL database is used to
store information about users, going on and finished games and its results. Redis storage is used to store
temporary information for app, such as message ids and intermediate information. The web app is round statistics
that administrators show to players. Web app is integrated with Telegram Mini App.

## Tests

To run tests use:
```
docker compose run test make test
```
To run certain test or tests:
```
docker compose run test make test k="storage"
```
Temporarily app tests don't work because they're written improperly. There are plans to replace them with
autotests.


## Linter

The code is written in accordance with [PEP8](https://peps.python.org/pep-0008/). Linter Ruff is used to maintain a good style of code. To check style use
```
make lint
```
Fix some linter warnings
```
make fix-lint
```

## Gallery

![`/start`](/img/start.png?raw=true)

![create lobby](/img/create_lobby.png?raw=true)

![round](/img/round.png?raw=true)

![stats](/img/stats.png?raw=true)
