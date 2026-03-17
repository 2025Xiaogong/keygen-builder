# By Hitachi_Mako 233!!  hitachimako @52pojie

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta


ALPHABET = "DY14UF3RHWCXLQB6IKJT9N5AGS2PM8VZ7E"
ALPHABET_INDEX = {char: idx for idx, char in enumerate(ALPHABET)}

MIN_BASE_DATE = date(2004, 1, 1)
MAX_BASE_DATE = date(2034, 12, 31)
MAX_OFFSET_DAYS = 3652
DEFAULT_FIELD_5_6 = 6
DEFAULT_FIELD_7_8 = 1
AUTO_VARIANT_FOR_PRODUCT_1 = 100

ALLOWED_VARIANT_VALUES = (
    100,
    120,
    150,
    160,
    170,
    180,
    200,
    220,
    230,
    250,
    260,
    270,
    280,
    300,
    320,
    400,
    430,
    450,
    460,
    500,
    520,
    530,
    550,
    560,
    570,
    580,
    590,
    592,
    595,
    597,
    598,
    599,
    600,
    610,
    620,
    625,
    630,
    632,
    633,
    650,
    660,
    670,
    675,
    685,
    688,
    690,
    692,
    694,
    700,
    720,
    730,
    735,
    740,
    750,
    760,
    765,
    770,
    800,
)


def base34_encode(value: int, width: int) -> str:
    limit = 34**width
    if not 0 <= value < limit:
        raise ValueError(f"value {value} does not fit into {width} base-34 chars")
    chars = ["D"] * width
    for idx in range(width - 1, -1, -1):
        chars[idx] = ALPHABET[value % 34]
        value //= 34
    return "".join(chars)


def base34_decode(text: str) -> int:
    value = 0
    for char in text:
        value = value * 34 + ALPHABET_INDEX[char]
    return value


def crc16_like(text: str) -> int:
    value = 0
    for char in text:
        value ^= ord(char) << 8
        for _ in range(8):
            if value & 0x8000:
                value = ((value << 1) ^ 0x8201) & 0xFFFF
            else:
                value = (value << 1) & 0xFFFF
    return value


def checksum_char(first24: str) -> str:
    return base34_encode(crc16_like(first24) % 0x9987, 3)[1]


def normalize_key(text: str) -> str:
    key = "".join(char for char in text.upper() if char in ALPHABET)
    if len(key) != 25:
        raise ValueError("product key must contain exactly 25 alphabet chars after separators are removed")
    return key


def group_key(raw_key: str) -> str:
    return "-".join(raw_key[idx : idx + 5] for idx in range(0, 25, 5))


def parse_date(text: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError("date must be YYYY-MM-DD, YYYY/MM/DD, or YYYY.MM.DD")


def prompt_value(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default if default is not None else "")


def serial_limit_for_product(product_id: int) -> int:
    return 65533 if product_id in (1, 4) else 776


def allowed_variant_code(product_id: int, variant_code: int) -> bool:
    if product_id == 4 and variant_code < 320:
        return False
    return variant_code in ALLOWED_VARIANT_VALUES or 820 <= variant_code <= 999


def minimum_variant_code(product_id: int) -> int:
    return 320 if product_id == 4 else ALLOWED_VARIANT_VALUES[0]


def variant_hint(product_id: int) -> str:
    values = [value for value in ALLOWED_VARIANT_VALUES if product_id != 4 or value >= 320]
    return ", ".join(str(value) for value in values) + ", 820-999"


def pack_base_date(base_date: date) -> int:
    if not MIN_BASE_DATE <= base_date <= MAX_BASE_DATE:
        raise ValueError(f"base date must be between {MIN_BASE_DATE} and {MAX_BASE_DATE}")
    return ((base_date.year - 2003) & 0x1F) << 9 | ((base_date.month & 0xF) << 5) | (base_date.day & 0x1F)


def derive_serial(
    product_id: int,
    variant_code: int,
    packed_date: int,
    expire_offset: int,
    version_offset: int,
) -> int:
    mix = (
        product_id * 0x45D
        + variant_code * 0x11
        + packed_date * 3
        + expire_offset * 5
        + version_offset * 7
    )
    return mix % serial_limit_for_product(product_id) + 1


def derive_seed(
    product_id: int,
    variant_code: int,
    packed_date: int,
    expire_offset: int,
    version_offset: int,
    serial: int,
) -> int:
    mix = (
        serial
        + product_id * 0x31
        + variant_code * 0x17
        + packed_date
        + expire_offset * 7
        + version_offset * 11
    )
    return mix % (34 * 34)


def decode_key(raw_key: str) -> dict:
    key = normalize_key(raw_key)
    seed = base34_decode(key[22:24])
    seed_low = seed & 0xFF
    product_id = base34_decode(key[0:2]) ^ seed_low ^ 0xBF
    variant_code = base34_decode(key[2:4]) ^ seed_low ^ 0xED
    field_5_6 = base34_decode(key[4:6]) ^ seed_low ^ 0x77
    field_7_8 = base34_decode(key[6:8]) ^ seed_low ^ 0xDF
    serial = base34_decode(key[8:12]) ^ seed ^ 0x4755
    packed_date = base34_decode(key[12:16]) ^ seed ^ 0x7CC1
    base_date = date(((packed_date >> 9) & 0x1F) + 2003, (packed_date >> 5) & 0xF, packed_date & 0x1F)
    expire_offset = base34_decode(key[16:19]) ^ seed_low ^ 0x3FD
    version_offset = base34_decode(key[19:22]) ^ seed_low ^ 0x935
    return {
        "product_id": product_id,
        "variant_code": variant_code,
        "field_5_6": field_5_6,
        "field_7_8": field_7_8,
        "serial": serial,
        "seed": seed,
        "base_date": base_date,
        "expire_offset": expire_offset,
        "expire_date": base_date + timedelta(days=expire_offset),
        "version_offset": version_offset,
        "version_limit_date": base_date + timedelta(days=version_offset),
        "checksum_ok": key[24] == checksum_char(key[:24]),
    }


def validate_layout(decoded: dict) -> bool:
    try:
        pack_base_date(decoded["base_date"])
    except ValueError:
        return False
    return (
        decoded["checksum_ok"]
        and 1 <= decoded["product_id"] <= 999
        and allowed_variant_code(decoded["product_id"], decoded["variant_code"])
        and 1 <= decoded["field_5_6"] <= 15
        and 1 <= decoded["field_7_8"] <= 15
        and 0 <= decoded["expire_offset"] <= MAX_OFFSET_DAYS
        and 1 <= decoded["version_offset"] <= MAX_OFFSET_DAYS
        and 0 < decoded["serial"] <= serial_limit_for_product(decoded["product_id"])
        and 0 <= decoded["seed"] < 34 * 34
    )


def validate_current_sample(decoded: dict) -> bool:
    return (
        validate_layout(decoded)
        and decoded["product_id"] == 1
        and decoded["variant_code"] != 999
        and decoded["field_5_6"] <= 100
        and decoded["field_7_8"] <= 100
        and decoded["serial"] != 0xFFFF
        and decoded["expire_offset"] < 3653
        and decoded["version_offset"] < 3653
    )


def generate_key(
    product_id: int,
    variant_code: int,
    base_date: date,
    expire_offset: int,
    version_offset: int,
    field_5_6: int = DEFAULT_FIELD_5_6,
    field_7_8: int = DEFAULT_FIELD_7_8,
) -> dict:
    if not 1 <= product_id <= 999:
        raise ValueError("product id must be in 1..999")
    if product_id == 1:
        variant_code = AUTO_VARIANT_FOR_PRODUCT_1
    if not allowed_variant_code(product_id, variant_code):
        raise ValueError(f"variant code is invalid for product {product_id}; allowed values: {variant_hint(product_id)}")
    if not 1 <= field_5_6 <= 15:
        raise ValueError("field_5_6 must be in 1..15")
    if not 1 <= field_7_8 <= 15:
        raise ValueError("field_7_8 must be in 1..15")
    if not 0 <= expire_offset <= MAX_OFFSET_DAYS:
        raise ValueError(f"expire offset must be in 0..{MAX_OFFSET_DAYS}")
    if not 1 <= version_offset <= MAX_OFFSET_DAYS:
        raise ValueError(f"version offset must be in 1..{MAX_OFFSET_DAYS}")

    packed_date = pack_base_date(base_date)
    serial = derive_serial(product_id, variant_code, packed_date, expire_offset, version_offset)
    seed = derive_seed(product_id, variant_code, packed_date, expire_offset, version_offset, serial)
    seed_low = seed & 0xFF

    first24 = "".join(
        [
            base34_encode(product_id ^ seed_low ^ 0xBF, 2),
            base34_encode(variant_code ^ seed_low ^ 0xED, 2),
            base34_encode(field_5_6 ^ seed_low ^ 0x77, 2),
            base34_encode(field_7_8 ^ seed_low ^ 0xDF, 2),
            base34_encode(serial ^ seed ^ 0x4755, 4),
            base34_encode(packed_date ^ seed ^ 0x7CC1, 4),
            base34_encode(expire_offset ^ seed_low ^ 0x3FD, 3),
            base34_encode(version_offset ^ seed_low ^ 0x935, 3),
            base34_encode(seed, 2),
        ]
    )
    raw_key = first24 + checksum_char(first24)
    decoded = decode_key(raw_key)

    if not validate_layout(decoded):
        raise RuntimeError("generated key failed the recovered layout checks")

    return {
        "product_id": product_id,
        "variant_code": variant_code,
        "field_5_6": field_5_6,
        "field_7_8": field_7_8,
        "serial": serial,
        "seed": seed,
        "base_date": base_date,
        "expire_offset": expire_offset,
        "expire_date": base_date + timedelta(days=expire_offset),
        "version_offset": version_offset,
        "version_limit_date": base_date + timedelta(days=version_offset),
        "raw_key": raw_key,
        "grouped_key": group_key(raw_key),
        "decoded": decoded,
        "current_sample_ok": validate_current_sample(decoded),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simplified Product Key generator recovered from detailed.md.")
    parser.add_argument("--product-id", type=int, help="Recovered product id. The current sample only fully accepts 1.")
    parser.add_argument("--variant-code", type=int, help="Recovered variant code. Ignored for product id 1.")
    parser.add_argument("--base-date", help=f"Recovered base date ({MIN_BASE_DATE}..{MAX_BASE_DATE}).")
    parser.add_argument("--expire-offset", type=int, help=f"Expire offset in days (0..{MAX_OFFSET_DAYS}).")
    parser.add_argument("--version-offset", type=int, help=f"Version support offset in days (1..{MAX_OFFSET_DAYS}).")
    parser.add_argument("--field-5-6", type=int, default=DEFAULT_FIELD_5_6, help="Field 5..6, valid range 1..15.")
    parser.add_argument("--field-7-8", type=int, default=DEFAULT_FIELD_7_8, help="Field 7..8, valid range 1..15.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    default_base_date = date.today()
    if default_base_date < MIN_BASE_DATE:
        default_base_date = MIN_BASE_DATE
    if default_base_date > MAX_BASE_DATE:
        default_base_date = MAX_BASE_DATE

    product_id_text = str(args.product_id) if args.product_id is not None else prompt_value("Product id", "1")
    product_id = int(product_id_text)

    if product_id == 1:
        variant_code = AUTO_VARIANT_FOR_PRODUCT_1
    else:
        default_variant = minimum_variant_code(product_id)
        variant_prompt = f"Variant code ({variant_hint(product_id)})"
        variant_text = (
            str(args.variant_code)
            if args.variant_code is not None
            else prompt_value(variant_prompt, str(default_variant))
        )
        variant_code = int(variant_text)

    base_date_text = args.base_date or prompt_value("Base date", default_base_date.isoformat())
    expire_offset_text = (
        str(args.expire_offset) if args.expire_offset is not None else prompt_value("Expire offset days", "30")
    )
    version_offset_text = (
        str(args.version_offset) if args.version_offset is not None else prompt_value("Version support offset days", "3652")
    )

    result = generate_key(
        product_id=product_id,
        variant_code=variant_code,
        base_date=parse_date(base_date_text),
        expire_offset=int(expire_offset_text),
        version_offset=int(version_offset_text),
        field_5_6=args.field_5_6,
        field_7_8=args.field_7_8,
    )

    print(f"Product id       : {result['product_id']}")
    if result["product_id"] == 1:
        print(f"Variant code     : {result['variant_code']} (auto-selected for product id 1)")
    else:
        print(f"Variant code     : {result['variant_code']}")
    print(f"Base date        : {result['base_date']}")
    print(f"Expire offset    : {result['expire_offset']} days")
    print(f"Expire date      : {result['expire_date']}")
    print(f"Version offset   : {result['version_offset']} days")
    print(f"Version limit    : {result['version_limit_date']}")
    print(f"Field 5..6       : {result['field_5_6']}")
    print(f"Field 7..8       : {result['field_7_8']}")
    print(f"Serial           : {result['serial']}")
    print(f"Seed             : {result['seed']}")
    print(f"Raw key          : {result['raw_key']}")
    print(f"Grouped key      : {result['grouped_key']}")
    print(f"Checksum ok      : {result['decoded']['checksum_ok']}")
    print(f"Current sample ok: {result['current_sample_ok']}")


if __name__ == "__main__":
    main()
