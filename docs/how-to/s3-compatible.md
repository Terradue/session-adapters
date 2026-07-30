# Use an S3-compatible service

Pass the service endpoint to `S3Adapter`. Credentials may still come from the
boto3 credential chain:

```python
import requests
from botocore.config import Config

from session_adapters.s3_adapter import S3Adapter

adapter = S3Adapter(
    endpoint_url="https://objects.example.com",
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),
)

session = requests.Session()
session.mount("s3://", adapter)

response = session.get("s3://example-bucket/path/to/object")
```

For a local development service, explicit credentials can be supplied:

```python
adapter = S3Adapter(
    endpoint_url="http://127.0.0.1:9000",
    region_name="us-east-1",
    aws_access_key_id="development-access-key",
    aws_secret_access_key="development-secret-key",
)
```

!!! warning "Protect credentials"

    Load real credentials from environment variables or a secret manager.
    Avoid embedding them in application code. Whether TLS verification and
    addressing styles are required depends on the selected service.

Backend compatibility ultimately depends on the service's implementation of
the boto3 operations used by the adapter: `HeadObject`, `GetObject`,
`PutObject`, `DeleteObject`, and `ListObjectsV2`.
