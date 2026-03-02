package handlers

import "github.com/gin-gonic/gin"

func GetLyrics(c *gin.Context) {
    id := c.Param("spotify_id")
    c.JSON(200, gin.H{"lines": []map[string]interface{}{{"time": 0, "text": "Mock lyrics for " + id}}})
}
