package spotify

import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "strconv"
    "time"
)

type Track struct {
    ID         string `json:"id"`
    Name       string `json:"name"`
    Artist     string `json:"artist"`
    Album      string `json:"album"`
    DurationMs int    `json:"duration_ms"`
    CoverURL   string `json:"cover_url"`
}

type SearchResult struct {
    Tracks []Track `json:"tracks"`
    Total  int     `json:"total"`
    Offset int     `json:"offset"`
    Limit  int     `json:"limit"`
}

func Search(query, searchType string, limit, offset int) (*SearchResult, error) {
    if !IsAuthenticated() {
        return nil, fmt.Errorf("not authenticated: please set sp_dc in settings")
    }

    token, err := GetToken()
    if err != nil { return nil, err }

    params := url.Values{}
    params.Set("q",      query)
    params.Set("type",   searchType) // "track", "album", "playlist"
    params.Set("limit",  strconv.Itoa(limit))
    params.Set("offset", strconv.Itoa(offset))
    params.Set("market", "from_token")

    req, _ := http.NewRequest("GET",
        "https://api.spotify.com/v1/search?"+params.Encode(), nil)
    req.Header.Set("Authorization", "Bearer "+token)
    req.Header.Set("Accept",        "application/json")
    req.Header.Set("App-platform",  "WebPlayer")
    req.Header.Set("User-Agent",    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    client := &http.Client{Timeout: 10 * time.Second}
    resp, err := client.Do(req)
    if err != nil { return nil, fmt.Errorf("search network error: %w", err) }
    defer resp.Body.Close()

    // Token expired — refresh and retry once
    if resp.StatusCode == 401 {
        store.mu.RLock()
        spDc := store.spDc
        store.mu.RUnlock()

        newToken, err := fetchNewToken(spDc)
        if err != nil { return nil, fmt.Errorf("session expired: please re-enter sp_dc") }

        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()

        return Search(query, searchType, limit, offset) // retry once
    }

    if resp.StatusCode == 429 {
        retryAfter := resp.Header.Get("Retry-After")
        return nil, fmt.Errorf("rate limited by Spotify. Wait %s seconds", retryAfter)
    }

    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("spotify search returned status %d", resp.StatusCode)
    }

    var raw map[string]json.RawMessage
    json.NewDecoder(resp.Body).Decode(&raw)

    result := &SearchResult{Offset: offset, Limit: limit}

    // Parse tracks
    if tracksRaw, ok := raw["tracks"]; ok {
        var tracksWrapper struct {
            Items []struct {
                ID      string `json:"id"`
                Name    string `json:"name"`
                Artists []struct{ Name string `json:"name"` } `json:"artists"`
                Album   struct {
                    Name   string `json:"name"`
                    Images []struct{ URL string `json:"url"` } `json:"images"`
                } `json:"album"`
                DurationMs int `json:"duration_ms"`
            } `json:"items"`
            Total int `json:"total"`
        }
        json.Unmarshal(tracksRaw, &tracksWrapper)
        result.Total = tracksWrapper.Total
        for _, item := range tracksWrapper.Items {
            coverURL := ""
            if len(item.Album.Images) > 0 { coverURL = item.Album.Images[0].URL }
            artistName := ""
            if len(item.Artists) > 0 { artistName = item.Artists[0].Name }
            result.Tracks = append(result.Tracks, Track{
                ID:         item.ID,
                Name:       item.Name,
                Artist:     artistName,
                Album:      item.Album.Name,
                DurationMs: item.DurationMs,
                CoverURL:   coverURL,
            })
        }
    }

    return result, nil
}
