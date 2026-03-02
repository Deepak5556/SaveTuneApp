package handlers

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

func WebSocketDownloads(c *gin.Context) {
    c.String(http.StatusOK, "WebSocket Connection Established")
}
