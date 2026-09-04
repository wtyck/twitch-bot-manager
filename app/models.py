"""Pydantic request and response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=25, pattern=r"^[A-Za-z0-9_]+$")
    command_prefix: str = Field(default="!", min_length=1, max_length=3)
    enabled: bool = True

    @field_validator("name", "username", "command_prefix")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    username: str | None = Field(
        default=None, min_length=3, max_length=25, pattern=r"^[A-Za-z0-9_]+$"
    )
    command_prefix: str | None = Field(default=None, min_length=1, max_length=3)
    enabled: bool | None = None

    @field_validator("name", "username", "command_prefix")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None


class Bot(BotCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["running", "stopped"]
    created_at: str
    updated_at: str


class ChannelCreate(BaseModel):
    bot_id: int = Field(gt=0)
    name: str = Field(min_length=3, max_length=25, pattern=r"^[A-Za-z0-9_]+$")
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def normalize_channel_name(cls, value: str) -> str:
        return value.strip().lower()


class ChannelUpdate(BaseModel):
    bot_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=3, max_length=25, pattern=r"^[A-Za-z0-9_]+$")
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_channel_name(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class Channel(ChannelCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
    updated_at: str


class ManagerConfig(BaseModel):
    default_prefix: str = Field(min_length=1, max_length=3)
    auto_reconnect: bool
    response_delay_ms: int = Field(ge=0, le=5000)
    respond_to_whispers: bool


class ManagerConfigUpdate(BaseModel):
    default_prefix: str | None = Field(default=None, min_length=1, max_length=3)
    auto_reconnect: bool | None = None
    response_delay_ms: int | None = Field(default=None, ge=0, le=5000)
    respond_to_whispers: bool | None = None

    @field_validator("default_prefix")
    @classmethod
    def strip_optional_prefix(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None
