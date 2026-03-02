package handlers

import "github.com/gin-gonic/gin"

func GetLibrary(c *gin.Context) {
    c.JSON(200, gin.H{"tracks": []map[string]interface{}{{"id": "1", "title": "Mock Track"}}, "total": 1})
}

func DeleteLibraryItem(c *gin.Context) {
    c.JSON(200, gin.H{"status": "deleted", "id": c.Param("id")})
}
