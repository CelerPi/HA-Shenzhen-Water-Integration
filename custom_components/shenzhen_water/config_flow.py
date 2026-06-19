from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApiClient, ShenzhenWaterApiError
from .const import (
    CONF_BASE_URL,
    CONF_CHANNEL,
    CONF_CUSTOMER_CODES,
    CONF_GUID,
    CONF_MOBILE,
    CONF_TENANT_ID,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_CHANNEL,
    DEFAULT_TENANT_ID,
    DOMAIN,
)


class ShenzhenWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._pending_data: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(user_input)
            data[CONF_CUSTOMER_CODES] = _parse_customer_codes(data[CONF_CUSTOMER_CODES])
            if not data[CONF_CUSTOMER_CODES]:
                errors["base"] = "invalid_customer_codes"
                return self.async_show_form(
                    step_id="user",
                    data_schema=_user_schema(),
                    errors=errors,
                )
            await self.async_set_unique_id("|".join(data[CONF_CUSTOMER_CODES]))
            self._abort_if_unique_id_configured()

            if data.get(CONF_TOKEN) and data.get(CONF_GUID):
                return self.async_create_entry(
                    title=f"深圳水务 {data[CONF_CUSTOMER_CODES][0]}",
                    data=data,
                )

            self._pending_data = data
            try:
                await self._client(data).async_send_validation_code()
            except ShenzhenWaterApiError:
                errors["base"] = "send_code_failed"
            else:
                return await self.async_step_sms()

        return self.async_show_form(step_id="user", data_schema=_user_schema(), errors=errors)

    async def async_step_sms(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token, guid = await self._client(self._pending_data).async_login(
                    user_input["validation_code"]
                )
            except ShenzhenWaterApiError:
                errors["base"] = "login_failed"
            else:
                if self.source == config_entries.SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates={CONF_TOKEN: token, CONF_GUID: guid},
                    )
                data = {**self._pending_data, CONF_TOKEN: token, CONF_GUID: guid}
                return self.async_create_entry(
                    title=f"深圳水务 {data[CONF_CUSTOMER_CODES][0]}",
                    data=data,
                )

        return self.async_show_form(
            step_id="sms",
            data_schema=vol.Schema({vol.Required("validation_code"): str}),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._pending_data = dict(self._get_reauth_entry().data)
            try:
                await self._client(self._pending_data).async_send_validation_code()
            except ShenzhenWaterApiError:
                errors["base"] = "send_code_failed"
            else:
                return await self.async_step_sms()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            errors=errors,
        )

    def _client(self, data: dict[str, Any]) -> ShenzhenWaterApiClient:
        return ShenzhenWaterApiClient(
            async_get_clientsession(self.hass),
            base_url=data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            mobile=data[CONF_MOBILE],
            customer_codes=list(data[CONF_CUSTOMER_CODES]),
            tenant_id=data.get(CONF_TENANT_ID, DEFAULT_TENANT_ID),
            channel=data.get(CONF_CHANNEL, DEFAULT_CHANNEL),
            token=data.get(CONF_TOKEN),
            guid=data.get(CONF_GUID),
        )


def _parse_customer_codes(value: str) -> list[str]:
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            vol.Required(CONF_MOBILE): str,
            vol.Required(CONF_CUSTOMER_CODES): str,
            vol.Optional(CONF_TENANT_ID, default=DEFAULT_TENANT_ID): str,
            vol.Optional(CONF_CHANNEL, default=DEFAULT_CHANNEL): str,
            vol.Optional(CONF_TOKEN): str,
            vol.Optional(CONF_GUID): str,
        }
    )
