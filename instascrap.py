import instaloader
import time
import random
import os
import logging
from datetime import datetime
import sys

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

        # Perform login with a delay to avoid rate limiting
        print("Logging in with username and password...")
        time.sleep(random.uniform(2, 4))  # Small delay before login
        L.login(username, password)
        L.save_session_to_file(session_file)
        print("✓ Login successful! Session saved.")
        return True

    except instaloader.exceptions.BadCredentialsException:
        print("❌ Invalid username or password.")
    except instaloader.exceptions.ConnectionException as e:
        print(f"⚠ Connection error: {e}")
        if "429" in str(e):
            wait_time = random.uniform(60, 120)
            print(f"Rate limited! Waiting {wait_time:.0f} seconds...")
            time.sleep(wait_time)
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
    # Base delay with some randomization
    base_delay = random.uniform(10, 15)
    
    # Occasional longer pauses to mimic human behavior
    if idx and idx % random.randint(5, 9) == 0:
        delay = random.uniform(30, 60)
        print(f"Taking a longer break ({delay:.1f}s) to avoid rate limits...")
    else:
        # Add small variability to appear more human-like
        delay = base_delay * random.uniform(0.8, 1.2)
    
    # Add tiny jitter for more randomness
    jitter = random.uniform(0, 0.5)
    total_delay = delay + jitter
    
    time.sleep(total_delay)
    return total_delay

def get_post_comments(post, max_comments=None, username=None, password=None, retry_count=0):
    """Fetch usernames who commented on the post with session validation."""
    # Guard against too many retries to prevent infinite loops
    if retry_count >= 3:
        print("⚠ Too many retry attempts. Please try again later.")
        return []
    
    # Check if session is valid before attempting to fetch comments
    if not L.test_login():
        print("⚠ Session invalid before fetching comments. Refreshing...")
        if username and password:
            if login(username, password, force_new_session=True):
                print("Session refreshed successfully.")
                # Small delay after login before making API request
                time.sleep(random.uniform(3, 7))
            else:
                print("❌ Failed to refresh session. Exiting.")
                return []
    
    usernames = []
    try:
        print("Preparing to fetch comments...")
        # Small delay before API request
        time.sleep(random.uniform(2, 5))
        
        comments_iterator = post.get_comments()
        for idx, comment in enumerate(comments_iterator, 1):
            try:
                usernames.append(comment.owner.username)
                if idx % 10 == 0:
                    print(f"Processed {idx} comments so far...")
                
                # Apply smart rate limiting
                smart_sleep(idx)
                
                if max_comments and idx >= max_comments:
                    print(f"✓ Reached requested limit of {max_comments} comments")
                    break
            except Exception as ce:
                print(f"Error processing comment {idx}: {ce}")
                # Continue with next comment instead of failing completely
                continue
                
    except instaloader.exceptions.LoginRequiredException:
        print("⚠ Login required during comment fetch. Refreshing session...")
        if username and password:
            if login(username, password, force_new_session=True):
                print("Session refreshed. Retrying comment fetch...")
                # Wait before retrying to avoid rate limits
                wait_time = random.uniform(15, 30) * (retry_count + 1)
                print(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
                # Recursive call with increased retry count
                return get_post_comments(post, max_comments, username, password, retry_count + 1)
            else:
                print("Failed to refresh session.")
    except instaloader.exceptions.ConnectionException as e:
        print(f"⚠ Connection error: {e}")
        if "429" in str(e):
            print("Instagram rate limit detected. Taking a longer break...")
            wait_time = random.uniform(60, 120) * (retry_count + 1)
            print(f"Waiting {wait_time:.1f}s before retry...")
            time.sleep(wait_time)
            return get_post_comments(post, max_comments, username, password, retry_count + 1)
    except Exception as e:
        print(f"⚠ Error fetching comments: {e}")
    
    # Report results
    if usernames:
        print(f"Successfully retrieved {len(usernames)} usernames from comments")
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

    # Hardcoded credentials
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
            # Validate session before fetching post
            if not L.test_login():
                print("Session invalid. Refreshing before fetching post...")
                if not login(username, password, force_new_session=True):
                    print("❌ Failed to refresh session. Please try again.")
                    continue
            
            # Fetch post data
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            print(f"Fetching comments for post: {shortcode}")
            print(f"Post by @{post.owner_username} - Has {post.comments} comments")
            
            # Get comment count limit
            max_comments = input("Enter max comments to fetch (default: 50): ")
            max_comments = int(max_comments) if max_comments.isdigit() else 50
            
            # Get comments with automatic session validation
            usernames = get_post_comments(post, max_comments, username, password)
            
            if usernames:
                save_usernames_to_file(usernames)
            else:
                print("No usernames retrieved.")
        except instaloader.exceptions.InstaloaderException as e:
            print(f"❌ Instagram error: {e}")
            # Handle specific Instagram errors
            if "login_required" in str(e).lower() or "not logged in" in str(e).lower():
                print("Attempting to refresh session...")
                login(username, password, force_new_session=True)
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        logging.exception("Critical error occurred")
