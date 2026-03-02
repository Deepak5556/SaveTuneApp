package db

import (
	"database/sql"
	"fmt"
	"log"

	_ "modernc.org/sqlite"
)

var DB *sql.DB

// InitDB initializes SQLite and creates tables via IF NOT EXISTS migrations.
func InitDB(filepath string) error {
	var err error
	DB, err = sql.Open("sqlite", filepath)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	migrations := []string{
		`CREATE TABLE IF NOT EXISTS tracks (id TEXT PRIMARY KEY, spotify_id TEXT UNIQUE, title TEXT, artist TEXT, album TEXT, duration_ms INTEGER, cover_url TEXT, file_path TEXT, format TEXT, bitrate INTEGER, downloaded_at DATETIME)`,
		`CREATE TABLE IF NOT EXISTS playlists (id TEXT PRIMARY KEY, name TEXT, cover_url TEXT, track_count INTEGER)`,
		`CREATE TABLE IF NOT EXISTS playlist_tracks (playlist_id TEXT, track_id TEXT, position INTEGER, PRIMARY KEY(playlist_id, track_id))`,
		`CREATE TABLE IF NOT EXISTS lyrics (spotify_id TEXT PRIMARY KEY, lines TEXT, fetched_at DATETIME)`,
		`CREATE TABLE IF NOT EXISTS download_queue (job_id TEXT PRIMARY KEY, spotify_id TEXT, status TEXT, progress REAL, speed_kbps REAL, file_path TEXT, error TEXT, queued_at DATETIME)`,
		`CREATE TABLE IF NOT EXISTS api_cache (query_key TEXT PRIMARY KEY, response TEXT, expires_at DATETIME)`,
		`CREATE TABLE IF NOT EXISTS favorites (spotify_id TEXT PRIMARY KEY, added_at DATETIME)`,
	}

	for _, m := range migrations {
		if _, err := DB.Exec(m); err != nil {
			return fmt.Errorf("migration error: %w", err)
		}
	}

	log.Println("SQLite database initialized successfully")
	return nil
}

// CloseDB closes the database connection.
func CloseDB() {
	if DB != nil {
		DB.Close()
	}
}
