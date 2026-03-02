package db

import "fmt"

func InsertDownloadJob(jobID, spotifyID string) error {
	stmt, err := DB.Prepare("INSERT INTO download_queue (job_id, spotify_id, status, progress, speed_kbps, queued_at) VALUES (?, ?, 'queued', 0, 0, CURRENT_TIMESTAMP)")
	if err != nil {
		return err
	}
	defer stmt.Close()
	_, err = stmt.Exec(jobID, spotifyID)
	return err
}

func UpdateDownloadProgress(jobID string, progress, speed float64, status string) error {
	stmt, err := DB.Prepare("UPDATE download_queue SET progress = ?, speed_kbps = ?, status = ? WHERE job_id = ?")
	if err != nil {
		return err
	}
	defer stmt.Close()
	_, err = stmt.Exec(progress, speed, status, jobID)
	return err
}

func GetDownloadJob(jobID string) (map[string]interface{}, error) {
	fmt.Println("Fetching download state for job:", jobID)
	return map[string]interface{}{"status": "downloading", "progress": 50}, nil
}
