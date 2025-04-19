import instaloader
import time
import random
import os
import logging
import getpass
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("instascraper_log.txt"), logging.StreamHandler()]
)

# Initialize Instaloader instance
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=True,
    save_metadata=False,
    compress_json=False,
    max_connection_attempts=3,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    request_timeout=60
)

def get_session_filename(username):
    """Generate a session filename for the user."""
    return f"{username}.session"

def login(username, password, force_new_session=False):
    """Log in to Instagram and manage session."""
    session_file = get_session_filename(username)

    # Remove old session if forced
    if force_new_session and os.path.exists(session_file):
        os.remove(session_file)
        print("Forced new session: old session removed.")

    try:
        # Load existing session
        if not force_new_session and os.path.exists(session_file):
            L.load_session_from_file(username)
            print("Session loaded from file.")
            if L.test_login():
                print("✓ Session is valid.")
                return True
            else:
                print("⚠ Session is invalid. Logging in again...")

        # Perform login
        print("Logging in with username and password...")
        L.login(username, password)
        L.save_session_to_file(session_file)
        print("✓ Login successful! Session saved.")
        return True

    except instaloader.exceptions.BadCredentialsException:
        print("❌ Invalid username or password.")
    except instaloader.exceptions.ConnectionException as e:
        print(f"⚠ Connection error: {e}")
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("Two-factor authentication required!")
        try:
            two_factor_code = input("Enter the 2FA code from your app: ").strip()
            L.two_factor_login(two_factor_code)
            L.save_session_to_file(session_file)
            print("✓ 2FA login successful!")
            return True
        except Exception as e:
            print(f"❌ 2FA login failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")

    return False

def verify_session(username):
    """Verify if the session is valid."""
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return True
    except Exception as e:
        print(f"Session verification failed: {e}")
        return False

def get_shortcode(url):
    """Extract the shortcode from an Instagram URL."""
    url = url.rstrip('/')
    if '/p/' in url:
        return url.split('/p/')[1].split('/')[0]
    elif '/reel/' in url:
        return url.split('/reel/')[1].split('/')[0]
    print("❌ Invalid Instagram post URL format.")
    return None

def smart_sleep(idx=None):
    """Sleep with randomization to avoid detection."""
    base_delay = random.uniform(8, 12)
    if idx and idx % random.randint(4, 8) == 0:
        delay = random.uniform(25, 45)
        print(f"Taking a longer break ({delay:.1f}s) to avoid rate limits...")
    else:
        delay = base_delay
    time.sleep(delay)

def get_post_comments(post, max_comments=None):
    """Fetch usernames who commented on the post."""
    usernames = []
    try:
        comments_iterator = post.get_comments()
        for idx, comment in enumerate(comments_iterator, 1):
            usernames.append(comment.owner.username)
            if idx % 10 == 0:
                print(f"Processed {idx} comments so far...")
            smart_sleep(idx)
            if max_comments and idx >= max_comments:
                break
    except instaloader.exceptions.LoginRequiredException:
        print("⚠ Login required. Please log in again.")
    except instaloader.exceptions.ConnectionException as e:
        print(f"⚠ Connection error: {e}")
    except Exception as e:
        print(f"⚠ Error fetching comments: {e}")
    return usernames

def save_usernames_to_file(usernames, filename="usernames.txt"):
    """Save usernames to a file."""
    if not usernames:
        print("No usernames to save.")
        return
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for username in usernames:
                file.write(f"{username}\n")
        print(f"✓ Usernames saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving usernames: {e}")

def main():
    print("=" * 50)
    print("Instagram Username Scraper")
    print("=" * 50)

    # Get credentials
    username = "janet_thedreamer"
    password = "Ttlshiwwya2002#"

    # Log in
    if not login(username, password):
        print("❌ Login failed. Exiting.")
        return

    while True:
        url = input("\nEnter Instagram post URL (or 'exit' to quit): ")
        if url.lower() in ['exit', 'quit']:
            break

        shortcode = get_shortcode(url)
        if not shortcode:
            continue

        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            print(f"Fetching comments for post: {shortcode}")
            max_comments = input("Enter max comments to fetch (default: 50): ")
            max_comments = int(max_comments) if max_comments.isdigit() else 50
            usernames = get_post_comments(post, max_comments)
            if usernames:
                save_usernames_to_file(usernames)
            else:
                print("No usernames retrieved.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
