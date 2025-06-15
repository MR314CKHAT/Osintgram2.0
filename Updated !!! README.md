# Osintgram2.0
FOR EDUCATIONAL PURPOSE ONLY!

You can find the original ccode here: https://github.com/Datalux/Osintgram
It`s made with an old API. This one is up to date and working.

Tools and commands:

- addrs           Get all registered addressed by target photos
- captions        Get user's photos captions
- comments        Get total comments of target's posts
- followers       Get target followers
- followings      Get users followed by target
- fwersemail      Get email of target followers
- fwingsemail     Get email of users followed by target
- fwersnumber     Get phone number of target followers
- fwingsnumber    Get phone number of users followed by target
- hashtags        Get hashtags used by target
- info            Get target info
- likes           Get total likes of target's posts
- mediatype       Get user's posts type (photo or video)
- photodes        Get description of target's photos
- photos          Download user's photos in output folder
- propic          Download user's profile picture
- stories         Download user's stories  
- tagged          Get list of users tagged by target
- wcommented      Get a list of user who commented target's photos
- wtagged         Get a list of user who tagged target



Installation:
git clone https://github.com/MR314CKHAT/Osintgram2.0.git

cd Osintgram/Osintgram2.0

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

log in to your Instagram account in a webbrowser
presss f12 got to application -> storage -> cookies and copy your session ID

echo "IG_SESSIONID=SESSIONID" > .env # for sessionid paste ur sessionid
this sessionid is only valid for a period of time, if its not valid anymore u have to get a new sessionid and change it in the .env file

Usage:


![{F9F92409-EC8F-4494-831B-DD45A7D3DCE8}](https://github.com/user-attachments/assets/a384d985-7823-4fa6-8c1a-d3a971a37e45)



python3 main.py <target_username>
or with a command: python3 main.py <target_username> --command <command>






