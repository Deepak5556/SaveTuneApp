package handlers

import (
    "strconv"
    "strings"
    "savetune/spotify"
    "github.com/gin-gonic/gin"
)

func Search(c *gin.Context) {
    if !spotify.IsAuthenticated() {
        c.JSON(401, gin.H{
            "error": "Not connected to Spotify. Please enter your sp_dc key in Settings.",
            "code":  "NOT_AUTHENTICATED",
        })
        return
    }

    query      := c.Query("q")
    searchType := c.DefaultQuery("type", "track")
    limit, _   := strconv.Atoi(c.DefaultQuery("limit", "20"))
    offset, _  := strconv.Atoi(c.DefaultQuery("offset", "0"))

    if strings.TrimSpace(query) == "" {
        c.JSON(400, gin.H{"error": "Search query cannot be empty", "code": "EMPTY_QUERY"})
        return
    }

    results, err := spotify.Search(query, searchType, limit, offset)
    if err != nil {
        code := "SEARCH_ERROR"
        if strings.Contains(err.Error(), "session expired") { code = "SESSION_EXPIRED" }
        if strings.Contains(err.Error(), "rate limited")    { code = "RATE_LIMITED" }
        c.JSON(500, gin.H{"error": err.Error(), "code": code})
        return
    }

    c.JSON(200, results)
}
