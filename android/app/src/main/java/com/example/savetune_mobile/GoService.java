package com.example.savetune_mobile;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

public class GoService extends Service {
    private static final String TAG = "SaveTuneGoService";
    private static final String CHANNEL_ID = "savetune_go_channel";
    private static final int NOTIFICATION_ID = 9001;

    private Process serverProcess;
    private volatile boolean running = false;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "GoService onCreate");
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        extractAndStart();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "GoService onStartCommand");
        if (!running || serverProcess == null || !isProcessAlive()) {
            extractAndStart();
        }
        return START_STICKY;
    }

    private boolean isProcessAlive() {
        try {
            serverProcess.exitValue();
            return false; // process ended
        } catch (IllegalThreadStateException e) {
            return true; // still running
        }
    }

    private void extractAndStart() {
        new Thread(() -> {
            try {
                // In Android 10+, binaries must be packaged as native libraries to execute.
                File nativeDir = new File(getApplicationInfo().nativeLibraryDir);
                File serverFile = new File(nativeDir, "libsavetune.so");

                if (!serverFile.exists() || !serverFile.canExecute()) {
                    Log.e(TAG, "FATAL: libsavetune.so not found or not executable in " + nativeDir.getAbsolutePath());
                    return;
                }

                Log.d(TAG, "Binary path: " + serverFile.getAbsolutePath());
                Log.d(TAG, "Binary size: " + serverFile.length() + " bytes");

                // Prepare paths
                File dbFile = new File(getFilesDir(), "savetune.db");
                File dlDir = getExternalFilesDir("Music");
                if (dlDir == null) dlDir = new File(getFilesDir(), "downloads");
                dlDir.mkdirs();

                File ffmpegFile = new File(nativeDir, "libffmpeg.so");
                String ffmpegPath = (ffmpegFile.exists() && ffmpegFile.canExecute())
                    ? ffmpegFile.getAbsolutePath() : "";

                // Build and start process
                ProcessBuilder pb = new ProcessBuilder(serverFile.getAbsolutePath());
                pb.directory(getFilesDir());
                pb.redirectErrorStream(false);

                // Environment variables — Go binary reads these
                pb.environment().put("PORT",          "7799");
                pb.environment().put("HOST",          "127.0.0.1");
                pb.environment().put("DB_PATH",       dbFile.getAbsolutePath());
                pb.environment().put("DOWNLOAD_DIR",  dlDir.getAbsolutePath());
                pb.environment().put("FFMPEG_PATH",   ffmpegPath);
                pb.environment().put("HOME",          getFilesDir().getAbsolutePath());
                pb.environment().put("TMPDIR",        getCacheDir().getAbsolutePath());

                Log.d(TAG, "Starting Go server on 127.0.0.1:7799");
                serverProcess = pb.start();
                running = true;

                // Stream stdout to logcat
                new Thread(() -> {
                    try (BufferedReader br = new BufferedReader(
                            new InputStreamReader(serverProcess.getInputStream()))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            Log.i(TAG, "STDOUT: " + line);
                        }
                    } catch (IOException e) {
                        Log.e(TAG, "stdout reader error", e);
                    }
                }, "go-stdout").start();

                // Stream stderr to logcat
                new Thread(() -> {
                    try (BufferedReader br = new BufferedReader(
                            new InputStreamReader(serverProcess.getErrorStream()))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            Log.e(TAG, "STDERR: " + line);
                        }
                    } catch (IOException e) {
                        Log.e(TAG, "stderr reader error", e);
                    }
                }, "go-stderr").start();

                // Monitor and restart on crash
                int exitCode = serverProcess.waitFor();
                running = false;
                Log.e(TAG, "Go server exited with code: " + exitCode);
                Log.d(TAG, "Restarting in 2 seconds...");
                Thread.sleep(2000);
                extractAndStart();

            } catch (Exception e) {
                Log.e(TAG, "extractAndStart failed", e);
                running = false;
            }
        }, "go-server-thread").start();
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "GoService onDestroy");
        running = false;
        if (serverProcess != null) {
            serverProcess.destroy();
            serverProcess = null;
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "SaveTune Server",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Keeps the SaveTune music server running");
            channel.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    @SuppressWarnings("deprecation")
    private Notification buildNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        return builder
            .setContentTitle("SaveTune")
            .setContentText("Music server running")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setOngoing(true)
            .build();
    }
}
