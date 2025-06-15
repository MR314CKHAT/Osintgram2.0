import datetime
import json
import sys
import urllib
import os
from dotenv import load_dotenv
load_dotenv()
import codecs
from pathlib import Path
import requests
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from geopy.geocoders import Nominatim

from instagrapi import Client as AppClient
from instagrapi.exceptions import ClientThrottledError
from prettytable import PrettyTable

from src import printcolors as pc
from src import config

class Osintgram:
    api = None
    api2 = None
    geolocator = Nominatim(user_agent="http")
    user_id = None
    target_id = None
    is_private = True
    following = False
    target = ""
    writeFile = False
    jsonDump = False
    cli_mode = False
    output_dir = "output"

    def __init__(self, target, is_file, is_json, is_cli, output_dir, clear_cookies):
        self.output_dir = output_dir or self.output_dir        
        u = config.getUsername()
        p = config.getPassword()
        self.clear_cookies(clear_cookies)
        self.cli_mode = is_cli
        if not is_cli:
            print("\nAttempt to login...")
        self.login(u, p)
        self.setTarget(target)
        self.writeFile = is_file
        self.jsonDump = is_json

    def clear_cookies(self, clear_cookies):
        if clear_cookies:
            self.clear_cache()

    def setTarget(self, target):
        self.target = target
        user = self.get_user(target)
        self.target_id = user['id']
        self.is_private = user['is_private']
        self.following = self.check_following()
        self.__printTargetBanner__()
        self.output_dir = f"{self.output_dir}/{self.target}"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def login(self, u, p):
        session_id = os.getenv("IG_SESSIONID")
        if session_id:
            print("Login via session ID...")
            self.api = AppClient()
            try:
                self.api.login_by_sessionid(session_id)
                print("Login successful via session.")
            except Exception as e:
                print("Login failed:", str(e))
                exit(1)
        else:
            print("No session ID found! Please update IG_SESSIONID in .env.")
            exit(1)
                
    def __get_feed__(self):
        try:
            # Fetch all media posts of the target
            return self.api.user_medias(self.target_id, amount=1000)
        except Exception as e:
            print(f"Error retrieving feed: {e}")
            return []

    def __get_comments__(self, media_id, amount=100):
        try:
            comments = self.api.media_comments(media_id, amount=amount)
            return comments
        except Exception as e:
            print(f"Error retrieving comments: {e}")
            return []

    def __printTargetBanner__(self):
        try:
            current_username = self.api.user_info_by_id(self.api.user_id).username
        except Exception:
            current_username = "Unknown"
        pc.printout("\nLogged as ", pc.GREEN)
        pc.printout(self.api.username, pc.CYAN)
        pc.printout(". Target: ", pc.GREEN)
        pc.printout(str(self.target), pc.CYAN)
        pc.printout(f" [{self.target_id}]")
        if self.is_private:
            pc.printout(" [PRIVATE PROFILE]", pc.BLUE)
        if self.following:
            pc.printout(" [FOLLOWING]", pc.GREEN)
        else:
            pc.printout(" [NOT FOLLOWING]", pc.RED)
        print('\n')

    def change_target(self):
        pc.printout("Insert new target username: ", pc.YELLOW)
        line = input()
        self.setTarget(line)
        return

    def get_addrs(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for geodata...\n")
        data = self.__get_feed__()
        locations = {}
        for post in data:
            if post.location and post.location.lat and post.location.lng:
                coords = f"{post.location.lat}, {post.location.lng}"
                timestamp = post.taken_at.timestamp() if post.taken_at else None
                locations[coords] = timestamp
        address = {}
        for coords, ts in locations.items():
            try:
                details = self.geolocator.reverse(coords)
                time_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else "Unknown"
                address[details.address] = time_str
            except Exception as e:
                print(f" Error during reverse geocoding: {e}")
        sort_addresses = sorted(address.items(), key=lambda p: p[1], reverse=True)
        if sort_addresses:
            t = PrettyTable()
            t.field_names = ['Post', 'Address', 'Time']
            t.align["Post"] = "l"
            t.align["Address"] = "l"
            t.align["Time"] = "l"
            pc.printout(f"\n {len(sort_addresses)} addresses found!\n", pc.GREEN)
            json_data = {}
            addrs_list = []
            for i, (addr, time) in enumerate(sort_addresses, 1):
                t.add_row([str(i), addr, time])
                if self.jsonDump:
                    addrs_list.append({'address': addr, 'time': time})
            if self.writeFile:
                with open(f"{self.output_dir}/{self.target}_addrs.txt", "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                json_data['address'] = addrs_list
                with open(f"{self.output_dir}/{self.target}_addrs.json", "w") as f:
                    json.dump(json_data, f)
            print(t)
        else:
            pc.printout(" No geotags found.\n", pc.RED)

    def get_captions(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target captions...\n")
        captions = []
        data = self.__get_feed__()
        counter = 0
        for item in data:
            if item.caption_text:
                captions.append(item.caption_text)
                counter += 1
                sys.stdout.write(f"\rFound: {counter}")
                sys.stdout.flush()
        print()
        json_data = {}
        if counter > 0:
            pc.printout(f"{counter} captions found!\n", pc.GREEN)
            if self.writeFile:
                file_name = f"{self.output_dir}/{self.target}_captions.txt"
                with open(file_name, "w") as f:
                    for caption in captions:
                        f.write(caption + "\n\n")
            if self.jsonDump:
                json_data['captions'] = captions
                json_file_name = f"{self.output_dir}/{self.target}_captions.json"
                with open(json_file_name, "w") as f:
                    json.dump(json_data, f, indent=4)
            for s in captions:
                print(s + "\n")
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_total_comments(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target total comments...\n")
        comments_counter = 0
        posts = 0
        data = self.__get_feed__()
        for post in data:
            comments_counter += post.comment_count or 0
            posts += 1
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_comments.txt"
            with open(file_name, "w") as file:
                file.write(f"{comments_counter} comments in {posts} posts\n")
        if self.jsonDump:
            json_data = {
                'comment_counter': comments_counter,
                'posts': posts
            }
            json_file_name = f"{self.output_dir}/{self.target}_comments.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f)
        pc.printout(str(comments_counter), pc.MAGENTA)
        pc.printout(" comments in " + str(posts) + " posts\n")

    def get_comment_data(self):
        if self.check_private_profile():
            return
        pc.printout("Retrieving all comments, this may take a moment...\n")
        data = self.__get_feed__()
        _comments = []
        t = PrettyTable(['POST ID', 'ID', 'Username', 'Comment'])
        t.align["POST ID"] = "l"
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Comment"] = "l"
        for post in data:
            post_id = post.pk
            try:
                comments = self.api.media_comments(post_id)
                for comment in comments:
                    t.add_row([post_id, comment.user.pk, comment.user.username, comment.text])
                    _comments.append({
                        "post_id": post_id,
                        "user_id": comment.user.pk, 
                        "username": comment.user.username,
                        "comment": comment.text
                    })
            except Exception as e:
                pc.printout(f"Error retrieving comments for post {post_id}: {e}\n", pc.RED)
        print(t)
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_comment_data.txt"
            with open(file_name, 'w') as f:
                f.write(str(t))
        if self.jsonDump:
            file_name_json = f"{self.output_dir}/{self.target}_comment_data.json"
            with open(file_name_json, 'w') as f:
                json.dump({"comments": _comments}, f, indent=4)

    def get_followers(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target followers...\n")
        try:
            followers_dict = self.api.user_followers(self.target_id)
        except Exception as e:
            pc.printout(f"Error retrieving followers: {e}\n", pc.RED)
            return
        followers = []
        for user_id, user in followers_dict.items():
            followers.append({
                'id': user.pk,
                'username': user.username,
                'full_name': user.full_name
            })
        t = PrettyTable(['ID', 'Username', 'Full Name'])
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Full Name"] = "l"
        for u in followers:
            t.add_row([str(u['id']), u['username'], u['full_name']])
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_followers.txt"
            with open(file_name, "w") as f:
                f.write(str(t))
        if self.jsonDump:
            json_data = {'followers': followers}
            json_file_name = f"{self.output_dir}/{self.target}_followers.json"
            with open(json_file_name, "w") as f:
                json.dump(json_data, f, indent=4)
        print(t)

    def get_followings(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for users followed by target...\n")
        try:
            following_dict = self.api.user_following(self.target_id)
        except Exception as e:
            pc.printout(f"Error retrieving following list: {e}\n", pc.RED)
            return
        followings = []
        for user_id, user in following_dict.items():
            followings.append({
                'id': user.pk,
                'username': user.username,
                'full_name': user.full_name
            })
        t = PrettyTable(['ID', 'Username', 'Full Name'])
        t.align["ID"] = "l"
        t.align["Username"] = "l"
        t.align["Full Name"] = "l"
        for u in followings:
            t.add_row([str(u['id']), u['username'], u['full_name']])
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_followings.txt"
            with open(file_name, 'w') as f:
                f.write(str(t))
        if self.jsonDump:
            json_data = {'followings': followings}
            json_file_name = f"{self.output_dir}/{self.target}_followings.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f, indent=4)
        print(t)

    def get_hashtags(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target hashtags...\n")
        hashtags = []
        data = self.__get_feed__()
        for post in data:
            caption = post.caption_text
            if caption:
                for word in caption.split():
                    if word.startswith('#'):
                        hashtags.append(word)
        if not hashtags:
            pc.printout("Sorry! No hashtags found :-(\n", pc.RED)
            return
        hashtag_counter = {}
        for tag in hashtags:
            hashtag_counter[tag] = hashtag_counter.get(tag, 0) + 1
        sorted_tags = sorted(hashtag_counter.items(), key=lambda value: value[1], reverse=True)
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_hashtags.txt"
            with open(file_name, "w") as f:
                for tag, count in sorted_tags:
                    f.write(f"{count}. {tag}\n")
        if self.jsonDump:
            json_data = {'hashtags': [tag for tag, _ in sorted_tags]}
            json_file_name = f"{self.output_dir}/{self.target}_hashtags.json"
            with open(json_file_name, "w") as f:
                json.dump(json_data, f, indent=4)
        for tag, count in sorted_tags:
            print(f"{count}. {tag}")

    def get_user_info(self):
       try:
           user = self.api.user_info_by_username(self.target)
           print(f"[+] Username     : {user.username}")
           print(f"[+] Full Name    : {user.full_name}")
           print(f"[+] Private      : {'Yes' if user.is_private else 'No'}")
           print(f"[+] Verified     : {'Yes' if user.is_verified else 'No'}")
           print(f"[+] Biography    : {user.biography}")
           print(f"[+] Followers    : {user.follower_count}")
           print(f"[+] Following    : {user.following_count}")
           print(f"[+] Posts        : {user.media_count}")
           print(f"[+] Profile picture URL: {user.profile_pic_url_hd}")
       except Exception as e:
           print(f"Error retrieving user information: {e}")
       if self.writeFile:
           file_name = f"{self.output_dir}/{self.target}_info.txt"
           with open(file_name, "w") as f:
               f.write(f"Username       : {user.username}\n")
               f.write(f"Full Name      : {user.full_name}\n")
               f.write(f"Private        : {'Yes' if user.is_private else 'No'}\n")
               f.write(f"Verified       : {'Yes' if user.is_verified else 'No'}\n")
               f.write(f"Biography      : {user.biography}\n")
               f.write(f"Followers      : {user.follower_count}\n")
               f.write(f"Following      : {user.following_count}\n")
               f.write(f"Posts          : {user.media_count}\n")
               f.write(f"Profile Pic URL: {user.profile_pic_url_hd}\n")
       if self.jsonDump:
           data = {
               "username": user.username,
               "full_name": user.full_name,
               "is_private": user.is_private,
               "is_verified": user.is_verified,
               "biography": user.biography,
               "follower_count": user.follower_count,
               "following_count": user.following_count,
               "media_count": user.media_count,
               "profile_pic_url_hd": str(user.profile_pic_url_hd)
           }
           json_file_name = f"{self.output_dir}/{self.target}_info.json"
           with open(json_file_name, "w") as f:
               json.dump(data, f, indent=4)

    def get_total_likes(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target total likes...\n")
        like_counter = 0
        posts = 0
        data = self.__get_feed__()
        for post in data:
            like_counter += getattr(post, 'like_count', 0)
            posts += 1
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_likes.txt"
            with open(file_name, "w") as file:
                file.write(f"{like_counter} likes in {posts} posts\n")
        if self.jsonDump:
            json_data = {
                'like_counter': like_counter,
                'posts': posts
            }
            json_file_name = f"{self.output_dir}/{self.target}_likes.json"
            with open(json_file_name, 'w') as f:
                json.dump(json_data, f, indent=4)
        pc.printout(str(like_counter), pc.MAGENTA)
        pc.printout(" likes in " + str(posts) + " posts\n")

    def get_media_type(self):
        if self.check_private_profile():
            return
        pc.printout("Analyzing target's posts types...\n")
        photo_counter = 0
        video_counter = 0
        data = self.__get_feed__()
        for post in data:
            media_type = post.media_type
            if media_type == 1:
                photo_counter += 1
            elif media_type == 2:
                video_counter += 1
        if (photo_counter + video_counter) > 0:
            if self.writeFile:
                file_name = f"{self.output_dir}/{self.target}_mediatype.txt"
                with open(file_name, "w") as file:
                    file.write(f"{photo_counter} photos and {video_counter} videos posted by target\n")
            pc.printout(f"\nWoohoo! We found {photo_counter} photos and {video_counter} videos posted by target\n", pc.GREEN)
            if self.jsonDump:
                json_data = {
                    'photos': photo_counter,
                    'videos': video_counter
                }
                json_file_name = f"{self.output_dir}/{self.target}_mediatype.json"
                with open(json_file_name, "w") as f:
                    json.dump(json_data, f, indent=4)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_people_who_commented(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for users who commented...\n")
        data = self.__get_feed__()
        users = {}
        for post in data:
            comments = self.__get_comments__(post.id)
            for comment in comments:
                user_id = comment.user.pk
                if user_id not in users:
                    users[user_id] = {
                        'id': user_id,
                        'username': comment.user.username,
                        'full_name': comment.user.full_name,
                        'counter': 1
                    }
                else:
                    users[user_id]['counter'] += 1
        if users:
            sorted_users = sorted(users.values(), key=lambda x: x['counter'], reverse=True)
            t = PrettyTable(['Comments', 'ID', 'Username', 'Full Name'])
            t.align = {'Comments': 'l', 'ID': 'l', 'Username': 'l','Full Name': 'l'}
            for u in sorted_users:
                t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])
            print(t)
            if self.writeFile:
                file_name = f"{self.output_dir}/{self.target}_users_who_commented.txt"
                with open(file_name, "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                json_file_name = f"{self.output_dir}/{self.target}_users_who_commented.json"
                with open(json_file_name, "w") as f:
                    json.dump({'users_who_commented': sorted_users}, f, indent=4)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_people_who_tagged(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for users who tagged target...\n")
        try:
            posts = self.api.usertag_medias(self.target_id, amount=1000)
        except Exception as e:
            pc.printout(f"Error retrieving tagged posts: {e}\n", pc.RED)
            return
        if not posts:
            pc.printout("Sorry! No results found :-(\n", pc.RED)
            return
        pc.printout(f"\nWoohoo! We found {len(posts)} photos\n", pc.GREEN)
        users = {}
        for post in posts:
            user = post.user
            if not user:
                continue
            user_id = user.pk
            if user_id not in users:
                users[user_id] = {
                    'id': user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'counter': 1
                }
            else:
                users[user_id]['counter'] += 1
        sorted_users = sorted(users.values(), key=lambda x: x['counter'], reverse=True)
        t = PrettyTable(['Photos', 'ID', 'Username', 'Full Name'])
        t.align = {'Photos': 'l', 'ID': 'l', 'Username': 'l', 'Full Name': 'l'}
        for u in sorted_users:
            t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])
        print(t)
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_users_who_tagged.txt"
            with open(file_name, "w") as f:
                f.write(str(t))
        if self.jsonDump:
            json_file_name = f"{self.output_dir}/{self.target}_users_who_tagged.json"
            with open(json_file_name, "w") as f:
                json.dump({'users_who_tagged': sorted_users}, f, indent=4)

    def get_photo_description(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for photo descriptions...\n")
        try:
            posts = self.api.user_medias(self.target_id, amount=50)
        except Exception as e:
            pc.printout(f"Error retrieving posts: {e}", pc.RED)
            return
        descriptions = []
        t = PrettyTable(['Nr.', 'Description'])
        t.align["Nr."] = "l"
        t.align["Description"] = "l"
        json_data = {}
        descriptions_list = []
        for count, post in enumerate(posts, 1):
            descr = post.accessibility_caption
            t.add_row([str(count), descr])
            if self.jsonDump:
                descriptions_list.append({'description': descr})
            descriptions.append(descr)
        if not descriptions:
            pc.printout("Sorry! No results found :-(\n", pc.RED)
            return
        if self.writeFile:
            file_name = f"{self.output_dir}/{self.target}_photodes.txt"
            with open(file_name, "w") as f:
                f.write(str(t))
        if self.jsonDump:
            json_data['descriptions'] = descriptions_list
            json_file_name = f"{self.output_dir}/{self.target}_descriptions.json"
            with open(json_file_name, "w") as f:
                json.dump(json_data, f, indent=4)
        print(t)

    def get_user_photo(self):
        if self.check_private_profile():
            return
        limit = -1
        if self.cli_mode:
            user_input = ""
        else:
            pc.printout("How many photos you want to download (default all): ", pc.YELLOW)
            user_input = input()
        try:
            if user_input == "":
                pc.printout("Downloading all photos available...\n", pc.GREEN)
            else:
                limit = int(user_input)
                pc.printout(f"Downloading {limit} photos...\n", pc.GREEN)
        except ValueError:
            pc.printout("Wrong value entered\n", pc.RED)
            return
        try:
            media_list = self.api.user_medias(self.target_id, amount=limit if limit > 0 else 0)
        except Exception as e:
            pc.printout(f"Error fetching media: {e}\n", pc.RED)
            return
        counter = 0
        for media in media_list:
            if media.media_type == 1:
                photo_urls = [media.thumbnail_url]
            elif media.media_type == 8:
                photo_urls = [r.thumbnail_url for r in media.resources if r.media_type == 1]
            else:
                continue
            for url in photo_urls:
                try:
                    filename = f"{self.output_dir}/{self.target}_{media.pk}_{counter}.jpg"
                    urllib.request.urlretrieve(url, filename)
                    counter += 1
                    sys.stdout.write(f"\rDownloaded {counter}")
                    sys.stdout.flush()
                    if limit != -1 and counter >= limit:
                        break
                except Exception as e:
                    pc.printout(f"\nFailed to download image: {e}\n", pc.RED)
                    continue
            if limit != -1 and counter >= limit:
                break
        sys.stdout.write(" photos\n")
        sys.stdout.flush()
        pc.printout(f"\nWoohoo! We downloaded {counter} photos (saved in {self.output_dir} folder)\n", pc.GREEN)

    def get_user_propic(self):
        try:
            user_info = self.api.user_info_by_username(self.target)
            pic_url = user_info.profile_pic_url_hd
            print(f"[+] Profile picture URL: {pic_url}")
            return pic_url
        except Exception as e:
            print(f"Error retrieving profile picture: {e}")
            return None

    def get_user_stories(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for target stories...\n")
        try:
            stories = self.api.user_stories(self.target_id)
        except Exception as e:
            pc.printout(f"Error retrieving stories: {e}\n", pc.RED)
            return
        if not stories:
            pc.printout("Sorry! No stories found :-(\n", pc.RED)
            return
        counter = 0
        for story in stories:
            media_type = story.media_type
            story_id = story.pk
            try:
                if media_type == 1 and story.image_versions2:
                    url = story.image_versions2.candidates[0].url
                    file_ext = ".jpg"
                elif media_type == 2 and story.video_versions:
                    url = story.video_versions[0].url
                    file_ext = ".mp4"
                else:
                    continue
                filename = f"{self.output_dir}/{self.target}_{story_id}{file_ext}"
                urllib.request.urlretrieve(url, filename)
                counter += 1
            except Exception as e:
                pc.printout(f"Error downloading: {e}\n", pc.RED)
        if counter > 0:
            pc.printout(f"{counter} story file(s) saved in {self.output_dir} folder\n", pc.GREEN)
        else:
            pc.printout("Sorry! No downloadable stories found :-(\n", pc.RED)

    def get_user(self, username):
        try:
            content = self.api.user_info_by_username(username)
            return {
                'id': content.pk,
                'is_private': content.is_private,
                'username': content.username
            }
        except Exception as e:
            print(f"Error retrieving user information: {e}")
            return None

    def set_write_file(self, flag: bool):
        status = "enabled" if flag else "disabled"
        color = pc.GREEN if flag else pc.RED
        pc.printout("Write to file: ")
        pc.printout(status, color)
        pc.printout("\n")
        self.writeFile = flag

    def set_json_dump(self, flag: bool):
        status = "enabled" if flag else "disabled"
        color = pc.GREEN if flag else pc.RED
        pc.printout("Write to JSON: ")
        pc.printout(status, color)
        pc.printout("\n")
        self.jsonDump = flag

    def to_json(self, python_object):
        if isinstance(python_object, bytes):
            return {'__class__': 'bytes',
                    '__value__': codecs.encode(python_object, 'base64').decode('utf-8')}
        raise TypeError(f"Object of type {type(python_object).__name__} is not JSON serializable")

    def from_json(self, json_object):
        if '__class__' in json_object and json_object['__class__'] == 'bytes':
            return codecs.decode(json_object['__value__'].encode(), 'base64')
        return json_object

    def onlogin_callback(self, api, new_settings_file):
        cache_settings = api.settings
        with open(new_settings_file, 'w') as outfile:
            json.dump(cache_settings, outfile, default=self.to_json)

    def check_following(self):
        try:
            status = self.api.user_following_status(self.target_id)
            return status.following
        except Exception as e:
            print(f"Error checking follow relationship: {e}")
            return False


    def check_private_profile(self):
        if self.is_private and not self.following:
            pc.printout("Impossible to execute command: user has private profile\n", pc.RED)
            try:
                send = input("Do you want to send a follow request? [Y/N]: ").strip().lower()
                if send == "y":
                    self.api.user_follow(self.target_id)
                    print("Follow request sent to target. Try this command again after they accept.")
            except Exception as e:
                print(f"Error sending follow request: {e}")
            return True
        return False

    def clear_cache(self):
        try:
            with open("config/settings.json", 'w') as f:
                f.write("{}")
            pc.printout("Cache cleared.\n", pc.GREEN)
        except FileNotFoundError:
            pc.printout("settings.json not found.\n", pc.RED)
            
    def get_fwersemail(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for emails of target followers... this can take a few minutes\n")
        try:
            followers_dict = self.api.user_followers(self.target_id, amount=0)
        except ClientThrottledError:
            pc.printout("\nInstagram blocked the requests. Please wait before trying again.\n", pc.RED)
            return
        except Exception as e:
            pc.printout(f"\nError occurred: {e}\n", pc.RED)
            return

        followers = list(followers_dict.values())
        print(f"\nTotal followers fetched: {len(followers)}")

        pc.printout("Do you want to get all emails? (y/n): ", pc.YELLOW)
        choice = input().strip().lower()
        if choice in ["y", "yes"]:
            limit = len(followers)
        elif choice in ["n", "no"]:
            try:
                pc.printout("How many emails do you want to get? ", pc.YELLOW)
                limit = int(input().strip())
            except ValueError:
                pc.printout("Invalid number entered.\n", pc.RED)
                return
        elif choice == "":
            return
        else:
            pc.printout("Please answer with y or n.\n", pc.RED)
            return

        results = []
        for user_short in followers:
            if len(results) >= limit:
                break
            sys.stdout.write(f"\rChecked {len(results)} followers")
            sys.stdout.flush()
            try:
                user_info = self.api.user_info(user_short.pk)
            except Exception:
                continue
            email = getattr(user_info, "public_email", None)
            if email:
                results.append({
                    'id': user_info.pk,
                    'username': user_info.username,
                    'full_name': user_info.full_name or "",
                    'email': email
                })
        print("\r", end="")

        if results:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Email'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Email"] = "l"
            for entry in results:
                t.add_row([str(entry['id']), entry['username'], entry['full_name'], entry['email']])
            if self.writeFile:
                with open(f"{self.output_dir}/{self.target}_fwersemail.txt", "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                with open(f"{self.output_dir}/{self.target}_fwersemail.json", "w") as f:
                    json.dump({'followers_email': results}, f, indent=4)
            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)


    def get_fwingsemail(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for emails of users followed by target... this can take a few minutes\n")
        try:
            followings_dict = self.api.user_following(self.target_id, amount=0)
        except ClientThrottledError:
            pc.printout("\nInstagram blocked the requests. Please wait before trying again.\n", pc.RED)
            return
        except Exception as e:
            pc.printout(f"\nError occurred: {e}\n", pc.RED)
            return

        followings = list(followings_dict.values())

        pc.printout("Do you want to get all emails? (y/n): ", pc.YELLOW)
        choice = input().strip().lower()
        if choice in ["y", "yes"]:
            limit = len(followings)
        elif choice in ["n", "no"]:
            try:
                pc.printout("How many emails do you want to get? ", pc.YELLOW)
                limit = int(input().strip())
            except ValueError:
                pc.printout("Error: Invalid number entered\n", pc.RED)
                return
        elif choice == "":
            return
        else:
            pc.printout("Error: Please enter y or n\n", pc.RED)
            return

        results = []
        for user_short in followings:
            if len(results) >= limit:
                break
            sys.stdout.write(f"\rChecked {len(results)} followings")
            sys.stdout.flush()
            try:
                user_info = self.api.user_info(user_short.pk)
            except Exception:
                continue
            email = getattr(user_info, "public_email", None)
            if email:
                results.append({
                    'id': user_info.pk,
                    'username': user_info.username,
                    'full_name': user_info.full_name or "",
                    'email': email
                })
        print("\r", end="")

        if results:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Email'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Email"] = "l"
            for entry in results:
                t.add_row([str(entry['id']), entry['username'], entry['full_name'], entry['email']])
            if self.writeFile:
                with open(f"{self.output_dir}/{self.target}_fwingsemail.txt", "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                with open(f"{self.output_dir}/{self.target}_fwingsemail.json", "w") as f:
                    json.dump({'followings_email': results}, f, indent=4)
            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)


    def get_fwingsnumber(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for phone numbers of users followed by target... this may take a few minutes\n")
        try:
            followings_dict = self.api.user_following(self.target_id, amount=0)
        except ClientThrottledError:
            pc.printout("\nError: Instagram blocked the requests. Please wait a few minutes before trying again.\n", pc.RED)
            return
        except Exception as e:
            pc.printout(f"\nError occurred: {e}\n", pc.RED)
            return

        followings = list(followings_dict.values())

        pc.printout("Do you want to retrieve all phone numbers? (y/n): ", pc.YELLOW)
        choice = input().strip().lower()
        if choice in ["y", "yes"]:
            limit = len(followings)
        elif choice in ["n", "no"]:
            try:
                pc.printout("How many phone numbers do you want to retrieve? ", pc.YELLOW)
                limit = int(input().strip())
            except ValueError:
                pc.printout("Error: Invalid number entered\n", pc.RED)
                return
        elif choice == "":
            return
        else:
            pc.printout("Error: Please enter y or n\n", pc.RED)
            return

        results = []
        for user_short in followings:
            if len(results) >= limit:
                break
            sys.stdout.write(f"\rChecked {len(results)} followings")
            sys.stdout.flush()
            try:
                user_info = self.api.user_info(user_short.pk)
            except Exception:
                continue
            phone = getattr(user_info, "contact_phone_number", None)
            if phone:
                results.append({
                    'id': user_info.pk,
                    'username': user_info.username,
                    'full_name': user_info.full_name or "",
                    'contact_phone_number': phone
               })
        print("\r", end="")

        if results:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Phone number'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Phone number"] = "l"
            for entry in results:
                t.add_row([str(entry['id']), entry['username'], entry['full_name'], entry['contact_phone_number']])
            if self.writeFile:
                with open(f"{self.output_dir}/{self.target}_fwingsnumber.txt", "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                with open(f"{self.output_dir}/{self.target}_fwingsnumber.json", "w") as f:
                    json.dump({'followings_phone_numbers': results}, f, indent=4)
            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)


    def get_fwersnumber(self):
        if self.check_private_profile():
            return
        pc.printout("Searching for phone numbers of followers... this may take a few minutes\n")
        try:
            followers_dict = self.api.user_followers(self.target_id, amount=0)
        except ClientThrottledError:
            pc.printout("\nError: Instagram blocked the requests. Please wait a few minutes before trying again.\n", pc.RED)
            return
        except Exception as e:
            pc.printout(f"\nError occurred: {e}\n", pc.RED)
            return

        followers = list(followers_dict.values())

        pc.printout("Do you want to retrieve all phone numbers? (y/n): ", pc.YELLOW)
        choice = input().strip().lower()
        if choice in ["y", "yes"]:
            limit = len(followers)
        elif choice in ["n", "no"]:
            try:
                pc.printout("How many phone numbers do you want to retrieve? ", pc.YELLOW)
                limit = int(input().strip())
            except ValueError:
                pc.printout("Error: Invalid number entered\n", pc.RED)
                return
        elif choice == "":
            return
        else:
            pc.printout("Error: Please enter y or n\n", pc.RED)
            return

        results = []
        for user_short in followers:
            if len(results) >= limit:
                break
            sys.stdout.write(f"\rChecked {len(results)} followers")
            sys.stdout.flush()
            try:
                user_info = self.api.user_info(user_short.pk)
            except Exception:
                continue
            phone = getattr(user_info, "contact_phone_number", None)
            if phone:
                results.append({
                    'id': user_info.pk,
                    'username': user_info.username,
                    'full_name': user_info.full_name or "",
                    'contact_phone_number': phone
                })
        print("\r", end="")

        if results:
            t = PrettyTable(['ID', 'Username', 'Full Name', 'Phone number'])
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"
            t.align["Phone number"] = "l"
            for entry in results:
                t.add_row([str(entry['id']), entry['username'], entry['full_name'], entry['contact_phone_number']])
            if self.writeFile:
                with open(f"{self.output_dir}/{self.target}_fwersnumber.txt", "w") as f:
                    f.write(str(t))
            if self.jsonDump:
                with open(f"{self.output_dir}/{self.target}_fwersnumber.json", "w") as f:
                    json.dump({'followers_phone_numbers': results}, f, indent=4)
            print(t)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def get_people_tagged_by_user(self):
        pc.printout("Searching for users tagged by target...\n", pc.YELLOW)

        try:
            medias = self.api.user_medias(self.target_id, amount=0)  # amount=0 = all
        except Exception as e:
            self.printout(f"Error fetching media: {e}\n", self.RED)
            return

        tagged_users = {}
        for media in medias:
            if hasattr(media, "usertags") and media.usertags:
                for tag in media.usertags:
                    uid = tag.user.pk
                    if uid not in tagged_users:
                        tagged_users[uid] = {
                            "id": uid,
                            "username": tag.user.username,
                            "full_name": tag.user.full_name,
                            "post_count": 1
                        }
                    else:
                        tagged_users[uid]["post_count"] += 1
    
        if tagged_users:
            sorted_users = sorted(tagged_users.values(), key=lambda x: x['post_count'], reverse=True)

            from prettytable import PrettyTable
            t = PrettyTable(['Posts', 'Full Name', 'Username', 'ID'])
            t.align["Posts"] = "l"
            t.align["Full Name"] = "l"
            t.align["Username"] = "l"
            t.align["ID"] = "l"

            for user in sorted_users:
                t.add_row([
                    user['post_count'],
                    user['full_name'],
                    user['username'],
                    user['id']
                ])

            print(t)

            if self.writeFile:
                file_name = f"{self.output_dir}/{self.target}_tagged.txt"
                with open(file_name, "w") as f:
                    f.write(str(t))

            if self.jsonDump:
                import json
                json_data = {"tagged": sorted_users}
                json_file = f"{self.output_dir}/{self.target}_tagged.json"
                with open(json_file, "w") as f:
                    json.dump(json_data, f, indent=4)
        else:
            self.printout("Sorry! No tagged users found.\n", self.RED)
