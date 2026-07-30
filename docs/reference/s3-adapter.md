# `S3Adapter`

::: session_adapters.s3_adapter.S3Adapter
    options:
      members:
        - __init__
        - close

## Constructor parameters

All constructor parameters are optional and are passed to `boto3.client("s3",
...)`.

| Parameter | Purpose |
| --- | --- |
| `region_name` | AWS region or service-specific region |
| `aws_access_key_id` | Explicit access key |
| `aws_secret_access_key` | Explicit secret key |
| `aws_session_token` | Explicit temporary session token |
| `endpoint_url` | Override the S3 endpoint |
| `config` | A botocore-compatible client configuration object |

When explicit credentials are omitted, boto3 resolves credentials through its
normal provider chain.

## `GET` object query parameters

| Query parameter | boto3 argument | Example value |
| --- | --- | --- |
| `range` | `Range` | `bytes=0-99` |
| `versionId` | `VersionId` | `example-version` |

The adapter uses the first value when a parameter is repeated.

## `PUT` header mapping

| Request header | boto3 argument |
| --- | --- |
| `Content-Type` | `ContentType` |
| `Cache-Control` | `CacheControl` |
| `Content-Encoding` | `ContentEncoding` |
| `Content-Language` | `ContentLanguage` |
| `Content-Disposition` | `ContentDisposition` |

A string request body is UTF-8 encoded before being passed as `Body`.

## `PUT` encryption query parameters

| Query | boto3 arguments |
| --- | --- |
| `sse=AES256` | `ServerSideEncryption="AES256"` |
| `sse=aws:kms` | `ServerSideEncryption="aws:kms"` |
| `sse=aws:kms&kmsKeyId=ID` | Also sets `SSEKMSKeyId="ID"` |

Other `sse` values are ignored.

## Prefix listings

An empty key or a key ending in `/` invokes `list_objects_v2`.

| Query parameter | boto3 argument |
| --- | --- |
| `delimiter` | `Delimiter` |
| `maxKeys` | `MaxKeys`, converted to `int` |

The response content type is `application/json`:

```json
{
  "KeyCount": 1,
  "IsTruncated": false,
  "Contents": [
    {
      "Key": "folder/file.txt",
      "Size": 7,
      "ETag": "etag123"
    }
  ],
  "CommonPrefixes": ["folder/sub/"]
}
```

The adapter copies HTTP headers from
`ResponseMetadata.HTTPHeaders` into the Requests response.
