## Endpoints for Documentation & Admin panel

* /auth/openapi.json - Openapi
* /auth/admin - Admin panel
* /auth/docs - Swagger documentation
* /auth/redoc - ReDoc documentation
* /auth/mkdocs - MkDocs documentation


## Project Directory Structure
```
├── .githooks
    ├── pre-push
├── .github
      ├── workflows
├── api
    ├── endpoints
        ├── v1
        ├── v2
├── app
    ├── module-name
        ├── crud.py
        ├── model.py
        ├── schema.py
        ├── service.py
    ├── crud.py
    ├── main.py
    ├── model.py
├── core
├── data # SQL scripts for database population
├── deploy
├── docker
├── docs
├── migrations
├── pipelines
    ├── accounts
    ├── admin
├── tests
    ├── api
        ├── test_module-name
    ├── integration
    ├── unit
```

Базая структура выглядит следующим образом:
- `core` — ядро, системные вызовы, коннекторы, настройки, не предметно-ориентированный код, а уровень инфраструктуры
- `app` — предметная область приложения, ключевая часть приложения, где сосредоточеная вся бизнес-логика и взаимодействие с данными
- `api` — presentation layer

`app` в свою очередь, состоит из следующих структур:
- `model.py` — доменные сущности: таблицы в БД
- `crud.py` — коллекции данных, некий стандартизированный интерфейс работы с сущностями, тут не сосредоточена логика, тут есть только относительно тривиальные операции ввода/вывода
- `schema.py` — pydantic-схемы, валидация
- `service.py` — это сердце приложения, бизнес-логика, где происходит работа с сущностями/репозиториями,
валидации/запись/сохранение и так далее, они инжектят в себя репозитории и взаимодействют с ними. Они реализуют use case. Сюда же относится и взаимодействие с внешними сервисами. В свою очередь `service.py` реализованы по паттерну CQRS, и предполагают, что разные сервисы будут отвечать за чтение и запись данных (отделение command от query).

В итоге, получается такая схема:
- `api` взаимодействует с `service`
- `service` реализуют логику и взаимодействуют с `crud` по контрактам из `schemas`
- `crud` взаимодействует с хранилищами (postgres/redis) по контрактам из `schemas`, используя `models` и возвращают данные

## При обновлении версии secrets

1. Запустить Pipeline

## При обновлении схем баз данных

1. В корне проекта alembic revision --autogenerate -m "name" создаем миграцию
make create migrations name=init
2. alembic upgrade head применить миграцию

## Start Project

1. Создать симлинки
```sh
cp .env.example .env.development && ln -sf .env.development .env
```

2. Загрузить .env в окружение
```sh
source .env
```

3. Install pyenv
https://github.com/pyenv/pyenv#installation

4. Install poetry
```sh
curl -sSL https://install.python-poetry.org | python3 -
```

5. Install python
```sh
pyenv install 3.11.5 && pyenv global 3.11.5
```

6. Set interpreter
```sh
poetry env use 3.11.5
```

7. Install dependencies.
```sh
poetry lock --no-update && poetry install --no-root
```

8. Run project
```sh
poetry run python3 app/main.py
```

9. Setup pre-commit hooks
```sh
pre-commit install
```
core.hooksPath should be deleted

## Troubleshoot & Debug

1. Kill service on specific port
```sh
fuser -k 8000/tcp
```

1. Test API via curl
```sh
curl -X POST -d '' http://0.0.0.0:8000/api/v1/auth/
```

### Adding a new route

For CRUD applications, follow the example in [resource.rs](apps/api.routes/resource.rs) and add your resource route to:

- ```GET /<resource-name>/{:id}```
- ```GET /<resource-name>/list```
- ```POST /<resource-name>```
- ```PUT /<resource-name>/{:id}```
- ```DELETE /<resource-name>/{:id}```


### Adding a new model

ToDo

### Tests

ToDo

## Migrations

Migrations are run using alembic.
We are using Makefile.

And fill in `upgrade` and `downgrade` methods. For more information see
[Alembic's official documentation](https://alembic.sqlalchemy.org/en/latest/tutorial.html#create-a-migration-script).

## Pre-Commit

1. **Install `pre-commit`** (if you haven't already):
   ```bash
   pip install pre-commit
   ```

2. **Install the pre-commit hooks** specified in your `.pre-commit-config.yaml` file by running:
   ```bash
   pre-commit install
   ```
   This command sets up pre-commit to automatically run the hooks defined in your configuration before each commit.

3. **Run the hooks manually (optional):** If you want to run the hooks on all files (instead of just the staged files), you can use:
   ```bash
   pre-commit run --all-files
   ```

Once installed, each time you make a commit, `pre-commit` will automatically run `isort`, `black`, `ruff`, and `mypy` to format and lint your code as specified.

### Connecting to a source DB

ToDo

## Tags

Tags allow you to identify specific release versions of your code. 
You can think of a tag as a branch that doesn't change. 
Once it is created, it loses the ability to change the history of commits.
Tags are just the repository frozen in time.

## Database performance check

```
wrk -c30 -t3 -d10s  -H "Authorization: bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhcnRlbS5rdXN0aWtvdkBnbWFpbC5jb20iLCJ1aWQiOjUsImZuIjpudWxsLCJsbiI6bnVsbCwicGVybWlzc2lvbnMiOiJ1c2VyIiwiZXhwIjoxNjU0MDIxODg2fQ.439CjqvKtBMvIXBEmH0FLW98Te51ur-VBlTsaS7AkhI" http://localhost:8888/api/users/me  --timeout 5
Running 10s test @ http://localhost:8888/api/users/me
  3 threads and 30 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    49.86ms   23.51ms 167.93ms   67.88%
    Req/Sec   201.13     28.65   343.00     71.00%
  6013 requests in 10.01s, 1.18MB read
Requests/sec:    600.77
Transfer/sec:    121.03KB


##  Changing the route in the API Gateway
```
in the api gateway you need to replace index.html with maintenance.html in the / and /{files+} sections
