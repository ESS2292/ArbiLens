"""Create the configured S3 bucket when a local emulator starts empty."""

import time

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.services.storage import get_s3_client


def main() -> None:
    settings = get_settings()
    client = get_s3_client()
    name = settings.s3_bucket
    for _attempt in range(30):
        try:
            names = {bucket["Name"] for bucket in client.list_buckets().get("Buckets", [])}
            if name not in names:
                client.create_bucket(Bucket=name)
            return
        except (BotoCoreError, ClientError, OSError):
            time.sleep(1)
    raise SystemExit(f"Could not create bucket {name}.")


if __name__ == "__main__":
    main()
