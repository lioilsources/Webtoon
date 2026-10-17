FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -o /webtoon ./cmd/webtoon

FROM alpine:3
RUN apk add --no-cache ca-certificates
COPY --from=builder /webtoon /webtoon
ENTRYPOINT ["/webtoon"]
CMD ["serve"]
