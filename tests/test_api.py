"""API integration tests for Twitch Bot Manager."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient


class TwitchBotManagerAPITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["TBM_DATABASE_PATH"] = str(Path(self.temp_dir.name) / "test.db")

        from app.main import create_app

        self.app = create_app()
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        self.temp_dir.cleanup()

    async def test_health_reports_demo_mode(self) -> None:
        response = await self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "mode": "demo", "service": "twitch-bot-manager"},
        )

    async def test_bot_profile_crud_lifecycle(self) -> None:
        create = await self.client.post(
            "/api/bots",
            json={
                "name": "Chat Guardian",
                "username": "guardian_demo",
                "command_prefix": "!",
            },
        )
        self.assertEqual(create.status_code, 201)
        created = create.json()
        self.assertEqual(created["name"], "Chat Guardian")
        self.assertEqual(created["status"], "stopped")
        self.assertTrue(created["enabled"])

        listing = await self.client.get("/api/bots")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([bot["id"] for bot in listing.json()], [created["id"]])

        update = await self.client.patch(
            f"/api/bots/{created['id']}",
            json={"name": "Guardian", "enabled": False},
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["name"], "Guardian")
        self.assertFalse(update.json()["enabled"])

        fetched = await self.client.get(f"/api/bots/{created['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json(), update.json())

        delete = await self.client.delete(f"/api/bots/{created['id']}")
        self.assertEqual(delete.status_code, 204)
        self.assertEqual((await self.client.get("/api/bots")).json(), [])
        self.assertEqual(
            (await self.client.get(f"/api/bots/{created['id']}")).status_code,
            404,
        )

    async def test_start_and_stop_bot_changes_demo_state(self) -> None:
        created = (
            await self.client.post(
                "/api/bots",
                json={"name": "Greeter", "username": "greeter_demo"},
            )
        ).json()

        started = await self.client.post(f"/api/bots/{created['id']}/start")
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.json()["status"], "running")

        stopped = await self.client.post(f"/api/bots/{created['id']}/stop")
        self.assertEqual(stopped.status_code, 200)
        self.assertEqual(stopped.json()["status"], "stopped")

        await self.client.patch(f"/api/bots/{created['id']}", json={"enabled": False})
        rejected = await self.client.post(f"/api/bots/{created['id']}/start")
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["detail"], "Disabled bots cannot be started")

    async def test_channel_crud_is_scoped_to_a_bot(self) -> None:
        bot = (
            await self.client.post("/api/bots", json={"name": "Moderator", "username": "mod_demo"})
        ).json()

        create = await self.client.post(
            "/api/channels",
            json={"bot_id": bot["id"], "name": "sample_channel"},
        )
        self.assertEqual(create.status_code, 201)
        channel = create.json()
        self.assertEqual(channel["bot_id"], bot["id"])
        self.assertTrue(channel["enabled"])

        listing = await self.client.get(f"/api/channels?bot_id={bot['id']}")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json(), [channel])

        update = await self.client.patch(f"/api/channels/{channel['id']}", json={"enabled": False})
        self.assertEqual(update.status_code, 200)
        self.assertFalse(update.json()["enabled"])

        delete = await self.client.delete(f"/api/channels/{channel['id']}")
        self.assertEqual(delete.status_code, 204)
        self.assertEqual((await self.client.get("/api/channels")).json(), [])

        missing_bot = await self.client.post(
            "/api/channels", json={"bot_id": 9999, "name": "nowhere"}
        )
        self.assertEqual(missing_bot.status_code, 404)

    async def test_config_defaults_can_be_updated_and_persisted(self) -> None:
        defaults = await self.client.get("/api/config")
        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(
            defaults.json(),
            {
                "default_prefix": "!",
                "auto_reconnect": True,
                "response_delay_ms": 250,
                "respond_to_whispers": False,
            },
        )

        update = await self.client.patch(
            "/api/config",
            json={"default_prefix": "?", "response_delay_ms": 500},
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["default_prefix"], "?")
        self.assertEqual(update.json()["response_delay_ms"], 500)

        from app.main import create_app

        second_client = AsyncClient(
            transport=ASGITransport(app=create_app()), base_url="http://test"
        )
        try:
            persisted = await second_client.get("/api/config")
            self.assertEqual(persisted.json(), update.json())
        finally:
            await second_client.aclose()


if __name__ == "__main__":
    unittest.main()
