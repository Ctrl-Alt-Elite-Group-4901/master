# master
main repository

1. The main code of the project lies in main.py, and in order to run it must be in a Python 3.11 or higher environment with the right Kivy tools downloaded with the pip command. The architecture of the project must match with the folders in a necessary heirarchy. Many of the files are placeholders right now that are generated when the code is ran, such as screens/main.kv, and any TEMP.txt file only exists because Github doesn't allow for empty folders. SQLite Studio is a free app that is needed to see and maipulate the database for the app outside of running it. It uses other .py files within the app to run functions that access the SQLite commands. The .kv files within function like .html files in a different application and are the design pages of the actual code.
2. One the Python environment is setup in the VS terminal, the main.py code can be ran and will generate the necessary files, and should write them on your machine as needed. This current iteration is a simple login and registering system that opens up to a main menu that can see the profile, menu, and delete account. Thanks to saving the SQLite databse, user logins and passwords are saved even when the Arete demo is fully closed.

   NEXT GOALS: password hashing, basic game demo, stylizing pages (settings, menu, profile, statistics)
