# Osintgram2.0
FOR EDUCATIONAL PURPOSE ONLY!

This program is currently in development. For any bugs or errors you can write me on IG levi.re19.

You can find the original code here: https://github.com/Datalux/Osintgram
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

1. git clone https://github.com/MR314CKHAT/Osintgram2.0.git

2. cd Osintgram/Osintgram2.0

3. python3 -m venv venv

4. source venv/bin/activate

5. pip install -r requirements.txt

6. log in to your Instagram account in a webbrowser
presss f12 got to application -> storage -> cookies and copy your session ID

7. echo "IG_SESSIONID=<SESSIONID>" > .env # for sessionid paste ur sessionid
this sessionid is only valid for a period of time, if its not valid anymore u have to do number 6 and 7 again

If you want to use docker the installation is in the oldREADME.md, but its not tested if it works.

Usage:


![{F9F92409-EC8F-4494-831B-DD45A7D3DCE8}](https://github.com/user-attachments/assets/a384d985-7823-4fa6-8c1a-d3a971a37e45)



python3 main.py <target_username>
or with a command: python3 main.py <target_username> --command <command>



Changes from old Osintgram

updated API in Osintgram.py
adjusted main.py





