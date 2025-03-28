import sys
import os

from tools.google.core.google_auth import GoogleAuth


class YouTubeClient:
    """Klasse zum Abrufen von YouTube-Playlisten und Lieblingsvideos"""

    def __init__(self):
        self.service = GoogleAuth.get_service("youtube", "v3")

    def get_liked_videos(self, max_results=10):
        return self._get_videos_from_playlist("LL", max_results)

    def _get_videos_from_playlist(self, playlist_id, max_results=5):
        request = self.service.playlistItems().list(
            part="snippet", playlistId=playlist_id, maxResults=max_results
        )
        response = request.execute()

        videos = []
        video_ids = [
            video["snippet"]["resourceId"]["videoId"]
            for video in response.get("items", [])
        ]

        if not video_ids:
            return videos

        video_request = self.service.videos().list(
            part="snippet", id=",".join(video_ids)
        )
        video_response = video_request.execute()

        for video in video_response.get("items", []):
            videos.append(
                {
                    "title": video["snippet"]["title"],
                    "channel": video["snippet"]["channelTitle"],
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                }
            )
        return videos


# Testlauf
if __name__ == "__main__":
    yt_client = YouTubeClient()
    liked_videos = yt_client.get_liked_videos()
    print(liked_videos)
