FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -o /webtoon ./cmd/webtoon

# Spark voice worker (deploy/voice-worker): `webtoon voice-worker` needs ffmpeg for trim + loudnorm.
#   docker build --target voice-worker .
FROM alpine:3.22 AS voice-worker
RUN apk add --no-cache ffmpeg ca-certificates tzdata \
 && adduser -D -H -u 65532 nonroot
COPY --from=builder /webtoon /webtoon
USER 65532:65532
ENTRYPOINT ["/webtoon"]
CMD ["voice-worker"]

# API (JODA, deploy/docker-compose.yml): the default target, stays the last stage.
FROM alpine:3
RUN apk add --no-cache ca-certificates
COPY --from=builder /webtoon /webtoon
ENTRYPOINT ["/webtoon"]
CMD ["serve"]
