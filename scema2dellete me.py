def get_default_schema():
    """
    Return the empty starting data with the v2 structure.
    All comments are written in simple English (A1 Level) to explain every value.
    """
    return {
        # This is the version number of the file. 
        # Source: Developer logic. Goal: If we change the structure in the future, we make this 3 to reset the file.
        "_schema_version": 2, 
        
        # Section 0: Data Integrity (Health of the JSON file)
        "0_data_integrity": {
            # How many times the app fixed a broken JSON file automatically.
            # Source: analytics.py strict replica engine. Goal: Know if the user tries to hack the file.
            "schema_repairs_count": 0,
            
            # The exact time when the last fix happened (Unix Float).
            # Source: analytics.py. Goal: Know when the hacking or file corruption happened.
            "last_repair_timestamp": 0.0
        },

        # Section 1: App Lifecycle (How the user opens and uses the app)
        "1_app_lifecycle": {
            # The exact date and time the user opened the app for the very first time (String).
            # Source: App startup logic. Goal: Easy to read date for humans.
            "first_app_launch_date_str": "Unknown",
            
            # The exact time the user opened the app for the very first time (Unix Float).
            # Source: App startup logic. Goal: Easy to use for math and code calculations.
            "first_app_launch_timestamp": 0.0,
            
            # How many times the user opened the app in total.
            # Source: App startup logic. Goal: Know if the user likes the app and uses it a lot.
            "total_launches": 0,
            
            # Total minutes the app was open on the screen.
            # Source: App shutdown logic. Goal: Measure how long the user stays inside the app.
            "total_uptime_minutes": 0.0,
            
            # How many different days the user opened the app.
            # Source: App startup logic. Goal: Know if the user opens the app every day or rarely.
            "unique_days_active": 0,

            "last_active_timestamp": 0.0,
            
            "ui_interactions": {
                # How many times the user pressed keyboard shortcuts (like Ctrl+V).
                # Source: UI events. Goal: Know if the user prefers keyboard over mouse.
                "hardware_shortcuts_used": 0,
                
                # How many times the user right-clicked to open the menu.
                # Source: UI events. Goal: Know if the right-click menu is useful.
                "context_menu_used": 0
            },
            "support_interactions": {
                # How many times the user clicked the main contact button.
                # Source: UI buttons. Goal: Measure how often users need help.
                "main_contact_btn_clicks": 0,
                
                # How many times the user clicked the WhatsApp icon.
                # Source: UI buttons. Goal: Track WhatsApp support usage.
                "whatsapp_clicks": 0,
                
                # How many times the user clicked the LinkedIn icon.
                # Source: UI buttons. Goal: Track LinkedIn profile visits.
                "linkedin_clicks": 0,
                
                # How many times the user clicked the GitHub icon.
                # Source: UI buttons. Goal: Track open-source code interest.
                "github_clicks": 0,
                
                # How many times the user clicked the Email icon (only one count per popup).
                # Source: UI buttons. Goal: Track email support usage without fake spam counts.
                "email_clicks": 0
            }
        },

        # Section 2: Search Behavior (How the user adds links)
        "2_search_behavior": {
            # Total number of YouTube links the user pasted.
            # Source: Search bar. Goal: Measure general download activity.
            "total_links_searched": 0,
            
            # Number of links that are for one video only.
            # Source: Search bar. Goal: Know if users prefer single videos.
            "single_video_links": 0,
            
            # Number of links that are for full playlists.
            # Source: Search bar. Goal: Know if users prefer playlists.
            "playlist_links": 0,
            
            # Number of bad or wrong links the user entered.
            # Source: Link validation logic. Goal: Know if users make mistakes often.
            "invalid_links_entered": 0,
            
            # How many times the user clicked 'Fetch Sizes' to see video MB size.
            # Source: UI button. Goal: Know if users care about video sizes before downloading.
            "fetch_sizes_clicks": 0,
            
            # How many videos the app read from YouTube successfully.
            # Source: yt-dlp fetcher. Goal: Measure the success rate of reading data.
            "videos_fetched_successfully": 0
        },

        # Section 3: Download Stats (How the user downloads videos)
        "3_download_stats": {
            "single_videos": {
                # User clicked download for a single video.
                # Source: Download button. Goal: Track intention to download.
                "attempted": 0,
                # Download finished 100%.
                # Source: Download manager. Goal: Track true success.
                "completed": 0,
                # Download stopped because of an error (like no internet).
                # Source: Download manager. Goal: Track technical problems.
                "failed": 0,
                # User clicked the stop/cancel button.
                # Source: Cancel button. Goal: Track user behavior.
                "canceled": 0
            },
            "playlists": {
                # User clicked download for a playlist.
                # Source: Download button. Goal: Track intention to download playlists.
                "attempted": 0,
                # Full playlist finished 100%.
                # Source: Download manager. Goal: Track playlist success.
                "completed": 0,
                # Playlist stopped because of an error.
                # Source: Download manager. Goal: Track playlist problems.
                "failed": 0,
                # User canceled the playlist download.
                # Source: Cancel button. Goal: Track user behavior.
                "canceled": 0,
            },
            "volume": {
                # Total MegaBytes (MB) the user downloaded in their life.
                # Source: Download manager. Goal: Measure data usage.
                "total_downloaded_mb": 0.0,
                # Total time the user spent downloading (in seconds).
                # Source: Download manager. Goal: Measure time cost.
                "total_download_time_seconds": 0.0
            },
            # User choices for video quality.
            # Source: UI Dropdown menus. Goal: Know the most popular video quality.
            "quality_preferences": {
                "single_videos_exact_resolutions": {
                    "exact_144p": 0,
                    "exact_240p": 0,
                    "exact_360p": 0, 
                    "exact_480p": 0,
                    "exact_720p": 0,
                    "exact_1080p": 0, 
                    "exact_1440p": 0,
                    "exact_4k": 0, 
                    "exact_8k": 0, 
                    "exact_16k_plus": 0,
                    "audio_only": 0
                },
                "playlist_presets": {
                    "best_quality": 0,
                    "medium": 0, 
                    "low": 0,
                    "audio_only": 0
                }
            }
        },

        # Section 4: Network Profile (Internet speed data)
        "4_network_profile": {
            "download_speeds": {
                # The highest download speed the user ever reached (MegaBits per second).
                # Source: Download manager. Goal: Know how fast the user's internet is.
                "highest_mbps": 0.0,
                # The lowest download speed the user ever reached.
                # Source: Download manager. Goal: Know how slow the internet can get.
                "lowest_mbps": 0.0
            },
            "speed_test": {
                # Speed result from the manual network test.
                # Source: Network tester logic. Goal: Track manual speed checks.
                "last_result_mbps": 0.0,
                # Best result from manual tests.
                # Source: Network tester logic. Goal: Know maximum tested speed.
                "highest_mbps": 0.0,
                # Worst result from manual tests.
                # Source: Network tester logic. Goal: Know minimum tested speed.
                "lowest_mbps": 0.0,
                # Time of the last manual test.
                # Source: Network tester logic. Goal: Know when the last check happened.
                "last_tested_timestamp": 0.0
            }
        },

        # Section 5: Conversion Stats (FFmpeg operations)
        "5_conversion_stats": {
            # How many videos were successfully converted to MP4.
            # Source: FFmpeg logic. Goal: Track conversion success.
            "completed": 0,
            # How many conversions failed to finish.
            # Source: FFmpeg logic. Goal: Track conversion errors.
            "failed": 0,
            # How many conversions the user canceled.
            # Source: FFmpeg logic. Goal: Track user stops.
            "canceled": 0,
            # How many times the app skipped conversion because the video is already MP4.
            # Source: FFmpeg logic. Goal: Track smart saving of time.
            "skipped_already_mp4": 0,
            # How many times the user chose fast conversion speed.
            # Source: UI settings. Goal: Track user speed choices.
            "speed_mode_fast": 0,
            # How many times the user chose slow conversion speed.
            # Source: UI settings. Goal: Track user quality choices.
            "speed_mode_slow": 0,
            "volume": {
                # Total MegaBytes of converted videos.
                # Source: FFmpeg logic. Goal: Measure processing volume.
                "total_converted_mb": 0.0,
                # Total time spent converting videos.
                # Source: FFmpeg logic. Goal: Measure CPU time used.
                "total_conversion_time_seconds": 0.0
            }
        },

        # Section 6: Resilience and Errors (Network problems)
        "6_resilience_and_errors": {
            # How many times YouTube blocked the download.
            # Source: yt-dlp errors. Goal: Track YouTube ban rates.
            "youtube_blocks": 0,
            # How many times the app tried again automatically after internet drop.
            # Source: Network logic. Goal: Measure auto-recovery success.
            "network_retries": 0,
            # How many times the app warned the user about large files.
            # Source: UI popups. Goal: Track data warnings.
            "data_limit_warnings_shown": 0,
            # How many times the app failed to read a link.
            # Source: yt-dlp errors. Goal: Track read errors.
            "fetch_failures": 0,
        },

        # Section 7: System Hardware (Computer specs)
        "7_system_hardware": {
            # Windows, Mac, or Linux version.
            # Source: Python OS module. Goal: Know the target operating systems.
            "os_version": "Unknown",
            # Number of CPU cores.
            # Source: Python OS module. Goal: Know PC strength.
            "cpu_cores": 0,
            # The full name of the processor.
            # Source: Windows Registry / OS commands. Goal: Know hardware types.
            "cpu_name": "Unknown",
            # Total RAM size in GB.
            # Source: OS commands. Goal: Know memory capacity.
            "ram_gb": "Unknown",
            # The name of the graphic card.
            # Source: OS commands. Goal: Know GPU power.
            "gpu_name": "Unknown",
            # Time of the last hardware check.
            # Source: Background scanner. Goal: Only check hardware every 6 months.
            "last_scan_timestamp": 0.0
        }
    }