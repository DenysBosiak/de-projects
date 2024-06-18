import os
import sys
import praw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.constants import CLIENT_ID, SECRET


reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=SECRET,
    user_agent='Airscholar Agent'
)


print(reddit.read_only)