"""FastAPI application factory and REST routes."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status

from app.database import Database
from app.models import (
    Bot,
    BotCreate,
    BotUpdate,
    Channel,
    ChannelCreate,
    ChannelUpdate,
    ManagerConfig,
    ManagerConfigUpdate,
)


def _database_path() -> str:
    return os.getenv("TBM_DATABASE_PATH", str(Path("data") / "twitch_bot_manager.db"))


def create_app() -> FastAPI:
    app = FastAPI(
        title="Twitch Bot Manager",
        description="Demo-mode API for managing Twitch bot profiles and channels.",
        version="1.0.0",
    )
    database = Database(_database_path())
    database.initialize()
    app.state.database = database

    def get_bot_or_404(bot_id: int) -> dict[str, object]:
        bot = database.fetch_one("SELECT * FROM bots WHERE id = ?", (bot_id,))
        if bot is None:
            raise HTTPException(status_code=404, detail="Bot profile not found")
        return bot

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "mode": os.getenv("TBM_MODE", "demo"),
            "service": "twitch-bot-manager",
        }

    @app.get("/api/bots", response_model=list[Bot], tags=["bots"])
    def list_bots() -> list[dict[str, object]]:
        return database.fetch_all("SELECT * FROM bots ORDER BY id")

    @app.post(
        "/api/bots",
        response_model=Bot,
        status_code=status.HTTP_201_CREATED,
        tags=["bots"],
    )
    def create_bot(payload: BotCreate) -> dict[str, object]:
        try:
            bot_id = database.execute(
                """
                INSERT INTO bots (name, username, command_prefix, enabled)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload.name,
                    payload.username,
                    payload.command_prefix,
                    int(payload.enabled),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409, detail="A bot with that username already exists"
            ) from error
        return get_bot_or_404(bot_id)

    @app.get("/api/bots/{bot_id}", response_model=Bot, tags=["bots"])
    def get_bot(bot_id: int) -> dict[str, object]:
        return get_bot_or_404(bot_id)

    @app.patch("/api/bots/{bot_id}", response_model=Bot, tags=["bots"])
    def update_bot(bot_id: int, payload: BotUpdate) -> dict[str, object]:
        get_bot_or_404(bot_id)
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if changes:
            columns = ", ".join(f"{key} = ?" for key in changes)
            values = [
                int(value) if isinstance(value, bool) else value for value in changes.values()
            ]
            try:
                database.execute(
                    f"UPDATE bots SET {columns}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (*values, bot_id),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(
                    status_code=409, detail="A bot with that username already exists"
                ) from error
        return get_bot_or_404(bot_id)

    def set_bot_state(bot_id: int, target: str) -> dict[str, object]:
        bot = get_bot_or_404(bot_id)
        if target == "running" and not bool(bot["enabled"]):
            raise HTTPException(status_code=409, detail="Disabled bots cannot be started")
        database.execute(
            "UPDATE bots SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (target, bot_id),
        )
        return get_bot_or_404(bot_id)

    @app.post("/api/bots/{bot_id}/start", response_model=Bot, tags=["runtime"])
    def start_bot(bot_id: int) -> dict[str, object]:
        return set_bot_state(bot_id, "running")

    @app.post("/api/bots/{bot_id}/stop", response_model=Bot, tags=["runtime"])
    def stop_bot(bot_id: int) -> dict[str, object]:
        return set_bot_state(bot_id, "stopped")

    @app.delete("/api/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["bots"])
    def delete_bot(bot_id: int) -> Response:
        get_bot_or_404(bot_id)
        database.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def get_channel_or_404(channel_id: int) -> dict[str, object]:
        channel = database.fetch_one("SELECT * FROM channels WHERE id = ?", (channel_id,))
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found")
        return channel

    @app.get("/api/channels", response_model=list[Channel], tags=["channels"])
    def list_channels(bot_id: int | None = None) -> list[dict[str, object]]:
        if bot_id is None:
            return database.fetch_all("SELECT * FROM channels ORDER BY id")
        get_bot_or_404(bot_id)
        return database.fetch_all("SELECT * FROM channels WHERE bot_id = ? ORDER BY id", (bot_id,))

    @app.post(
        "/api/channels",
        response_model=Channel,
        status_code=status.HTTP_201_CREATED,
        tags=["channels"],
    )
    def create_channel(payload: ChannelCreate) -> dict[str, object]:
        get_bot_or_404(payload.bot_id)
        try:
            channel_id = database.execute(
                "INSERT INTO channels (bot_id, name, enabled) VALUES (?, ?, ?)",
                (payload.bot_id, payload.name, int(payload.enabled)),
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="That bot is already assigned to this channel",
            ) from error
        return get_channel_or_404(channel_id)

    @app.get("/api/channels/{channel_id}", response_model=Channel, tags=["channels"])
    def get_channel(channel_id: int) -> dict[str, object]:
        return get_channel_or_404(channel_id)

    @app.patch("/api/channels/{channel_id}", response_model=Channel, tags=["channels"])
    def update_channel(channel_id: int, payload: ChannelUpdate) -> dict[str, object]:
        get_channel_or_404(channel_id)
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if "bot_id" in changes:
            get_bot_or_404(int(changes["bot_id"]))
        if changes:
            columns = ", ".join(f"{key} = ?" for key in changes)
            values = [
                int(value) if isinstance(value, bool) else value for value in changes.values()
            ]
            try:
                database.execute(
                    f"UPDATE channels SET {columns}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (*values, channel_id),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(
                    status_code=409,
                    detail="That bot is already assigned to this channel",
                ) from error
        return get_channel_or_404(channel_id)

    @app.delete(
        "/api/channels/{channel_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["channels"],
    )
    def delete_channel(channel_id: int) -> Response:
        get_channel_or_404(channel_id)
        database.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def read_config() -> dict[str, object]:
        config = database.fetch_one(
            """
            SELECT default_prefix, auto_reconnect, response_delay_ms,
                   respond_to_whispers
            FROM manager_config WHERE id = 1
            """
        )
        if config is None:
            raise HTTPException(status_code=500, detail="Manager configuration is missing")
        return config

    @app.get("/api/config", response_model=ManagerConfig, tags=["configuration"])
    def get_config() -> dict[str, object]:
        return read_config()

    @app.patch("/api/config", response_model=ManagerConfig, tags=["configuration"])
    def update_config(payload: ManagerConfigUpdate) -> dict[str, object]:
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if changes:
            columns = ", ".join(f"{key} = ?" for key in changes)
            values = [
                int(value) if isinstance(value, bool) else value for value in changes.values()
            ]
            database.execute(
                f"UPDATE manager_config SET {columns} WHERE id = 1",
                tuple(values),
            )
        return read_config()

    return app


app = create_app()
