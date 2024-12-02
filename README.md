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

1. cd docker/dev
```sh
docker-compose up -d
```

2. Создать пользователя
```sh
POST http://127.0.0.1:8000/api/v1/user
{
    "first_name": "test_user",
    "last_name": "test_user",
    "password": "testpass",
    "email": "test@test.ru"
}
```

3. Авторизация http://127.0.0.1:8000/api/v1/auth/basic
Form data 
username = test@test.ru
password = testpass
Получаем access_token

4. Сохраняем данные из задания 
```sh
POST  http://127.0.0.1:8000/api/v1/cargo_insurance/create_all

{
    "2020-06-01": [
        {
            "cargo_type": "Glass",
            "rate": "0.04"
        },
        {
            "cargo_type": "Other",
            "rate": "0.01"
        }
    ],
    "2020-07-01": [
        {
            "cargo_type": "Glass",
            "rate": "0.035"
        },
        {
            "cargo_type": "Other",
            "rate": "0.015"
        }
    ]
}

Bearer token ****

TODO Очень плохая струкрута которую сложно валидировать
```

5. Синтаксис запросов 

```sh
запрос http://0.0.0.0:8000/api/v1/cargo_insurance/list?filters={"cargo_type": ["Glass"]}&period=2020-06-01:2020-06-01&cost=500

    "data": {
        "items": [
            {
                "base_fields": {},
                "id": "f365cd38-f419-4408-86a8-a158d7ad6590",
                "updated_at": "2024-12-01T13:07:03",
                "created_at": "2024-12-01T13:07:03",
                "updated_by": "f8779c73-02a5-4d09-b001-6da2167f7c0d",
                "created_by": "f8779c73-02a5-4d09-b001-6da2167f7c0d",
                "changelog": [],
                "cost": 500.0,
                "date": "2020-06-01T00:00:00",
                "cargo_type": "Glass",
                "rate": 0.04,
                "full_cost": 20.0
            }
        ],
        "total": 1,
        "page": 1,
        "size": 50,
        "pages": 1
    }
full_cost стоимость страхования груза
в запросах filters можно указать любой атрибут и значение.
period можно указать любую дату тарифа и посчитать стоимость страхования
если не указывать ни какие фильтры то посчитает для всех тарифов и для всех дат.
```

5. Полнотекстовый поиск

```sh
запрос http://0.0.0.0:8000/api/v1/cargo_insurance/list?fsearch=["entity value"]

```