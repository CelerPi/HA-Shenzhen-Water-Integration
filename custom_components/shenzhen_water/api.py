from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aiohttp import ClientError, ClientSession

from .crypto import decrypt_response, encrypt_payload, random_header


class ShenzhenWaterApiError(Exception):
    """Raised when Shenzhen Water cannot return usable data."""


class ShenzhenWaterAuthError(ShenzhenWaterApiError):
    """Raised when Shenzhen Water credentials are no longer valid."""


@dataclass(frozen=True)
class ShenzhenWaterBill:
    bill_month: str | None = None
    customer_code: str | None = None
    total_amount: float | None = None
    water_amount: float | None = None
    sewage_amount: float | None = None
    garbage_amount: float | None = None
    late_fee: float | None = None
    need_pay: float | None = None
    water_consumption: float | None = None
    water_after_reduced: float | None = None
    due_date: str | None = None
    payment_status: str | None = None
    water_status: str | None = None
    sewage_status: str | None = None
    garbage_status: str | None = None
    meter_code: str | None = None
    meter_current_reading: float | None = None
    meter_previous_reading: float | None = None
    meter_current_date: str | None = None
    meter_previous_date: str | None = None
    water_use_days: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShenzhenWaterData:
    latest_bill: ShenzhenWaterBill | None = None
    bills: tuple[ShenzhenWaterBill, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)
    result_code: int | None = None
    result_message: str | None = None


class ShenzhenWaterApiClient:
    def __init__(
        self,
        session: ClientSession,
        *,
        base_url: str,
        mobile: str,
        customer_codes: list[str],
        tenant_id: str,
        channel: str,
        token: str | None = None,
        guid: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._mobile = mobile
        self._customer_codes = customer_codes
        self._tenant_id = tenant_id
        self._channel = channel
        self._token = token or ""
        self._guid = guid or ""

    async def async_send_validation_code(self) -> None:
        data = await self._invoke(
            "op/user/GenerateValidationNumV20",
            {
                "validationType": 4,
                "mobile": self._mobile,
                "customerType": "login",
                "channel": self._channel,
            },
            include_token=False,
        )
        if data.get("code") != 0:
            raise ShenzhenWaterApiError(data.get("message") or "Failed to send SMS code")

    async def async_login(self, validation_code: str) -> tuple[str, str]:
        data = await self._invoke(
            "op/user/LoginV20",
            {
                "mobile": self._mobile,
                "validationNum": validation_code,
                "validationType": 4,
                "openid": self._mobile,
                "channel": self._channel,
            },
            include_token=False,
        )
        if data.get("code") != 0 or not isinstance(data.get("data"), dict):
            raise ShenzhenWaterApiError(data.get("message") or "Login failed")
        result = data["data"]
        token = result.get("token")
        guid = result.get("guid")
        if not token or guid is None:
            raise ShenzhenWaterApiError("Login response did not include token/guid")
        self._token = str(token)
        self._guid = str(guid)
        return self._token, self._guid

    async def async_fetch(self) -> ShenzhenWaterData:
        if not self._token or not self._guid:
            raise ShenzhenWaterAuthError("Missing token/guid; reauthentication required")

        response = await self._invoke(
            "op/BillInfo/GetLatestBillDetails2V30",
            {
                "customerType": "details",
                "customercodelist": self._customer_codes,
                "channel": self._channel,
                "openid": self._mobile,
                "guid": self._guid,
            },
        )
        if response.get("code") != 0:
            raise ShenzhenWaterApiError(response.get("message") or "Bill query failed")
        bills = tuple(_parse_bill(item) for item in response.get("data", []) if isinstance(item, dict))
        return ShenzhenWaterData(
            latest_bill=bills[0] if bills else None,
            bills=bills,
            raw=response,
            result_code=response.get("code"),
            result_message=response.get("message"),
        )

    async def _invoke(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        include_token: bool = True,
    ) -> dict[str, Any]:
        request_header = random_header()
        headers = {
            "04A52C9F": request_header,
            "Accept": "application/json, text/plain, */*",
            "Channel": self._channel,
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.82137777.com",
            "Referer": "https://www.82137777.com/",
            "TenantId": self._tenant_id,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            ),
        }
        if include_token:
            headers["Utoken"] = self._token
            headers["OpenId"] = self._mobile

        try:
            async with self._session.post(
                f"{self._base_url}/{endpoint}",
                headers=headers,
                data=encrypt_payload(payload, request_header),
                timeout=30,
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
                    raise ShenzhenWaterAuthError(f"HTTP {response.status}: {text}")
                if response.status >= 400:
                    raise ShenzhenWaterApiError(f"HTTP {response.status}: {text}")
                response_header = response.headers.get("04A52C9F")
                if not response_header:
                    raise ShenzhenWaterApiError("Missing 04A52C9F response header")
        except ClientError as err:
            raise ShenzhenWaterApiError("Request failed") from err
        except TimeoutError as err:
            raise ShenzhenWaterApiError("Request timed out") from err

        try:
            data = decrypt_response(text, response_header)
        except (ValueError, KeyError) as err:
            raise ShenzhenWaterApiError("Could not decrypt response") from err
        if not isinstance(data, dict):
            raise ShenzhenWaterApiError("Response JSON is not an object")
        if include_token and str(data.get("code")) == "9999904":
            raise ShenzhenWaterAuthError(data.get("message") or "Authentication expired")
        return data


def _parse_bill(raw: dict[str, Any]) -> ShenzhenWaterBill:
    meter = raw.get("meterWaterUses")
    meter_item = meter[0] if isinstance(meter, list) and meter and isinstance(meter[0], dict) else {}
    return ShenzhenWaterBill(
        bill_month=_stringify(raw.get("costDate")),
        customer_code=_stringify(raw.get("customerCode")),
        total_amount=_float(raw.get("totalAmount")),
        water_amount=_float(raw.get("waterAmount")),
        sewage_amount=_float(raw.get("sewageAmount")),
        garbage_amount=_float(raw.get("garbageAmount")),
        late_fee=_float(raw.get("lateFee")),
        need_pay=_float(raw.get("needpay")),
        water_consumption=_float(raw.get("waterConsumption")),
        water_after_reduced=_float(raw.get("waterAfterReduced")),
        due_date=_stringify(raw.get("dueDate")),
        payment_status=_stringify(raw.get("paymentStatus")),
        water_status=_stringify(raw.get("waterStatus")),
        sewage_status=_stringify(raw.get("sewageStatus")),
        garbage_status=_stringify(raw.get("garbageStatus")),
        meter_code=_stringify(meter_item.get("waterMeterCode")),
        meter_current_reading=_float(meter_item.get("waterNumber")),
        meter_previous_reading=_float(meter_item.get("waterNumberPreTime")),
        meter_current_date=_stringify(meter_item.get("meterCheckMonDate")),
        meter_previous_date=_stringify(meter_item.get("meterCheckPreDate")),
        water_use_days=_int(meter_item.get("waterUseDays")),
        raw=raw,
    )


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stringify(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
