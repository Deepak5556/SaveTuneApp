package handlers

import (
    "strings"
    "savetune/spotify"
    "github.com/gin-gonic/gin"
)

func SetSpDc(c *gin.Context) {
    var req struct {
        SpDc string `json:"sp_dc" binding:"required"`
    }
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": "sp_dc field is required", "code": "MISSING_SPDC"})
        return
    }

    spDc := strings.TrimSpace(req.SpDc)
    if len(spDc) < 100 {
        c.JSON(400, gin.H{
            "error": "sp_dc looks too short. Make sure you copied the entire cookie value.",
            "code":  "INVALID_FORMAT",
        })
        return
    }

    if err := spotify.SetSpDc(spDc); err != nil {
        c.JSON(401, gin.H{"error": err.Error(), "code": "AUTH_FAILED"})
        return
    }

    c.JSON(200, gin.H{"valid": true, "message": "Successfully connected to Spotify"})
}

func GetConfig(c *gin.Context) {
    c.JSON(200, gin.H{
        "authenticated": spotify.IsAuthenticated(),
        "sp_dc_set":     spotify.IsAuthenticated(),
    })
}
