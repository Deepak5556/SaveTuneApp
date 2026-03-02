package downloader

import (
    "fmt"
    "sync"
)

var wg sync.WaitGroup

func InitEngine() {
    fmt.Println("Engine initialized with concurrent workers")
}

func QueueDownload() {}

func EngineStartJob(jobID string) {
    wg.Add(1)
    go func() {
        defer wg.Done()
        fmt.Println("Processing job:", jobID)
        ExtractAndEmbed()
    }()
}
