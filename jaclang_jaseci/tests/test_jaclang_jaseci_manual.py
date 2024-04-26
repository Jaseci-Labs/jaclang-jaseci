"""Temporary."""

from contextlib import suppress
from json import load
from os import getenv
from typing import Union
from unittest.async_case import IsolatedAsyncioTestCase

from httpx import get, post

from ..collections import BaseCollection


class JacLangJaseciTests(IsolatedAsyncioTestCase):
    """JacLang Jaseci Feature Tests."""

    async def asyncSetUp(self) -> None:
        """Reset DB and wait for server."""
        self.host = "http://0.0.0.0:8000"
        BaseCollection.__client__ = None
        BaseCollection.__database__ = None
        self.client = BaseCollection.get_client()
        self.users = []
        self.database = getenv("DATABASE_NAME", "jaclang-manual")
        count = 0
        while True:
            if count > 5:
                self.get_openapi_json(1)
                break
            else:
                with suppress(Exception):
                    self.get_openapi_json(1)
                    break
            count += 1

    async def asyncTearDown(self) -> None:
        """Clean up DB."""
        await self.client.drop_database(self.database)

    def create_test_user(self, suffix: str = "") -> None:
        """Call openapi specs json."""
        email = f"user{suffix}@example.com"

        res = post(
            f"{self.host}/user/register",
            json={
                "password": "string",
                "email": email,
                "name": "string",
            },
        )
        res.raise_for_status()
        self.assertEqual({"message": "Successfully Registered!"}, res.json())

        res = post(
            f"{self.host}/user/login",
            json={"email": email, "password": "string"},
        )
        res.raise_for_status()
        res = res.json()

        token = res.get("token")
        self.assertIsNotNone(token)

        user = res.get("user")
        self.assertEqual(email, user["email"])
        self.assertEqual("string", user["name"])

        self.users.append(
            {"user": user, "headers": {"Authorization": f"Bearer {token}"}}
        )

    def get_openapi_json(self, timeout: int = None) -> dict:
        """Call openapi specs json."""
        res = get(f"{self.host}/openapi.json", timeout=timeout)
        res.raise_for_status()
        return res.json()

    def post_api(
        self, api: str, json: dict = None, user: int = 0, expect_error: bool = False
    ) -> Union[dict, int]:
        """Call post api return json."""
        res = post(
            f"{self.host}/walker/{api}", json=json, headers=self.users[user]["headers"]
        )

        if not expect_error:
            print(res.json())
            res.raise_for_status()
            return res.json()
        else:
            return res.status_code

    def test_all_features(self) -> None:
        """Test all features."""
        ############################################################
        # ------------------ TEST OPENAPI SPECS ------------------ #
        ############################################################

        res = self.get_openapi_json()

        with open("jaclang_jaseci/tests/simple_walkerapi_openapi_specs.json") as file:
            self.assertEqual(load(file), res)

        ############################################################
        # --------------------- CREATE USERS --------------------- #
        ############################################################

        self.create_test_user()
        self.create_test_user("2")

        ############################################################
        # ---------------------- TEST GRAPH ---------------------- #
        ############################################################

        res = self.post_api("create_sample_graph")
        self.assertEqual({"status": 200, "returns": [True]}, res)

        res = self.post_api("visit_sample_graph")
        self.assertEqual(200, res["status"])
        self.assertEqual([1, 2, 3], res["returns"])

        reports = res["reports"]
        report = reports[0]
        self.assertTrue(report["id"].startswith("n::"))

        report = reports[1]
        self.assertTrue(report["id"].startswith("n:boy:"))
        self.assertEqual({"val1": "a", "val2": "b"}, report["context"])

        report = reports[2]
        self.assertTrue(report["id"].startswith("n:girl:"))
        self.assertEqual({"val": "b"}, report["context"])

        res = self.post_api("update_sample_graph")
        self.assertEqual(200, res["status"])
        self.assertEqual([None, None], res["returns"])

        reports = res["reports"]
        report = reports[0]
        self.assertTrue(report["id"].startswith("n:girl:"))
        self.assertEqual({"val": "b"}, report["context"])

        report = reports[1]
        self.assertTrue(report["id"].startswith("n:girl:"))
        self.assertEqual({"val": "new"}, report["context"])

        res = self.post_api("create_list_field")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": []}, report["context"])

        first_user_node_id = report["id"]

        res = self.post_api(f"update_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1]}, report["context"])

        res = self.post_api(f"update_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1]}, report["context"])

        ############################################################
        # ---------------------- OTHER USER ---------------------- #
        ############################################################

        res = self.post_api("create_list_field", user=1)
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": []}, report["context"])

        second_user_node_id = report["id"]

        res = self.post_api(
            f"update_list_field/{second_user_node_id}", expect_error=True
        )
        self.assertEqual(403, res)  # forbidden

        ############################################################
        # -------------------- ALLOW ROOT READ ------------------- #
        ############################################################

        res = self.post_api(
            f"allow_other/{second_user_node_id}",
            json={"root_id": f'n::{self.users[0]["user"]["root_id"]}'},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": []}, report["context"])

        res = self.post_api(f"update_list_field/{second_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1]}, report["context"])

        res = self.post_api(f"update_list_field/{second_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1]}, report["context"])  # still based from [] not [1]

        ############################################################
        # ------------------- ALLOW ROOT WRITE ------------------- #
        ############################################################

        res = self.post_api(
            f"allow_other/{second_user_node_id}",
            json={"root_id": f'n::{self.users[0]["user"]["root_id"]}', "write": True},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": []}, report["context"])

        res = self.post_api(f"update_list_field/{second_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1]}, report["context"])

        res = self.post_api(f"update_list_field/{second_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1]}, report["context"])

        ############################################################
        # --------------------- DISALLOW ROOT -------------------- #
        ############################################################

        res = self.post_api(
            f"disallow_other/{second_user_node_id}",
            json={"root_id": f'n::{self.users[0]["user"]["root_id"]}'},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        res = self.post_api(
            f"update_list_field/{second_user_node_id}", expect_error=True
        )
        self.assertEqual(403, res)  # forbidden

        ############################################################
        # -------------------- ALLOW NODE READ ------------------- #
        ############################################################

        res = self.post_api(
            f"allow_other/{second_user_node_id}",
            json={"node_id": first_user_node_id},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1]}, report["context"])

        res = self.post_api(
            f"connect_other_node/{first_user_node_id}",
            json={"node_id": second_user_node_id},
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1]}, report["context"])

        res = self.post_api(f"update_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None, None], res["returns"])

        for report in res["reports"]:
            self.assertTrue(report["id"].startswith("n:someone"))
            self.assertEqual(
                {"val": [1, 1, 1]}, report["context"]
            )  # other update will revert back to [1,1] since it doesn't have write access

        res = self.post_api(f"get_list_field/{second_user_node_id}", user=1)

        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual(
            {"val": [1, 1]}, report["context"]
        )  # proves that it's not updated
        self.assertEqual([], res["reports"][1])

        ############################################################
        # ------------------- ALLOW NODE WRITE ------------------- #
        ############################################################

        res = self.post_api(
            f"allow_other/{second_user_node_id}",
            json={"node_id": first_user_node_id, "write": True},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1]}, report["context"])

        res = self.post_api(f"update_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None, None], res["returns"])

        reports = res["reports"]
        self.assertTrue(reports[0]["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1, 1, 1]}, reports[0]["context"])
        self.assertTrue(reports[1]["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1, 1]}, reports[1]["context"])

        res = self.post_api(f"get_list_field/{second_user_node_id}", user=1)
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual(
            {"val": [1, 1, 1]}, report["context"]
        )  # proves that it was able to update
        self.assertEqual([], res["reports"][1])

        res = self.post_api(f"get_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual(
            {"val": [1, 1, 1, 1]}, report["context"]
        )  # proves that it was able to update

        report = res["reports"][1][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual(
            {"val": [1, 1, 1]}, report["context"]
        )  # proves that it was able to access by first user

        ############################################################
        # --------------------- DISALLOW ROOT -------------------- #
        ############################################################

        res = self.post_api(
            f"disallow_other/{second_user_node_id}",
            json={"node_id": first_user_node_id},
            user=1,
        )
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        res = self.post_api(f"get_list_field/{first_user_node_id}")
        self.assertEqual(200, res["status"])
        self.assertEqual([None], res["returns"])

        report = res["reports"][0]
        self.assertTrue(report["id"].startswith("n:someone"))
        self.assertEqual({"val": [1, 1, 1, 1]}, report["context"])
        self.assertEqual(
            [], res["reports"][1]
        )  # proves that it wasn't able to access the node even it's connected