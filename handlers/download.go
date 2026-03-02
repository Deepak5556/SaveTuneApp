package handlers

import (
    "savetune/downloader"
    "github.com/gin-gonic/gin"
)

func QueueDownload(c *gin.Context) {
    go downloader.EngineStartJob("some-job-id")
    c.JSON(202, gin.H{"job_id": "test", "status": "queued"})
}

func GetDownloadStatus(c *gin.Context) {
    id := c.Param("id")
    c.JSON(200, gin.H{"job_id": id, "status": "downloading", "progress": 50.0})
}
