import json
import uuid
from typing import Optional

import pytest

from core.logger import logger


class BaseTest:
    entity = None
    url = None
    create_data = None
    update_data = None
    ifilter = None
    isort = None
    iread = None

    @pytest.mark.asyncio
    async def test_list(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_meta(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(
            url, params={"meta": True}, headers={"Authorization": f"Bearer {auth_data['access_token']}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_crud(self, test_client, auth_data, create_entity, delete_entity):

        ## Create
        url = f"api/v1/{self.entity}"
        response: dict = create_entity(url, self.create_data)
        if isinstance(response["data"], list):
            id = response["data"][0]["id"]
        else:
            id = response["data"]["id"]
        logger.info("create test passed")
        ## Read
        url = f"api/v1/{self.entity}/{id}"
        response = test_client.get(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
        assert response.status_code == 200
        logger.info("read test passed")

        ## Update
        response = test_client.patch(
            url, json=self.update_data, headers={"Authorization": f"Bearer {auth_data['access_token']}"}
        )
        assert response.status_code == 200
        logger.info("update test passed")

        ## Delete
        delete_entity(f"api/v1/{self.entity}/{id}")
        logger.info("delete test passed")

    @pytest.mark.asyncio
    async def test_sort(self, test_client, auth_data, testing):
        operands = ["descending"]
        url = f"api/v1/{self.entity}/list"
        annotations = self.isort.__dict__.get("__annotations__")
        fields = []
        if annotations:
            fields = list(self.isort.__dict__.get("__annotations__").keys())
        if fields:
            for operand in operands:
                for field in fields:
                    response = test_client.get(
                        url + f'?{operand}="{field}"',
                        headers={"Authorization": f"Bearer {auth_data['access_token']}"},
                    )
                    assert response.status_code == 200
                    if testing == "min":
                        break

    @pytest.mark.asyncio
    async def test_gt_lt_eq(self, test_client, auth_data):
        operands = ["lt"]  # ["lt, gt, eq"]
        url = f"api/v1/{self.entity}/list"
        fields_type = {}
        annotations = self.ifilter.__dict__.get("__annotations__")
        if annotations:
            for field, field_type in annotations.items():
                if field_type == Optional[int]:
                    fields_type[field] = field_type
                    break
            for operand in operands:
                for field in fields_type.keys():
                    response = test_client.get(
                        url,
                        params={operand: {field: 123}},
                        headers={"Authorization": f"Bearer {auth_data['access_token']}"},
                    )
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_period(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(
            url,
            params={"period": "2024-01-01:2024-07-01"},
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filters(self, test_client, auth_data):
        """Тест проверяет заполнение схем фильтрации и маппинга внешних фильтров.

        По умолчанию запрос возращает все записи сущности из базы.
        Если нужны детальные тесты, то их стоит добавить для каждого модуля отдельно."""

        def format_value(value):
            if isinstance(value, bool):
                return str(value).lower()  # лучше переделать на фронте и там отдавать просто булев тип в json
            elif isinstance(value, uuid.UUID):
                return str(value)
            elif isinstance(value, int):  # в некоторых enum числовые ключи, это не нумерик фильтр!
                return str(value)
            else:
                return value

        url = f"api/v1/{self.entity}/list"
        fields = self.iread.Meta.fields
        filters = {}
        for key, value in fields.items():
            if value.get("is_filterable") is True and "available_values" in value:
                raise ValueError(f"Can't be both is_filterable and available_values {key}")
            elif value.get("is_filterable") is True:  # числовые фильтры в отдельном тесте
                continue
            elif "filter_by" in value:
                column = value["filter_by"]
            elif "available_values" in value:
                column = key
            else:
                continue

            # if value.get("column_type") == "enum":
            #     available_values = list(filter(None, value["available_values"].values()))  # todo available может не быть словарем, например списком
            # else:
            available_values = list(filter(None, value["available_values"].keys()))
            if not available_values:
                logger.error(f"No values for {column}")  # todo exception здесь после старта основных тестов
                continue
            filters[column] = list(map(format_value, available_values)) + [None]
            try:
                json.dumps(filters)
            except:
                pass

        response = test_client.get(
            url,
            params={"filters": json.dumps(filters)},
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_report(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/report"
        response = test_client.get(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
        assert response.status_code == 200


class SearchOnMixin:
    @pytest.mark.asyncio
    async def test_list_fts(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(
            url,
            params={
                "search": json.dumps(
                    [
                        "test",
                    ]
                )
            },
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert response.status_code == 200


class SearchOffMixin:
    @pytest.mark.asyncio
    async def test_list_fts_unavailable(self, test_client, auth_data):
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(
            url,
            params={
                "search": json.dumps(
                    [
                        "test",
                    ]
                )
            },
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert response.status_code == 422 and response.json()["detail"] == "Search is not available here"


class PeriodOnMixin:
    @pytest.mark.asyncio
    async def test_same_period(self, test_client, auth_data):
        # Тест для фильтрации по датам. Данные тестирования добавлены только для сущности card
        url = f"api/v1/{self.entity}/list"
        response = test_client.get(
            url,
            params={"period": "2004-12-19:2004-12-19"},
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert len(response.json()["data"]["items"]) == 3
        response = test_client.get(
            url,
            params={"period": "2004-12-19:2004-12-20"},
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert len(response.json()["data"]["items"]) == 4
        response = test_client.get(
            url,
            params={"period": "2004-12-19:2004-12-18"},
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert response.status_code == 422


class BulkUpdateMixin:
    update_ids = None  # list of 2 or more entity ids in the tests/data.sql

    @pytest.mark.asyncio
    async def test_bulk_update(self, test_client, auth_data):
        if self.update_ids is None:
            raise NotImplementedError("update_ids must be defined")

        if self.update_data is None:
            raise NotImplementedError("update_data must be defined")
        url = f"api/v1/{self.entity}/{'.'.join(self.update_ids)}"

        response = test_client.patch(
            url, json=self.update_data, headers={"Authorization": f"Bearer {auth_data['access_token']}"}
        )
        assert response.status_code == 200

    # @pytest.mark.asyncio
    # async def test_changelog(self, test_client, auth_data):
    #     url = f"api/v1/{self.entity}"
    #     response = test_client.post(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
    #     assert response.status_code == 200

    # @pytest.mark.asyncio
    # async def test_crud_bulk(self, test_client, auth_data):

    #     ## Create
    #     url = f"api/v1/{self.entity}"
    #     response = test_client.post(
    #         url, json=[self.create_data], headers={"Authorization": f"Bearer {auth_data['access_token']}"}
    #     )
    #     assert response.status_code == 200
    #     list_id = [id for id in response.json()["data"]]
    #     list_id = list_id.join(".")
    #     logger.info("create test passed")

    #     ## Read
    #     url = f"api/v1/{self.entity}/{list_id}"
    #     response = test_client.get(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
    #     assert response.status_code == 200
    #     logger.info("read test passed")

    #     ## Update
    #     response = test_client.patch(
    #         url, json=self.update_data, headers={"Authorization": f"Bearer {auth_data['access_token']}"}
    #     )
    #     assert response.status_code == 200
    #     logger.info("update test passed")

    #     ## Delete
    #     response = test_client.delete(url, headers={"Authorization": f"Bearer {auth_data['access_token']}"})
    #     assert response.status_code == 200
    #     logger.info("delete test passed")
