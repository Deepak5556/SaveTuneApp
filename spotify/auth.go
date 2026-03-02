package spotify

import (
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

type tokenStore struct {
    mu          sync.RWMutex
    accessToken string
    expiresAt   time.Time
    spDc        string
}

var store = &tokenStore{}

type tokenResponse struct {
    AccessToken     string `json:"accessToken"`
    ExpirationMs    int64  `json:"accessTokenExpirationTimestampMs"`
    IsAnonymous     bool   `json:"isAnonymous"`
    ClientID        string `json:"clientId"`
}

func SetSpDc(spDc string) error {
    token, err := fetchNewToken(spDc)
    if err != nil { return err }
    store.mu.Lock()
    store.spDc        = spDc
    store.accessToken = token.AccessToken
    store.expiresAt   = time.UnixMilli(token.ExpirationMs)
    store.mu.Unlock()
    go autoRefreshLoop()
    return nil
}

func GetToken() (string, error) {
    store.mu.RLock()
    token   := store.accessToken
    expires := store.expiresAt
    spDc    := store.spDc
    store.mu.RUnlock()

    if token == "" {
        return "", fmt.Errorf("not authenticated: no sp_dc set")
    }
    if time.Now().After(expires.Add(-60 * time.Second)) {
        newToken, err := fetchNewToken(spDc)
        if err != nil { return "", err }
        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()
        return newToken.AccessToken, nil
    }
    return token, nil
}

func IsAuthenticated() bool {
    store.mu.RLock()
    defer store.mu.RUnlock()
    return store.spDc != "" && store.accessToken != "" && time.Now().Before(store.expiresAt)
}

func fetchNewToken(spDc string) (*tokenResponse, error) {
    client := &http.Client{Timeout: 10 * time.Second}
    req, err := http.NewRequest("GET",
        "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
        nil)
    if err != nil { return nil, err }

    req.Header.Set("Cookie",                  "sp_dc="+spDc)
    req.Header.Set("User-Agent",              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    req.Header.Set("Accept",                  "application/json")
    req.Header.Set("App-platform",            "WebPlayer")
    req.Header.Set("spotify-app-version",     "1.2.46.25.g7f189073")
    req.Header.Set("Sec-Fetch-Dest",          "empty")
    req.Header.Set("Sec-Fetch-Mode",          "cors")
    req.Header.Set("Sec-Fetch-Site",          "same-origin")

    resp, err := client.Do(req)
    if err != nil { return nil, fmt.Errorf("network error: %w", err) }
    defer resp.Body.Close()

    if resp.StatusCode == 401 { return nil, fmt.Errorf("sp_dc is invalid or expired") }
    if resp.StatusCode != 200 { return nil, fmt.Errorf("spotify returned status %d", resp.StatusCode) }

    var result tokenResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("failed to parse token response: %w", err)
    }
    if result.IsAnonymous {
        return nil, fmt.Errorf("sp_dc is invalid — got anonymous session")
    }
    if result.AccessToken == "" {
        return nil, fmt.Errorf("spotify returned empty access token")
    }
    return &result, nil
}

func autoRefreshLoop() {
    for {
        store.mu.RLock()
        expires := store.expiresAt
        spDc    := store.spDc
        store.mu.RUnlock()

        if spDc == "" {
            time.Sleep(60 * time.Second)
            continue
        }

        sleepUntil := expires.Add(-90 * time.Second)
        sleepDuration := time.Until(sleepUntil)
        if sleepDuration > 0 {
            time.Sleep(sleepDuration)
        }

        newToken, err := fetchNewToken(spDc)
        if err != nil { time.Sleep(30 * time.Second); continue }

        store.mu.Lock()
        store.accessToken = newToken.AccessToken
        store.expiresAt   = time.UnixMilli(newToken.ExpirationMs)
        store.mu.Unlock()
    }
}
