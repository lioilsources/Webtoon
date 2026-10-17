// Package db holds the schema migrations (embedded, run on startup) and the sqlc-generated queries (dbq).
package db

import (
	"embed"
	"errors"
	"fmt"
	"strings"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5" // pgx5:// driver
	"github.com/golang-migrate/migrate/v4/source/iofs"
)

//go:embed migrations/*.sql
var migrations embed.FS

// Migrate applies all pending up-migrations to databaseURL (postgres:// or postgresql://).
func Migrate(databaseURL string) error {
	src, err := iofs.New(migrations, "migrations")
	if err != nil {
		return err
	}
	u := databaseURL
	for _, p := range []string{"postgres://", "postgresql://"} {
		if strings.HasPrefix(u, p) {
			u = "pgx5://" + strings.TrimPrefix(u, p)
			break
		}
	}
	m, err := migrate.NewWithSourceInstance("iofs", src, u)
	if err != nil {
		return fmt.Errorf("migrate init: %w", err)
	}
	defer m.Close()
	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("migrate up: %w", err)
	}
	return nil
}
