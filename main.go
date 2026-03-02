package main

import (
	"fmt"
	"log"
	"os"
	"savetune/db"
	"savetune/downloader"
	"savetune/handlers"
	"savetune/spotify"
	"time"

	// Use modernc.org/sqlite, not github.com/mattn/go-sqlite3
	"github.com/gin-gonic/gin"
	_ "modernc.org/sqlite"
)

func main() {
	// Read all config from env (set by GoService.java)
	host := getEnv("HOST", "127.0.0.1")
	port := getEnv("PORT", "7799")
	dbPath := getEnv("DB_PATH", "./savetune.db")
	downloadDir := getEnv("DOWNLOAD_DIR", "./downloads")
	ffmpegPath := getEnv("FFMPEG_PATH", "ffmpeg")

	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Printf("=== SaveTune Server Starting ===")
	log.Printf("Bind:     %s:%s", host, port)
	log.Printf("DB:       %s", dbPath)
	log.Printf("Downloads:%s", downloadDir)
	log.Printf("FFmpeg:   %s", ffmpegPath)

	// Create download dir
	if err := os.MkdirAll(downloadDir, 0755); err != nil {
		log.Printf("Warning: could not create download dir: %v", err)
	}

	// Init DB
	if err := db.InitDB(dbPath); err != nil {
		log.Fatalf("FATAL: DB init failed: %v", err)
	}
	defer db.CloseDB()
	log.Printf("DB initialized: %s", dbPath)

	downloader.InitEngine()

	// Init Gin
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// Health check — Flutter polls this to know server is ready
	r.GET("/api/v1/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":        "ok",
			"timestamp":     time.Now().Unix(),
			"version":       "1.0.0",
			"authenticated": spotify.IsAuthenticated(),
		})
	})

	// All other routes
	v1 := r.Group("/api/v1")
	{
		v1.POST("/config/spdc", handlers.SetSpDc)
		v1.GET("/config", handlers.GetConfig)
		v1.GET("/search", handlers.Search)
		v1.POST("/download", handlers.QueueDownload)
		v1.GET("/download/:id", handlers.GetDownloadStatus)
		v1.GET("/library", handlers.GetLibrary)
		v1.DELETE("/library/:id", handlers.DeleteLibraryItem)
		v1.GET("/lyrics/:spotify_id", handlers.GetLyrics)
	}
	r.GET("/ws/downloads", handlers.WebSocketDownloads)

	addr := fmt.Sprintf("%s:%s", host, port)
	log.Printf("Server ready on http://%s", addr)
	log.Printf("Health: http://%s/api/v1/health", addr)

	if err := r.Run(addr); err != nil {
		log.Fatalf("FATAL: Server failed: %v", err)
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
