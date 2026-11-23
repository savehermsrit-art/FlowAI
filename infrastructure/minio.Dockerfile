# Source-only MinIO distribution, built locally from Go's verified module proxy.
# GOPROXY has no direct fallback: no Git checkout or repository connection occurs.
FROM golang:1.25-bookworm AS build
ENV GOPROXY=https://proxy.golang.org CGO_ENABLED=0
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build for attempt in 1 2 3; do go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z && exit 0; done; exit 1
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/* && useradd --uid 10002 minio && mkdir /data && chown minio:minio /data
COPY --from=build /go/bin/minio /usr/local/bin/minio
USER minio
ENTRYPOINT ["minio"]
