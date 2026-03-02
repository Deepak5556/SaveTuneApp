import os

files = {
    "handlers/config.go": """package handlers
import (
	"savetune/spotify"
	"github.com/gin-gonic/gin"
)
type ConfigReq struct {
	SPDC string `json:"sp_dc"`
}
func ConfigSPDC(c *gin.Context) {
	var req ConfigReq
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": "Invalid request"})
		return
	}
	if err := spotify.SetSPDC(req.SPDC); err != nil {
		c.JSON(401, gin.H{"error": err.Error(), "code": "AUTH_FAILED"})
		return
	}
	c.JSON(200, gin.H{"valid": true, "display_name": "User"})
}""",
    "handlers/search.go": """package handlers
import (
	"savetune/spotify"
	"github.com/gin-gonic/gin"
	"strconv"
)
func Search(c *gin.Context) {
	q := c.Query("q")
	typ := c.Query("type")
    res, err := spotify.Search(spotify.SearchParams{Query: q, Type: typ, Limit: 20})
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, res)
}""",
    "handlers/download.go": """package handlers
import (
    "savetune/downloader"
	"github.com/gin-gonic/gin"
)
func QueueDownload(c *gin.Context) {
    downloader.QueueDownload()
	c.JSON(202, gin.H{"job_id": "test", "status": "queued"})
}
func GetDownloadStatus(c *gin.Context) {
	id := c.Param("id")
	c.JSON(200, gin.H{"job_id": id, "status": "queued"})
}""",
    "handlers/library.go": """package handlers
import "github.com/gin-gonic/gin"
func GetLibrary(c *gin.Context) {
	c.JSON(200, gin.H{"tracks": []string{}, "total": 0})
}
func DeleteLibraryItem(c *gin.Context) {
	c.JSON(200, gin.H{"status": "deleted"})
}""",
    "handlers/lyrics.go": """package handlers
import "github.com/gin-gonic/gin"
func GetLyrics(c *gin.Context) {
	c.JSON(200, gin.H{"lines": []string{}})
}""",
    "handlers/websocket.go": """package handlers
import "github.com/gin-gonic/gin"
func WebSocketDownloads(c *gin.Context) {
}""",
    "downloader/engine.go": """package downloader
func InitEngine() {}
func QueueDownload() {}""",
    "downloader/ffmpeg.go": """package downloader
func ExtractAndEmbed() {}""",
    "downloader/metadata.go": """package downloader
func WriteTags() {}""",
    "spotify/track.go": """package spotify
func GetTrackCDN() {}""",
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
print("Go stubs generated.")
